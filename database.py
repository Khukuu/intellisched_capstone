import psycopg2
from psycopg2.extras import RealDictCursor
import os
from typing import List, Dict, Any
import hashlib
import secrets
import logging

# Configure logging for database module
logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, connection_string: str = None):
        # Use environment variable for database URL, fallback to default for development
        default_connection = "postgresql://postgres:asdf1234@localhost:5432/intellisched"
        self.connection_string = connection_string or os.getenv('DATABASE_URL', default_connection)
        
    def get_connection(self):
        """Get a database connection"""
        return psycopg2.connect(self.connection_string)
    
    def execute_query(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """Execute a query and return results as list of dictionaries"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                results = []
                for row in cursor.fetchall():
                    # Convert Decimal types to regular numbers for JSON serialization
                    row_dict = dict(row)
                    for key, value in row_dict.items():
                        if hasattr(value, 'quantize'):  # Check if it's a Decimal
                            row_dict[key] = float(value)
                    results.append(row_dict)
                return results
    
    def execute_many(self, query: str, params_list: List[tuple]) -> None:
        """Execute multiple queries with different parameters"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.executemany(query, params_list)
                conn.commit()
    
    def execute_single(self, query: str, params: tuple = None) -> None:
        """Execute a single query (INSERT, UPDATE, DELETE)"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                conn.commit()

# Database operations for the scheduling system
class ScheduleDatabase:
    def __init__(self, connection_string: str = None):
        self.db = DatabaseManager(connection_string)
        self.setup_tables()
    
    def setup_tables(self):
        """Create tables if they don't exist"""
        create_tables_sql = """
        CREATE TABLE IF NOT EXISTS cs_curriculum (
            id SERIAL PRIMARY KEY,
            subject_code VARCHAR(50) UNIQUE NOT NULL,
            subject_name VARCHAR(255) NOT NULL,
            lecture_hours_per_week INTEGER DEFAULT 0,
            lab_hours_per_week INTEGER DEFAULT 0,
            units INTEGER DEFAULT 0,
            semester INTEGER,
            program_specialization VARCHAR(255),
            year_level INTEGER
        );
        
        -- IT curriculum table (mirrors CS curriculum)
        CREATE TABLE IF NOT EXISTS it_curriculum (
            id SERIAL PRIMARY KEY,
            subject_code VARCHAR(50) UNIQUE NOT NULL,
            subject_name VARCHAR(255) NOT NULL,
            lecture_hours_per_week INTEGER DEFAULT 0,
            lab_hours_per_week INTEGER DEFAULT 0,
            units INTEGER DEFAULT 0,
            semester INTEGER,
            program_specialization VARCHAR(255),
            year_level INTEGER
        );
        
        CREATE TABLE IF NOT EXISTS teachers (
            id SERIAL PRIMARY KEY,
            teacher_id VARCHAR(20) UNIQUE NOT NULL,
            teacher_name VARCHAR(255) NOT NULL,
            can_teach TEXT,
            availability_days TEXT
        );
        
        CREATE TABLE IF NOT EXISTS rooms (
            id SERIAL PRIMARY KEY,
            room_id VARCHAR(20) UNIQUE NOT NULL,
            room_name VARCHAR(255) NOT NULL,
            is_laboratory BOOLEAN DEFAULT FALSE
        );
        
        CREATE TABLE IF NOT EXISTS sections (
            id SERIAL PRIMARY KEY,
            section_id VARCHAR(50) UNIQUE NOT NULL,
            subject_code VARCHAR(50),
            year_level INTEGER,
            num_meetings_non_lab INTEGER DEFAULT 0
        );
        
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            salt VARCHAR(255) NOT NULL,
            full_name VARCHAR(255),
            email VARCHAR(255) UNIQUE,
            role VARCHAR(20) DEFAULT 'user',
            status VARCHAR(20) DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS schedule_approvals (
            id SERIAL PRIMARY KEY,
            schedule_id VARCHAR(50) NOT NULL,
            schedule_name VARCHAR(255),
            semester INTEGER,
            status VARCHAR(20) DEFAULT 'pending',
            created_by VARCHAR(50),
            approved_by VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            approved_at TIMESTAMP,
            comments TEXT
        );
        
        CREATE TABLE IF NOT EXISTS notifications (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            title VARCHAR(255) NOT NULL,
            message TEXT NOT NULL,
            type VARCHAR(50) DEFAULT 'info',
            is_read BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS system_settings (
            id SERIAL PRIMARY KEY,
            setting_key VARCHAR(100) UNIQUE NOT NULL,
            setting_value TEXT,
            setting_type VARCHAR(50) DEFAULT 'string',
            description TEXT,
            updated_by VARCHAR(50),
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS system_analytics (
            id SERIAL PRIMARY KEY,
            metric_name VARCHAR(100) NOT NULL,
            metric_value NUMERIC,
            metric_data JSONB,
            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS user_activity_log (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            activity_type VARCHAR(100) NOT NULL,
            activity_description TEXT,
            ip_address INET,
            user_agent TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        # Split and execute each statement
        statements = [stmt.strip() for stmt in create_tables_sql.split(';') if stmt.strip()]
        for statement in statements:
            try:
                self.db.execute_single(statement)
            except Exception as e:
                logger.warning(f"Could not execute statement: {e}")
                # Continue with other statements
        
        # Idempotent schema fixes for existing deployments
        try:
            self.db.execute_single("ALTER TABLE teachers ADD COLUMN IF NOT EXISTS availability_days TEXT DEFAULT 'Mon,Tue,Wed,Thu,Fri,Sat'")
        except Exception as e:
            logger.warning(f"Schema fix failed (teachers.availability_days): {e}")
        
        # Check if users table has correct structure
        if not self._check_users_table_structure():
            logger.warning("Users table structure is incorrect. Attempting to fix...")
            if self._fix_users_table():
                logger.info("Users table structure fixed successfully")
            else:
                logger.error("Failed to fix users table structure. Please run fix_users_table.py manually.")
                return
        
        # Create default admin user if it doesn't exist
        self.create_default_admin()
    
    def _check_users_table_structure(self):
        """Check if the users table has the correct structure"""
        try:
            # Check if salt column exists
            result = self.db.execute_query("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'salt'
            """)
            return len(result) > 0
        except Exception as e:
            logger.error(f"Error checking table structure: {e}")
            return False
    
    def _fix_users_table(self):
        """Fix the users table structure by recreating it"""
        try:
            # Drop and recreate the users table
            self.db.execute_single("DROP TABLE IF EXISTS users CASCADE")
            
            create_users_sql = """
            CREATE TABLE users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                salt VARCHAR(255) NOT NULL,
                full_name VARCHAR(255),
                email VARCHAR(255),
                role VARCHAR(20) DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            );
            """
            
            self.db.execute_single(create_users_sql)
            return True
        except Exception as e:
            logger.error(f"Error fixing users table: {e}")
            return False
    
    def create_default_admin(self):
        """Create default admin, chair, dean, and secretary users if they don't exist"""
        try:
            # Check if admin user exists
            existing_admin = self.db.execute_query("SELECT id FROM users WHERE username = %s", ('admin',))
            if not existing_admin:
                # Create default admin user
                password = os.getenv('ADMIN_PASSWORD', 'AdminSecure123!')
                salt = secrets.token_hex(16)
                password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
                
                self.db.execute_single("""
                    INSERT INTO users (username, password_hash, salt, full_name, email, role, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, ('admin', password_hash, salt, 'Administrator', 'admin@intellisched.com', 'admin', 'active'))
                
                logger.info("Default admin user created (username: admin, password: [HIDDEN])")
            
            # Check if chair user exists
            existing_chair = self.db.execute_query("SELECT id FROM users WHERE username = %s", ('chair',))
            if not existing_chair:
                # Create default chair user
                password = os.getenv('CHAIR_PASSWORD', 'ChairSecure123!')
                salt = secrets.token_hex(16)
                password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
                
                self.db.execute_single("""
                    INSERT INTO users (username, password_hash, salt, full_name, email, role, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, ('chair', password_hash, salt, 'Department Chair', 'chair@intellisched.com', 'chair', 'active'))
                
                logger.info("Default chair user created (username: chair, password: [HIDDEN])")
            
            # Check if dean user exists
            existing_dean = self.db.execute_query("SELECT id FROM users WHERE username = %s", ('dean',))
            if not existing_dean:
                # Create default dean user
                password = os.getenv('DEAN_PASSWORD', 'DeanSecure123!')
                salt = secrets.token_hex(16)
                password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
                
                self.db.execute_single("""
                    INSERT INTO users (username, password_hash, salt, full_name, email, role, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, ('dean', password_hash, salt, 'Dean', 'dean@intellisched.com', 'dean', 'active'))
                
                print("✅ Default dean user created (username: dean, password: [HIDDEN])")
            
            # Check if secretary user exists
            existing_secretary = self.db.execute_query("SELECT id FROM users WHERE username = %s", ('sec',))
            if not existing_secretary:
                # Create default secretary user
                password = os.getenv('SECRETARY_PASSWORD', 'SecretarySecure123!')
                salt = secrets.token_hex(16)
                password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
                
                self.db.execute_single("""
                    INSERT INTO users (username, password_hash, salt, full_name, email, role, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, ('sec', password_hash, salt, 'Secretary', 'secretary@intellisched.com', 'secretary', 'active'))
                
                print("✅ Default secretary user created (username: sec, password: [HIDDEN])")
                
        except Exception as e:
            print(f"⚠️ Could not create default users: {e}")
    
    def verify_user_credentials(self, username: str, password: str) -> Dict[str, Any]:
        """Verify user credentials and return user info if valid"""
        try:
            user = self.db.execute_query("SELECT * FROM users WHERE username = %s", (username,))
            if not user:
                return None
            
            user = user[0]
            stored_hash = user['password_hash']
            salt = user['salt']
            
            # Hash the provided password with the stored salt
            input_hash = hashlib.sha256((password + salt).encode()).hexdigest()
            
            if input_hash == stored_hash:
                # Check if user is active
                if user.get('status') != 'active':
                    return None
                
                # Update last login
                self.db.execute_single("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s", (user['id'],))
                
                # Return user info (without sensitive data)
                return {
                    'id': user['id'],
                    'username': user['username'],
                    'full_name': user['full_name'],
                    'email': user['email'],
                    'role': user['role'],
                    'status': user.get('status', 'pending')
                }
            return None
        except Exception as e:
            logger.error(f"Error verifying credentials: {e}")
            return None
    
    def get_user_by_id(self, user_id: int) -> Dict[str, Any]:
        """Get user by ID (without sensitive data)"""
        try:
            user = self.db.execute_query("SELECT id, username, full_name, email, role, created_at, last_login FROM users WHERE id = %s", (user_id,))
            return user[0] if user else None
        except Exception as e:
            print(f"Error getting user: {e}")
            return None
    
    def get_user_by_username(self, username: str) -> Dict[str, Any]:
        """Get user by username (without sensitive data)"""
        try:
            user = self.db.execute_query("SELECT id, username, full_name, email, role, status, created_at, last_login FROM users WHERE username = %s", (username,))
            return user[0] if user else None
        except Exception as e:
            print(f"Error getting user: {e}")
            return None
    
    def create_user(self, user_data: Dict[str, Any]) -> bool:
        """Create a new user"""
        try:
            password = user_data['password']
            salt = secrets.token_hex(16)
            password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
            
            self.db.execute_single("""
                INSERT INTO users (username, password_hash, salt, full_name, email, role, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                user_data['username'],
                password_hash,
                salt,
                user_data.get('full_name', ''),
                user_data.get('email', ''),
                user_data.get('role', 'user'),
                user_data.get('status', 'pending')
            ))
            return True
        except Exception as e:
            print(f"Error creating user: {e}")
            return False
    
    def update_user_password(self, user_id: int, new_password: str) -> bool:
        """Update user password"""
        try:
            salt = secrets.token_hex(16)
            password_hash = hashlib.sha256((new_password + salt).encode()).hexdigest()
            
            self.db.execute_single("""
                UPDATE users SET password_hash = %s, salt = %s WHERE id = %s
            """, (password_hash, salt, user_id))
            return True
        except Exception as e:
            print(f"Error updating password: {e}")
            return False
    
    def load_subjects(self, programs: List[str] = None) -> List[Dict[str, Any]]:
        """Load all subjects from database for specified programs"""
        if programs is None:
            programs = ['CS']
        
        all_subjects = []
        seen_subjects = set()  # Track seen subject codes to avoid duplicates
        
        for program in programs:
            if program.upper() == 'IT':
                table_name = 'it_curriculum'
            else:
                table_name = 'cs_curriculum'
                
            query = f"""
            SELECT 
                subject_code,
                subject_name,
                lecture_hours_per_week,
                lab_hours_per_week,
                units,
                semester,
                program_specialization,
                year_level,
                '{program.upper()}' as program
            FROM {table_name}
            ORDER BY year_level, semester, subject_code
            """
            subjects = self.db.execute_query(query)
            
            # Add subjects, but skip duplicates (same subject_code, year_level, semester)
            for subject in subjects:
                # Create a unique key for deduplication
                dedup_key = (subject['subject_code'], subject['year_level'], subject['semester'])
                if dedup_key not in seen_subjects:
                    seen_subjects.add(dedup_key)
                    all_subjects.append(subject)
                else:
                    # For general education subjects that exist in both programs, 
                    # we need to make them available to both programs
                    # Find the existing subject and update its program info
                    for existing_subject in all_subjects:
                        if (existing_subject['subject_code'] == subject['subject_code'] and
                            existing_subject['year_level'] == subject['year_level'] and
                            existing_subject['semester'] == subject['semester']):
                            # Mark this subject as available to both programs
                            if 'available_programs' not in existing_subject:
                                existing_subject['available_programs'] = [existing_subject.get('program', 'CS')]
                            if program.upper() not in existing_subject['available_programs']:
                                existing_subject['available_programs'].append(program.upper())
                            print(f"Debug: Subject {subject['subject_code']} is available to programs: {existing_subject['available_programs']}")
                            break
        
        return all_subjects
    
    def load_teachers(self) -> List[Dict[str, Any]]:
        """Load all teachers from database"""
        # Check if availability_days column exists
        try:
            query = """
            SELECT 
                teacher_id,
                teacher_name,
                can_teach,
                availability_days
            FROM teachers
            ORDER BY teacher_name
            """
            return self.db.execute_query(query)
        except Exception as e:
            if "availability_days" in str(e):
                # Fallback query without availability_days
                query = """
                SELECT 
                    teacher_id,
                    teacher_name,
                    can_teach,
                    'Mon,Tue,Wed,Thu,Fri' as availability_days
                FROM teachers
                ORDER BY teacher_name
                """
                return self.db.execute_query(query)
            else:
                raise e
    
    def load_rooms(self) -> List[Dict[str, Any]]:
        """Load all rooms from database"""
        query = """
        SELECT 
            room_id,
            room_name,
            is_laboratory
        FROM rooms
        ORDER BY room_name
        """
        return self.db.execute_query(query)
    
    def load_sections(self) -> List[Dict[str, Any]]:
        """Load all sections from database"""
        query = """
        SELECT 
            section_id,
            subject_code,
            year_level,
            num_meetings_non_lab
        FROM sections
        ORDER BY section_id
        """
        return self.db.execute_query(query)
    
    def insert_subject(self, subject_data: Dict[str, Any]) -> None:
        """Insert a single subject"""
        query = """
        INSERT INTO cs_curriculum (subject_code, subject_name, lecture_hours_per_week, 
                             lab_hours_per_week, units, semester, program_specialization, year_level)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (subject_code) DO UPDATE SET
            subject_name = EXCLUDED.subject_name,
            lecture_hours_per_week = EXCLUDED.lecture_hours_per_week,
            lab_hours_per_week = EXCLUDED.lab_hours_per_week,
            units = EXCLUDED.units,
            semester = EXCLUDED.semester,
            program_specialization = EXCLUDED.program_specialization,
            year_level = EXCLUDED.year_level
        """
        params = (
            subject_data['subject_code'],
            subject_data['subject_name'],
            subject_data.get('lecture_hours_per_week', 0),
            subject_data.get('lab_hours_per_week', 0),
            subject_data['units'],
            subject_data.get('semester'),
            subject_data.get('program_specialization'),
            subject_data.get('year_level')
        )
        self.db.execute_single(query, params)
        
    def insert_it_subject(self, subject_data: Dict[str, Any]) -> None:
        """Insert a single IT subject"""
        query = """
        INSERT INTO it_curriculum (subject_code, subject_name, lecture_hours_per_week, 
                             lab_hours_per_week, units, semester, program_specialization, year_level)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (subject_code) DO UPDATE SET
            subject_name = EXCLUDED.subject_name,
            lecture_hours_per_week = EXCLUDED.lecture_hours_per_week,
            lab_hours_per_week = EXCLUDED.lab_hours_per_week,
            units = EXCLUDED.units,
            semester = EXCLUDED.semester,
            program_specialization = EXCLUDED.program_specialization,
            year_level = EXCLUDED.year_level
        """
        params = (
            subject_data['subject_code'],
            subject_data['subject_name'],
            subject_data.get('lecture_hours_per_week', 0),
            subject_data.get('lab_hours_per_week', 0),
            subject_data['units'],
            subject_data.get('semester'),
            subject_data.get('program_specialization'),
            subject_data.get('year_level')
        )
        self.db.execute_single(query, params)
        
    def insert_teacher(self, teacher_data: Dict[str, Any]) -> int:
        """Insert a single teacher and return the generated teacher_id"""
        # Ensure teacher_id exists (generate if not provided)
        teacher_id = teacher_data.get('teacher_id')
        if not teacher_id:
            import secrets
            teacher_id = f"T{secrets.token_hex(4).upper()}"
        
        query = """
        INSERT INTO teachers (teacher_id, teacher_name, can_teach, availability_days)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (teacher_id) DO UPDATE SET
            teacher_name = EXCLUDED.teacher_name,
            can_teach = EXCLUDED.can_teach,
            availability_days = EXCLUDED.availability_days
        RETURNING teacher_id
        """
        # Default to all days available if not specified
        availability_days = teacher_data.get('availability_days', ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'])
        params = (
            teacher_id,
            teacher_data['teacher_name'],
            teacher_data.get('can_teach', ''),
            availability_days
        )
        result = self.db.execute_query(query, params)
        return result[0]['teacher_id'] if result else None
    
    def insert_room(self, room_data: Dict[str, Any]) -> int:
        """Insert a single room and return the generated room_id"""
        # Ensure room_id exists (generate if not provided)
        room_id = room_data.get('room_id')
        if not room_id:
            import secrets
            room_id = f"R{secrets.token_hex(4).upper()}"
        query = """
        INSERT INTO rooms (room_id, room_name, is_laboratory)
        VALUES (%s, %s, %s)
        ON CONFLICT (room_id) DO UPDATE SET
            room_name = EXCLUDED.room_name,
            is_laboratory = EXCLUDED.is_laboratory
        RETURNING room_id
        """
        params = (
            room_id,
            room_data['room_name'],
            room_data.get('is_laboratory', False)
        )
        result = self.db.execute_query(query, params)
        return result[0]['room_id'] if result else None
    
    def insert_section(self, section_data: Dict[str, Any]) -> None:
        """Insert a single section"""
        query = """
        INSERT INTO sections (section_id, subject_code, year_level, num_meetings_non_lab)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (section_id) DO UPDATE SET
            subject_code = EXCLUDED.subject_code,
            year_level = EXCLUDED.year_level,
            num_meetings_non_lab = EXCLUDED.num_meetings_non_lab
        """
        params = (
            section_data['section_id'],
            section_data.get('subject_code'),
            section_data.get('year_level'),
            section_data.get('num_meetings_non_lab', 0)
        )
        self.db.execute_single(query, params)
    
    def migrate_from_csv(self):
        """Legacy function - data is already in PostgreSQL"""
        print("✅ Data is already in PostgreSQL database")
        print("📊 No CSV migration needed")

# Global database instance
db = ScheduleDatabase()

def load_subjects_from_db(programs: List[str] = None):
    """Load subjects from database for specified programs (replaces CSV loading)"""
    return db.load_subjects(programs)

def load_teachers_from_db():
    """Load teachers from database (replaces CSV loading)"""
    return db.load_teachers()

def load_rooms_from_db():
    """Load rooms from database (replaces CSV loading)"""
    return db.load_rooms()
 
def load_sections_from_db():
    """Load sections from database (replaces CSV loading)"""
    return db.load_sections()

def add_subject(subject_data: Dict[str, Any]) -> None:
    """Add a new subject to the CS curriculum database"""
    db.insert_subject(subject_data)

def add_it_subject(subject_data: Dict[str, Any]) -> None:
    """Add a new subject to the IT curriculum database"""
    db.insert_it_subject(subject_data)

def update_it_subject(subject_code: str, subject_data: Dict[str, Any]) -> None:
    """Update an existing IT subject in the database"""
    db.insert_it_subject(subject_data)  # Uses ON CONFLICT DO UPDATE

def delete_it_subject(subject_code: str) -> None:
    """Delete an IT subject from the database"""
    db.delete_it_subject(subject_code)

def add_teacher(teacher_data: Dict[str, Any]) -> int:
    """Add a new teacher to the database and return the generated ID"""
    return db.insert_teacher(teacher_data)

def add_room(room_data: Dict[str, Any]) -> int:
    """Add a new room to the database and return the generated ID"""
    return db.insert_room(room_data)
 
def add_section(section_data: Dict[str, Any]) -> None:
    """Add a new section to the database"""
    db.insert_section(section_data)

def update_subject(subject_code: str, subject_data: Dict[str, Any]) -> None:
    """Update an existing subject in the database"""
    db.insert_subject(subject_data)  # Uses ON CONFLICT DO UPDATE

def update_teacher(teacher_id: str, teacher_data: Dict[str, Any]) -> None:
    """Update an existing teacher in the database"""
    logger.info(f"Updating teacher {teacher_id} with data: {teacher_data}")
    
    # Build dynamic UPDATE query based on provided fields
    update_fields = []
    params = []
    
    if 'teacher_name' in teacher_data:
        update_fields.append("teacher_name = %s")
        params.append(teacher_data['teacher_name'])
    
    if 'can_teach' in teacher_data:
        update_fields.append("can_teach = %s")
        params.append(teacher_data['can_teach'])
    
    if 'availability_days' in teacher_data:
        update_fields.append("availability_days = %s")
        # Handle both string and array formats
        availability_days = teacher_data['availability_days']
        if isinstance(availability_days, str):
            # Split comma-separated string into array
            availability_days = [day.strip() for day in availability_days.split(',') if day.strip()]
        params.append(availability_days)
    
    if not update_fields:
        raise ValueError("No valid fields provided for update")
    
    query = f"""
    UPDATE teachers 
    SET {', '.join(update_fields)}
    WHERE teacher_id = %s
    """
    params.append(teacher_id)
    
    logger.info(f"Executing query: {query} with params: {params}")
    db.db.execute_single(query, params)

def update_room(room_id: str, room_data: Dict[str, Any]) -> None:
    """Update an existing room in the database"""
    query = """
    UPDATE rooms 
    SET room_name = %s, is_laboratory = %s
    WHERE room_id = %s
    """
    params = (
        room_data['room_name'],
        room_data.get('is_laboratory', False),
        room_id
    )
    db.db.execute_single(query, params)
 
def update_section(section_id: str, section_data: Dict[str, Any]) -> None:
    """Update an existing section in the database"""
    db.insert_section(section_data)  # Uses ON CONFLICT DO UPDATE

def delete_subject(subject_code: str) -> None:
    """Delete a subject from the CS curriculum database"""
    query = "DELETE FROM cs_curriculum WHERE subject_code = %s"
    db.db.execute_single(query, (subject_code,))

def delete_it_subject(subject_code: str) -> None:
    """Delete a subject from the IT curriculum database"""
    query = "DELETE FROM it_curriculum WHERE subject_code = %s"
    db.db.execute_single(query, (subject_code,))

def delete_teacher(teacher_id: str) -> None:
    """Delete a teacher from the database"""
    query = "DELETE FROM teachers WHERE teacher_id = %s"
    db.db.execute_single(query, (teacher_id,))

def delete_room(room_id: str) -> None:
    """Delete a room from the database"""
    query = "DELETE FROM rooms WHERE room_id = %s"
    db.db.execute_single(query, (room_id,))
 
def delete_section(section_id: str) -> None:
    """Delete a section from the database"""
    query = "DELETE FROM sections WHERE section_id = %s"
    db.db.execute_single(query, (section_id,))

def get_subject_by_code(subject_code: str) -> Dict[str, Any]:
    """Get a specific subject by code"""
    query = "SELECT * FROM cs_curriculum WHERE subject_code = %s"
    results = db.db.execute_query(query, (subject_code,))
    return results[0] if results else None

def get_teacher_by_id(teacher_id: str) -> Dict[str, Any]:
    """Get a specific teacher by ID"""
    query = "SELECT * FROM teachers WHERE teacher_id = %s"
    results = db.db.execute_query(query, (teacher_id,))
    return results[0] if results else None

def get_room_by_id(room_id: str) -> Dict[str, Any]:
    """Get a specific room by ID"""
    query = "SELECT * FROM rooms WHERE room_id = %s"
    results = db.db.execute_query(query, (room_id,))
    return results[0] if results else None

def get_section_by_id(section_id: str) -> Dict[str, Any]:
    """Get a specific section by ID"""
    query = "SELECT * FROM sections WHERE section_id = %s"
    results = db.db.execute_query(query, (section_id,))
    return results[0] if results else None

# Schedule approval functions
def create_schedule_approval(schedule_id: str, schedule_name: str, semester: int, created_by: str) -> bool:
    """Create a new schedule approval request"""
    try:
        query = """
        INSERT INTO schedule_approvals (schedule_id, schedule_name, semester, created_by, status)
        VALUES (%s, %s, %s, %s, 'pending')
        """
        db.db.execute_single(query, (schedule_id, schedule_name, semester, created_by))
        
        # Send notification to all deans about the new schedule submission
        try:
            # Get all dean users
            dean_query = "SELECT id FROM users WHERE role = 'dean'"
            deans = db.db.execute_query(dean_query)
            
            for dean in deans:
                create_notification(
                    dean['id'],
                    "New Schedule Submitted",
                    f"Chair {created_by} has submitted a new schedule '{schedule_name}' for semester {semester} and is awaiting your approval.",
                    "info"
                )
            logger.info(f"Sent notifications to {len(deans)} deans about schedule submission from {created_by}")
        except Exception as notification_error:
            logger.warning(f"Failed to send notifications for schedule submission: {notification_error}")
        
        return True
    except Exception as e:
        logger.error(f"Error creating schedule approval: {e}")
        return False

def get_pending_schedules() -> List[Dict[str, Any]]:
    """Get all pending schedule approvals"""
    query = """
    SELECT * FROM schedule_approvals 
    WHERE status = 'pending' 
    ORDER BY created_at DESC
    """
    logger.debug(f"Executing query: {query}")
    rows = db.db.execute_query(query)
    logger.info(f"Found {len(rows)} pending schedules in database")
    # Convert datetime fields to ISO strings for JSON serialization
    for r in rows:
        if 'created_at' in r and r['created_at']:
            try:
                r['created_at'] = r['created_at'].isoformat()
            except Exception:
                pass
        if 'approved_at' in r and r.get('approved_at'):
            try:
                r['approved_at'] = r['approved_at'].isoformat()
            except Exception:
                pass
    return rows

def get_approved_schedules() -> List[Dict[str, Any]]:
    """Get all approved schedules"""
    query = """
    SELECT * FROM schedule_approvals 
    WHERE status = 'approved' 
    ORDER BY approved_at DESC
    """
    rows = db.db.execute_query(query)
    for r in rows:
        if 'created_at' in r and r['created_at']:
            try:
                r['created_at'] = r['created_at'].isoformat()
            except Exception:
                pass
        if 'approved_at' in r and r.get('approved_at'):
            try:
                r['approved_at'] = r['approved_at'].isoformat()
            except Exception:
                pass
    return rows

def approve_schedule(schedule_id: str, approved_by: str, comments: str = None) -> bool:
    """Approve a schedule"""
    try:
        # Get schedule details for notification
        schedule_query = "SELECT * FROM schedule_approvals WHERE schedule_id = %s"
        schedule_result = db.db.execute_query(schedule_query, (schedule_id,))
        
        query = """
        UPDATE schedule_approvals 
        SET status = 'approved', approved_by = %s, approved_at = CURRENT_TIMESTAMP, comments = %s
        WHERE schedule_id = %s AND status = 'pending'
        """
        db.db.execute_single(query, (approved_by, comments, schedule_id))
        
        # Send notification to the creator
        if schedule_result:
            schedule = schedule_result[0]
            creator_id = get_user_id_by_username(schedule['created_by'])
            if creator_id:
                create_notification(
                    creator_id,
                    "Schedule Approved",
                    f"Your schedule '{schedule['schedule_name']}' has been approved by {approved_by}.",
                    "success"
                )
        
        return True
    except Exception as e:
        print(f"Error approving schedule: {e}")
        return False

def reject_schedule(schedule_id: str, rejected_by: str, comments: str = None) -> bool:
    """Reject a schedule"""
    try:
        # Get schedule details for notification
        schedule_query = "SELECT * FROM schedule_approvals WHERE schedule_id = %s"
        schedule_result = db.db.execute_query(schedule_query, (schedule_id,))
        
        query = """
        UPDATE schedule_approvals 
        SET status = 'rejected', approved_by = %s, approved_at = CURRENT_TIMESTAMP, comments = %s
        WHERE schedule_id = %s AND status = 'pending'
        """
        db.db.execute_single(query, (rejected_by, comments, schedule_id))
        
        # Send notification to the creator
        if schedule_result:
            schedule = schedule_result[0]
            creator_id = get_user_id_by_username(schedule['created_by'])
            if creator_id:
                create_notification(
                    creator_id,
                    "Schedule Rejected",
                    f"Your schedule '{schedule['schedule_name']}' has been rejected by {rejected_by}. Comments: {comments or 'No comments provided'}",
                    "warning"
                )
        
        return True
    except Exception as e:
        print(f"Error rejecting schedule: {e}")
        return False

def get_schedule_approval_status(schedule_id: str) -> Dict[str, Any]:
    """Get approval status for a specific schedule"""
    query = "SELECT * FROM schedule_approvals WHERE schedule_id = %s"
    results = db.db.execute_query(query, (schedule_id,))
    return results[0] if results else None

def delete_schedule_approval(schedule_id: str) -> None:
    """Delete a schedule approval record"""
    try:
        # First check if the record exists
        check_query = "SELECT * FROM schedule_approvals WHERE schedule_id = %s"
        existing = db.db.execute_query(check_query, (schedule_id,))
        logger.debug(f"Before deletion: Found {len(existing)} records for schedule_id: {schedule_id}")
        
        # Use execute_single for DELETE operations to ensure transaction is committed
        query = "DELETE FROM schedule_approvals WHERE schedule_id = %s"
        db.db.execute_single(query, (schedule_id,))
        logger.debug(f"Executed DELETE query for schedule_id: {schedule_id}")
        
        # Verify deletion
        remaining = db.db.execute_query(check_query, (schedule_id,))
        logger.debug(f"After deletion: Found {len(remaining)} records for schedule_id: {schedule_id}")
        
        return True
    except Exception as e:
        logger.error(f"Error deleting schedule approval record for {schedule_id}: {e}")
        return False

# Notification functions
def create_notification(user_id: int, title: str, message: str, notification_type: str = 'info') -> bool:
    """Create a new notification for a user"""
    try:
        # Check if notifications are enabled system-wide
        notifications_enabled = get_system_setting('enable_notifications', 'true')
        if notifications_enabled.lower() == 'false':
            logger.info(f"Notifications are disabled system-wide. Skipping notification for user_id: {user_id}, title: {title}")
            return True  # Return True to indicate "success" (no error, just skipped)
        
        query = """
        INSERT INTO notifications (user_id, title, message, type)
        VALUES (%s, %s, %s, %s)
        """
        logger.info(f"Creating notification for user_id: {user_id}, title: {title}, type: {notification_type}")
        db.db.execute_single(query, (user_id, title, message, notification_type))
        logger.info(f"Successfully created notification for user_id: {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error creating notification for user_id {user_id}: {e}")
        return False

def get_user_notifications(user_id: int, unread_only: bool = False) -> List[Dict[str, Any]]:
    """Get notifications for a user"""
    try:
        if unread_only:
            query = """
            SELECT * FROM notifications 
            WHERE user_id = %s AND is_read = FALSE 
            ORDER BY created_at DESC
            """
            logger.debug(f"Getting unread notifications for user_id: {user_id}")
            result = db.db.execute_query(query, (user_id,))
            logger.debug(f"Found {len(result)} unread notifications for user_id: {user_id}")
        else:
            query = """
            SELECT * FROM notifications 
            WHERE user_id = %s 
            ORDER BY created_at DESC
            """
            logger.debug(f"Getting all notifications for user_id: {user_id}")
            result = db.db.execute_query(query, (user_id,))
            logger.debug(f"Found {len(result)} total notifications for user_id: {user_id}")
        
        # Convert datetime objects to strings for JSON serialization
        for notification in result:
            if 'created_at' in notification and notification['created_at']:
                if hasattr(notification['created_at'], 'isoformat'):
                    notification['created_at'] = notification['created_at'].isoformat()
                else:
                    notification['created_at'] = str(notification['created_at'])
        
        return result
    except Exception as e:
        logger.error(f"Error getting notifications for user_id {user_id}: {e}")
        return []

def mark_notification_read(notification_id: int) -> bool:
    """Mark a notification as read"""
    try:
        query = "UPDATE notifications SET is_read = TRUE WHERE id = %s"
        logger.info(f"Marking notification {notification_id} as read")
        db.db.execute_single(query, (notification_id,))
        logger.info(f"Successfully marked notification {notification_id} as read")
        return True
    except Exception as e:
        logger.error(f"Error marking notification {notification_id} as read: {e}")
        return False

def delete_notification(notification_id: int) -> bool:
    """Delete a notification"""
    try:
        query = "DELETE FROM notifications WHERE id = %s"
        logger.info(f"Deleting notification {notification_id}")
        db.db.execute_single(query, (notification_id,))
        logger.info(f"Successfully deleted notification {notification_id}")
        return True
    except Exception as e:
        logger.error(f"Error deleting notification {notification_id}: {e}")
        return False

def get_user_id_by_username(username: str) -> int:
    """Get user ID by username"""
    try:
        query = "SELECT id FROM users WHERE username = %s"
        logger.debug(f"Looking up user_id for username: {username}")
        results = db.db.execute_query(query, (username,))
        if results:
            user_id = results[0]['id']
            logger.debug(f"Found user_id: {user_id} for username: {username}")
            return user_id
        else:
            logger.warning(f"No user found with username: {username}")
            return None
    except Exception as e:
        logger.error(f"Error getting user ID for username {username}: {e}")
        return None

# User management functions
def get_pending_users() -> List[Dict[str, Any]]:
    """Get all pending users for admin approval"""
    try:
        query = """
        SELECT id, username, full_name, email, role, created_at 
        FROM users 
        WHERE status = 'pending' 
        ORDER BY created_at DESC
        """
        users = db.db.execute_query(query)
        
        # Convert datetime objects to strings for JSON serialization
        for user in users:
            if 'created_at' in user and user['created_at']:
                user['created_at'] = user['created_at'].isoformat()
        
        return users
    except Exception as e:
        print(f"Error getting pending users: {e}")
        return []

def approve_user(user_id: int, approved_by: str) -> bool:
    """Approve a pending user"""
    try:
        # Update user status to active
        query = "UPDATE users SET status = 'active' WHERE id = %s AND status = 'pending'"
        db.db.execute_single(query, (user_id,))
        
        # Get user details for notification
        user_query = "SELECT username, full_name, email FROM users WHERE id = %s"
        user_result = db.db.execute_query(user_query, (user_id,))
        
        if user_result:
            user = user_result[0]
            # Create notification for the approved user
            create_notification(
                user_id,
                "Account Approved",
                f"Your account has been approved by {approved_by}. You can now log in to IntelliSched.",
                "success"
            )
        
        return True
    except Exception as e:
        print(f"Error approving user: {e}")
        return False

def reject_user(user_id: int, rejected_by: str, reason: str = None) -> bool:
    """Reject a pending user"""
    try:
        # Get user details before deletion
        user_query = "SELECT username, full_name, email FROM users WHERE id = %s"
        user_result = db.db.execute_query(user_query, (user_id,))
        
        # Delete the user
        query = "DELETE FROM users WHERE id = %s AND status = 'pending'"
        db.db.execute_single(query, (user_id,))
        
        return True
    except Exception as e:
        print(f"Error rejecting user: {e}")
        return False

def get_user_by_email(email: str) -> Dict[str, Any]:
    """Get user by email"""
    try:
        query = "SELECT id, username, full_name, email, role, status, created_at FROM users WHERE email = %s"
        results = db.db.execute_query(query, (email,))
        return results[0] if results else None
    except Exception as e:
        print(f"Error getting user by email: {e}")
        return None

def check_email_exists(email: str) -> bool:
    """Check if email already exists"""
    try:
        query = "SELECT id FROM users WHERE email = %s"
        results = db.db.execute_query(query, (email,))
        return len(results) > 0
    except Exception as e:
        print(f"Error checking email: {e}")
        return False

def get_all_users() -> List[Dict[str, Any]]:
    """Get all users for admin management"""
    try:
        query = """
        SELECT id, username, full_name, email, role, status, created_at, last_login 
        FROM users 
        ORDER BY created_at DESC
        """
        users = db.db.execute_query(query)
        
        # Convert datetime objects to strings for JSON serialization
        for user in users:
            if 'created_at' in user and user['created_at']:
                user['created_at'] = user['created_at'].isoformat()
            if 'last_login' in user and user['last_login']:
                user['last_login'] = user['last_login'].isoformat()
        
        return users
    except Exception as e:
        print(f"Error getting all users: {e}")
        return []

def delete_user(user_id: int, admin_username: str) -> bool:
    """Delete a user from the database with proper error handling and transaction management"""
    try:
        # Get user info for logging
        user = db.db.execute_query("SELECT username, full_name, role FROM users WHERE id = %s", (user_id,))
        if not user:
            logger.warning(f"User with ID {user_id} not found")
            return False
        
        user_info = user[0]
        username = user_info['username']
        
        logger.info(f"Starting deletion process for user {user_id} ({username}) by admin {admin_username}")
        
        # Use a single transaction for all operations
        with db.db.get_connection() as conn:
            with conn.cursor() as cursor:
                try:
                    # Start transaction
                    cursor.execute("BEGIN")
                    
                    # Delete user activity logs first (has foreign key to users)
                    cursor.execute("DELETE FROM user_activity_log WHERE user_id = %s", (user_id,))
                    logger.info(f"Deleted user activity logs for user {user_id}")
                    
                    # Delete notifications associated with this user
                    cursor.execute("DELETE FROM notifications WHERE user_id = %s", (user_id,))
                    logger.info(f"Deleted notifications for user {user_id}")
                    
                    # Delete schedule approvals created by this user
                    cursor.execute("DELETE FROM schedule_approvals WHERE created_by = %s", (username,))
                    logger.info(f"Deleted schedule approvals created by user {user_id}")
                    
                    # Update schedule approvals approved by this user (set to NULL)
                    cursor.execute("UPDATE schedule_approvals SET approved_by = NULL WHERE approved_by = %s", (username,))
                    logger.info(f"Cleared approval records for user {user_id}")
                    
                    # Finally, delete the user
                    cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
                    logger.info(f"Deleted user {user_id} from users table")
                    
                    # Commit transaction
                    cursor.execute("COMMIT")
                    conn.commit()
                    
                    logger.info(f"User successfully deleted by {admin_username}: {username} ({user_info['full_name']}) - Role: {user_info['role']}")
                    return True
                    
                except Exception as e:
                    # Rollback transaction on error
                    cursor.execute("ROLLBACK")
                    conn.rollback()
                    logger.error(f"Error deleting user {user_id}: {e}")
                    raise e
        
    except Exception as e:
        logger.error(f"Failed to delete user {user_id}: {e}")
        return False

# Analytics Functions
def record_user_activity(user_id: int, activity_type: str, description: str, ip_address: str = None, user_agent: str = None) -> bool:
    """Record user activity for analytics"""
    try:
        query = """
        INSERT INTO user_activity_log (user_id, activity_type, activity_description, ip_address, user_agent)
        VALUES (%s, %s, %s, %s, %s)
        """
        db.db.execute_single(query, (user_id, activity_type, description, ip_address, user_agent))
        return True
    except Exception as e:
        logger.error(f"Error recording user activity: {e}")
        return False

def get_user_activity_stats(days: int = 30) -> Dict[str, Any]:
    """Get user activity statistics"""
    try:
        # Activity by type
        activity_query = """
        SELECT activity_type, COUNT(*) as count
        FROM user_activity_log 
        WHERE created_at >= NOW() - INTERVAL '%s days'
        GROUP BY activity_type
        ORDER BY count DESC
        """
        activities = db.db.execute_query(activity_query, (days,))
        
        # Daily activity
        daily_query = """
        SELECT DATE(created_at) as date, COUNT(*) as count
        FROM user_activity_log 
        WHERE created_at >= NOW() - INTERVAL '%s days'
        GROUP BY DATE(created_at)
        ORDER BY date DESC
        """
        daily_activities = db.db.execute_query(daily_query, (days,))
        
        # Top active users
        users_query = """
        SELECT u.username, u.full_name, u.role, COUNT(a.id) as activity_count
        FROM users u
        LEFT JOIN user_activity_log a ON u.id = a.user_id AND a.created_at >= NOW() - INTERVAL '%s days'
        GROUP BY u.id, u.username, u.full_name, u.role
        ORDER BY activity_count DESC
        LIMIT 10
        """
        top_users = db.db.execute_query(users_query, (days,))
        
        # Convert date objects to ISO format strings for JSON serialization
        for daily in daily_activities:
            if 'date' in daily and daily['date']:
                daily['date'] = daily['date'].isoformat()
        
        return {
            'activities_by_type': activities,
            'daily_activities': daily_activities,
            'top_active_users': top_users
        }
    except Exception as e:
        logger.error(f"Error getting user activity stats: {e}")
        return {'activities_by_type': [], 'daily_activities': [], 'top_active_users': []}

def get_system_analytics() -> Dict[str, Any]:
    """Get comprehensive system analytics"""
    try:
        # User statistics
        user_stats_query = """
        SELECT 
            role,
            status,
            COUNT(*) as count
        FROM users 
        GROUP BY role, status
        ORDER BY role, status
        """
        user_stats = db.db.execute_query(user_stats_query)
        
        # Schedule statistics
        schedule_stats_query = """
        SELECT 
            status,
            COUNT(*) as count
        FROM schedule_approvals 
        GROUP BY status
        """
        schedule_stats = db.db.execute_query(schedule_stats_query)
        
        # Recent registrations
        recent_registrations_query = """
        SELECT DATE(created_at) as date, COUNT(*) as count
        FROM users 
        WHERE created_at >= NOW() - INTERVAL '30 days'
        GROUP BY DATE(created_at)
        ORDER BY date DESC
        """
        recent_registrations = db.db.execute_query(recent_registrations_query)
        
        # System data counts
        data_counts_query = """
        SELECT 
            'subjects' as type, COUNT(*) as count FROM cs_curriculum
            UNION ALL
            SELECT 'teachers', COUNT(*) FROM teachers
            UNION ALL
            SELECT 'rooms', COUNT(*) FROM rooms
            UNION ALL
            SELECT 'sections', COUNT(*) FROM sections
        """
        data_counts = db.db.execute_query(data_counts_query)
        
        # Convert date objects to ISO format strings for JSON serialization
        for reg in recent_registrations:
            if 'date' in reg and reg['date']:
                reg['date'] = reg['date'].isoformat()
        
        return {
            'user_statistics': user_stats,
            'schedule_statistics': schedule_stats,
            'recent_registrations': recent_registrations,
            'data_counts': data_counts
        }
    except Exception as e:
        logger.error(f"Error getting system analytics: {e}")
        return {
            'user_statistics': [],
            'schedule_statistics': [],
            'recent_registrations': [],
            'data_counts': []
        }

def record_metric(metric_name: str, metric_value: float, metric_data: Dict = None) -> bool:
    """Record a system metric"""
    try:
        query = """
        INSERT INTO system_analytics (metric_name, metric_value, metric_data)
        VALUES (%s, %s, %s)
        """
        import json
        data_json = json.dumps(metric_data) if metric_data else None
        db.db.execute_single(query, (metric_name, metric_value, data_json))
        return True
    except Exception as e:
        logger.error(f"Error recording metric: {e}")
        return False

def get_metrics_history(metric_name: str, days: int = 30) -> List[Dict[str, Any]]:
    """Get historical metrics data"""
    try:
        query = """
        SELECT metric_value, metric_data, recorded_at
        FROM system_analytics 
        WHERE metric_name = %s AND recorded_at >= NOW() - INTERVAL '%s days'
        ORDER BY recorded_at DESC
        """
        return db.db.execute_query(query, (metric_name, days))
    except Exception as e:
        logger.error(f"Error getting metrics history: {e}")
        return []

# System Settings Functions
def get_system_setting(key: str, default_value: str = None) -> str:
    """Get a system setting value"""
    try:
        query = "SELECT setting_value FROM system_settings WHERE setting_key = %s"
        results = db.db.execute_query(query, (key,))
        return results[0]['setting_value'] if results else default_value
    except Exception as e:
        logger.error(f"Error getting system setting {key}: {e}")
        return default_value

def set_system_setting(key: str, value: str, setting_type: str = 'string', description: str = None, updated_by: str = None) -> bool:
    """Set a system setting value"""
    try:
        query = """
        INSERT INTO system_settings (setting_key, setting_value, setting_type, description, updated_by)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (setting_key) 
        DO UPDATE SET 
            setting_value = EXCLUDED.setting_value,
            setting_type = EXCLUDED.setting_type,
            description = EXCLUDED.description,
            updated_by = EXCLUDED.updated_by,
            updated_at = CURRENT_TIMESTAMP
        """
        db.db.execute_single(query, (key, value, setting_type, description, updated_by))
        return True
    except Exception as e:
        logger.error(f"Error setting system setting {key}: {e}")
        return False

def get_all_system_settings() -> List[Dict[str, Any]]:
    """Get all system settings"""
    try:
        query = """
        SELECT setting_key, setting_value, setting_type, description, updated_by, updated_at
        FROM system_settings 
        ORDER BY setting_key
        """
        results = db.db.execute_query(query)
        # Convert datetime objects to ISO format strings for JSON serialization
        for result in results:
            if 'updated_at' in result and result['updated_at']:
                result['updated_at'] = result['updated_at'].isoformat()
        return results
    except Exception as e:
        logger.error(f"Error getting all system settings: {e}")
        return []

def delete_system_setting(key: str) -> bool:
    """Delete a system setting"""
    try:
        query = "DELETE FROM system_settings WHERE setting_key = %s"
        db.db.execute_single(query, (key,))
        return True
    except Exception as e:
        logger.error(f"Error deleting system setting {key}: {e}")
        return False

def initialize_default_settings():
    """Initialize default system settings"""
    default_settings = [
        ('system_name', 'IntelliSched', 'string', 'Name of the scheduling system'),
        ('max_schedule_generations_per_day', '10', 'integer', 'Maximum number of schedule generations per user per day'),
        ('session_timeout_minutes', '30', 'integer', 'User session timeout in minutes'),
        ('enable_notifications', 'true', 'boolean', 'Enable system notifications'),
        ('maintenance_mode', 'false', 'boolean', 'Enable maintenance mode'),
        ('backup_frequency_hours', '24', 'integer', 'Backup frequency in hours'),
        ('email_notifications', 'true', 'boolean', 'Enable email notifications'),
        ('default_semester', '1', 'integer', 'Default semester for schedule generation'),
        ('default_sections', '3', 'integer', 'Default number of sections for schedule generation'),
        ('max_file_upload_size_mb', '10', 'integer', 'Maximum file upload size in MB'),
        ('auto_approve_schedules', 'false', 'boolean', 'Automatically approve schedules without dean review')
    ]
    
    for key, value, setting_type, description in default_settings:
        # Only insert if setting doesn't exist
        existing = get_system_setting(key)
        if not existing:
            set_system_setting(key, value, setting_type, description, 'system')
            logger.info(f"Initialized default setting: {key} = {value}")

# Initialize default settings when module is imported
initialize_default_settings()
