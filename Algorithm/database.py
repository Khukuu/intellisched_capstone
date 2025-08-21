import psycopg2
from psycopg2.extras import RealDictCursor
import os
from typing import List, Dict, Any

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
        """
        
        # Split and execute each statement
        statements = create_tables_sql.split(';')
        for statement in statements:
            if statement.strip():
                self.db.execute_single(statement)
    
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

def add_subject(subject_data: Dict[str, Any]) -> None:
    """Add a new subject to the database"""
    db.insert_subject(subject_data)

def add_teacher(teacher_data: Dict[str, Any]) -> None:
    """Add a new teacher to the database"""
    db.insert_teacher(teacher_data)

def add_room(room_data: Dict[str, Any]) -> None:
    """Add a new room to the database"""
    db.insert_room(room_data)

def update_subject(subject_code: str, subject_data: Dict[str, Any]) -> None:
    """Update an existing subject in the database"""
    db.insert_subject(subject_data)  # Uses ON CONFLICT DO UPDATE

def update_teacher(teacher_id: str, teacher_data: Dict[str, Any]) -> None:
    """Update an existing teacher in the database"""
    db.insert_teacher(teacher_data)  # Uses ON CONFLICT DO UPDATE

def update_room(room_id: str, room_data: Dict[str, Any]) -> None:
    """Update an existing room in the database"""
    db.insert_room(room_data)  # Uses ON CONFLICT DO UPDATE

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
