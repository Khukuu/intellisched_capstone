-- Migration script to add teacher availability days
-- This script adds an availability_days column to the teachers table

-- Add availability_days column to teachers table
-- This will store an array of days when the teacher is available
-- Days: 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'
ALTER TABLE teachers 
ADD COLUMN availability_days TEXT[] DEFAULT ARRAY['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

-- Update existing teachers to have all days available by default
UPDATE teachers 
SET availability_days = ARRAY['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'] 
WHERE availability_days IS NULL;

-- Add a comment to document the column
COMMENT ON COLUMN teachers.availability_days IS 'Array of days when teacher is available (Mon, Tue, Wed, Thu, Fri, Sat)';
