# PostgreSQL Migration Guide

This guide explains how to migrate from CSV files to PostgreSQL database for the IntelliSched application.

## Prerequisites

1. **PostgreSQL Database**: Make sure you have PostgreSQL installed and running
2. **Database Creation**: Create a database named `intellisched`
3. **User Permissions**: Ensure the PostgreSQL user has proper permissions

## Database Setup

### 1. Create Database
```sql
CREATE DATABASE intellisched;
```

### 2. Connection String
The application uses the following connection string:
```
postgresql://postgres:asdf1234@localhost:5432/intellisched
```

**Components:**
- **Username**: `postgres`
- **Password**: `asdf1234`
- **Host**: `localhost`
- **Port**: `5432`
- **Database**: `intellisched`

## Migration Steps

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Migration Script
```bash
python migrate_to_db.py
```

This script will:
- Test the database connection
- Create necessary tables (subjects, teachers, rooms)
- Migrate data from CSV files to PostgreSQL
- Verify the migration was successful

### 3. Verify Migration
The migration script will show:
- Number of subjects migrated
- Number of teachers migrated
- Number of rooms migrated
- Sample data verification

## Database Schema

### Subjects Table
```sql
CREATE TABLE subjects (
    id SERIAL PRIMARY KEY,
    subject_code VARCHAR(20) UNIQUE NOT NULL,
    subject_name VARCHAR(255) NOT NULL,
    lecture_hours_per_week DECIMAL(4,2) DEFAULT 0,
    lab_hours_per_week DECIMAL(4,2) DEFAULT 0,
    units INTEGER NOT NULL,
    semester INTEGER,
    program_specialization VARCHAR(50),
    year_level INTEGER
);
```

### Teachers Table
```sql
CREATE TABLE teachers (
    id SERIAL PRIMARY KEY,
    teacher_id VARCHAR(20) UNIQUE NOT NULL,
    teacher_name VARCHAR(255) NOT NULL,
    can_teach TEXT
);
```

### Rooms Table
```sql
CREATE TABLE rooms (
    id SERIAL PRIMARY KEY,
    room_id VARCHAR(20) UNIQUE NOT NULL,
    room_name VARCHAR(255) NOT NULL,
    is_laboratory BOOLEAN DEFAULT FALSE
);
```

## Application Changes

The following files have been updated to use PostgreSQL:

1. **`database.py`** - New database connection and operations module
2. **`scheduler.py`** - Updated to load data from database instead of CSV
3. **`app.py`** - Updated API endpoints to use database
4. **`main.py`** - Updated to load data from database
5. **`main - Copy.py`** - Updated to load data from database

## Running the Application

After successful migration, run the application as usual:

```bash
python app.py
```

The application will now use PostgreSQL instead of CSV files for all data operations.

## Troubleshooting

### Connection Issues
- Verify PostgreSQL is running: `pg_ctl status`
- Check connection string in `database.py`
- Ensure database exists: `psql -l | grep intellisched`

### Permission Issues
- Grant necessary permissions to the PostgreSQL user
- Check if the user can create tables and insert data

### Data Issues
- Verify CSV files are in the correct format
- Check for encoding issues in CSV files
- Ensure all required fields are present

## Benefits of PostgreSQL Migration

1. **Better Performance**: Faster data retrieval and processing
2. **Data Integrity**: ACID compliance and constraint enforcement
3. **Scalability**: Better handling of large datasets
4. **Concurrent Access**: Multiple users can access data simultaneously
5. **Backup & Recovery**: Built-in backup and recovery mechanisms
6. **Query Flexibility**: Advanced SQL queries and data analysis

## Rollback (if needed)

If you need to revert to CSV files:
1. Keep the original CSV files as backup
2. Update the import statements in the modified files
3. Restore the original CSV loading logic

## Support

For issues with the migration:
1. Check the migration script output for error messages
2. Verify database connectivity
3. Ensure all dependencies are installed
4. Check PostgreSQL logs for database-specific errors

