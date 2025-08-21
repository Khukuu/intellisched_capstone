-- schema.sql

-- 1. Create the database
CREATE DATABASE intellisched;

-- Switch into the database
\c intellisched;

-- 2. Table: cs_curriculum
CREATE TABLE cs_curriculum (
    subject_code VARCHAR(20) PRIMARY KEY,
    subject_name VARCHAR(150) NOT NULL,
    lecture_hours_per_week INT NOT NULL,
    lab_hours_per_week INT NOT NULL,
    units INT NOT NULL,
    semester VARCHAR(20) NOT NULL,              -- e.g. "1st", "2nd"
    program_specialization VARCHAR(100),        -- e.g. "Data Science", "AI"
    year_level INT NOT NULL                     -- e.g. 1, 2, 3, 4
);

-- 3. Table: rooms
CREATE TABLE rooms (
    room_id SERIAL PRIMARY KEY,
    room_name VARCHAR(50) UNIQUE NOT NULL,
    is_laboratory BOOLEAN NOT NULL
);

-- 4. Table: teachers
CREATE TABLE teachers (
    teacher_id SERIAL PRIMARY KEY,
    teacher_name VARCHAR(100) NOT NULL,
    can_teach TEXT[] NOT NULL                   -- Array of subject codes
);
