import psycopg2
from psycopg2.extras import RealDictCursor
import os
from typing import List, Dict, Any
import hashlib
import secrets

class DatabaseManager:
    def __init__(self, connection_string: str = None):
        self.connection_string = connection_string or "postgresql://postgres:asdf1234@localhost:5432/intellisched"
        
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
        
        CREATE TABLE IF NOT EXISTS teachers (
            id SERIAL PRIMARY KEY,
            teacher_id VARCHAR(20) UNIQUE NOT NULL,
            teacher_name VARCHAR(255) NOT NULL,
            can_teach TEXT
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
            email VARCHAR(255),
            role VARCHAR(20) DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        );
        """
        
        # Split and execute each statement
        statements = create_tables_sql.split(';')
        for statement in statements:
            if statement.strip():
                self.db.execute_single(statement)
        
        # Check if users table has correct structure
        if not self._check_users_table_structure():
            print("⚠️ Users table structure is incorrect. Attempting to fix...")
            if self._fix_users_table():
                print("✅ Users table structure fixed successfully")
            else:
                print("❌ Failed to fix users table structure. Please run fix_users_table.py manually.")
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
            print(f"Error checking table structure: {e}")
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
            print(f"Error fixing users table: {e}")
            return False
    
    def create_default_admin(self):
        """Create default admin and chair users if they don't exist"""
        try:
            # Check if admin user exists
            existing_admin = self.db.execute_query("SELECT id FROM users WHERE username = %s", ('admin',))
            if not existing_admin:
                # Create default admin user
                password = "admin123"
                salt = secrets.token_hex(16)
                password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
                
                self.db.execute_single("""
                    INSERT INTO users (username, password_hash, salt, full_name, email, role)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, ('admin', password_hash, salt, 'Administrator', 'admin@intellisched.com', 'admin'))
                
                print("✅ Default admin user created (username: admin, password: admin123)")
            
            # Check if chair user exists
            existing_chair = self.db.execute_query("SELECT id FROM users WHERE username = %s", ('chair',))
            if not existing_chair:
                # Create default chair user
                password = "chair123"
                salt = secrets.token_hex(16)
                password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
                
                self.db.execute_single("""
                    INSERT INTO users (username, password_hash, salt, full_name, email, role)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, ('chair', password_hash, salt, 'Department Chair', 'chair@intellisched.com', 'chair'))
                
                print("✅ Default chair user created (username: chair, password: chair123)")
                
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
                # Update last login
                self.db.execute_single("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s", (user['id'],))
                
                # Return user info (without sensitive data)
                return {
                    'id': user['id'],
                    'username': user['username'],
                    'full_name': user['full_name'],
                    'email': user['email'],
                    'role': user['role']
                }
            return None
        except Exception as e:
            print(f"Error verifying credentials: {e}")
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
            user = self.db.execute_query("SELECT id, username, full_name, email, role, created_at, last_login FROM users WHERE username = %s", (username,))
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
                INSERT INTO users (username, password_hash, salt, full_name, email, role)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                user_data['username'],
                password_hash,
                salt,
                user_data.get('full_name', ''),
                user_data.get('email', ''),
                user_data.get('role', 'user')
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
    
    def load_subjects(self) -> List[Dict[str, Any]]:
        """Load all subjects from database"""
        query = """
        SELECT 
            subject_code,
            subject_name,
            lecture_hours_per_week,
            lab_hours_per_week,
            units,
            semester,
            program_specialization,
            year_level
        FROM cs_curriculum
        ORDER BY year_level, semester, subject_code
        """
        return self.db.execute_query(query)
    
    def load_teachers(self) -> List[Dict[str, Any]]:
        """Load all teachers from database"""
        query = """
        SELECT 
            teacher_id,
            teacher_name,
            can_teach
        FROM teachers
        ORDER BY teacher_name
        """
        return self.db.execute_query(query)
    
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
    
    def insert_teacher(self, teacher_data: Dict[str, Any]) -> None:
        """Insert a single teacher"""
        query = """
        INSERT INTO teachers (teacher_id, teacher_name, can_teach)
        VALUES (%s, %s, %s)
        ON CONFLICT (teacher_id) DO UPDATE SET
            teacher_name = EXCLUDED.teacher_name,
            can_teach = EXCLUDED.can_teach
        """
        params = (
            teacher_data['teacher_id'],
            teacher_data['teacher_name'],
            teacher_data.get('can_teach', '')
        )
        self.db.execute_single(query, params)
    
    def insert_room(self, room_data: Dict[str, Any]) -> None:
        """Insert a single room"""
        query = """
        INSERT INTO rooms (room_id, room_name, is_laboratory)
        VALUES (%s, %s, %s)
        ON CONFLICT (room_id) DO UPDATE SET
            room_name = EXCLUDED.room_name,
            is_laboratory = EXCLUDED.is_laboratory
        """
        params = (
            room_data['room_id'],
            room_data['room_name'],
            room_data.get('is_laboratory', False)
        )
        self.db.execute_single(query, params)
    
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

def load_subjects_from_db():
    """Load subjects from database (replaces CSV loading)"""
    return db.load_subjects()

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
    """Add a new subject to the database"""
    db.insert_subject(subject_data)

def add_teacher(teacher_data: Dict[str, Any]) -> None:
    """Add a new teacher to the database"""
    db.insert_teacher(teacher_data)

def add_room(room_data: Dict[str, Any]) -> None:
    """Add a new room to the database"""
    db.insert_room(room_data)
 
def add_section(section_data: Dict[str, Any]) -> None:
    """Add a new section to the database"""
    db.insert_section(section_data)

def update_subject(subject_code: str, subject_data: Dict[str, Any]) -> None:
    """Update an existing subject in the database"""
    db.insert_subject(subject_data)  # Uses ON CONFLICT DO UPDATE

def update_teacher(teacher_id: str, teacher_data: Dict[str, Any]) -> None:
    """Update an existing teacher in the database"""
    db.insert_teacher(teacher_data)  # Uses ON CONFLICT DO UPDATE

def update_room(room_id: str, room_data: Dict[str, Any]) -> None:
    """Update an existing room in the database"""
    db.insert_room(room_data)  # Uses ON CONFLICT DO UPDATE
 
def update_section(section_id: str, section_data: Dict[str, Any]) -> None:
    """Update an existing section in the database"""
    db.insert_section(section_data)  # Uses ON CONFLICT DO UPDATE

def delete_subject(subject_code: str) -> None:
    """Delete a subject from the database"""
    query = "DELETE FROM cs_curriculum WHERE subject_code = %s"
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
