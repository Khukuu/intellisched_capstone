-- Railway Database Migration Script
-- Rename columns from subject_* to course_*

-- Check current schema
SELECT column_name, table_name 
FROM information_schema.columns 
WHERE table_name IN ('cs_curriculum', 'it_curriculum', 'sections')
AND column_name IN ('subject_code', 'subject_id', 'course_code', 'course_id')
ORDER BY table_name, column_name;

-- Rename columns in cs_curriculum table
ALTER TABLE cs_curriculum RENAME COLUMN subject_code TO course_code;
ALTER TABLE cs_curriculum RENAME COLUMN subject_id TO course_id;

-- Rename columns in it_curriculum table  
ALTER TABLE it_curriculum RENAME COLUMN subject_code TO course_code;
ALTER TABLE it_curriculum RENAME COLUMN subject_id TO course_id;

-- Rename columns in sections table
ALTER TABLE sections RENAME COLUMN subject_code TO course_code;
ALTER TABLE sections RENAME COLUMN subject_id TO course_id;

-- Update constraints
ALTER TABLE cs_curriculum DROP CONSTRAINT IF EXISTS cs_curriculum_subject_code_key;
ALTER TABLE cs_curriculum ADD CONSTRAINT cs_curriculum_course_code_key UNIQUE (course_code);

ALTER TABLE it_curriculum DROP CONSTRAINT IF EXISTS it_curriculum_subject_code_key;
ALTER TABLE it_curriculum ADD CONSTRAINT it_curriculum_course_code_key UNIQUE (course_code);

-- Verify the changes
SELECT column_name, table_name 
FROM information_schema.columns 
WHERE table_name IN ('cs_curriculum', 'it_curriculum', 'sections')
AND column_name IN ('course_code', 'course_id')
ORDER BY table_name, column_name;
