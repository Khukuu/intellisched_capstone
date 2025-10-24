# Railway Database Migration Guide

This guide explains how to migrate the Railway PostgreSQL database from `subject_*` to `course_*` column names.

## Option 1: Run Migration Script (Recommended)

### Step 1: Deploy the Migration Script
1. Make sure `migrate_railway_simple.py` is in your Railway deployment
2. The script uses the existing database connection from your app

### Step 2: Run the Migration
```bash
# In Railway console or locally with Railway environment variables
python migrate_railway_simple.py
```

## Option 2: Direct SQL Migration

### Step 1: Connect to Railway Database
1. Go to your Railway project dashboard
2. Click on your PostgreSQL service
3. Go to the "Data" tab
4. Click "Query" to open the SQL editor

### Step 2: Run the SQL Migration
Copy and paste the contents of `migrate_railway.sql` into the SQL editor and execute it.

## Option 3: Using Railway CLI

### Step 1: Install Railway CLI
```bash
npm install -g @railway/cli
```

### Step 2: Connect to Your Project
```bash
railway login
railway link
```

### Step 3: Run Migration Script
```bash
railway run python migrate_railway_simple.py
```

## Verification

After running the migration, verify the changes:

```sql
-- Check that old columns are gone
SELECT column_name, table_name 
FROM information_schema.columns 
WHERE table_name IN ('cs_curriculum', 'it_curriculum', 'sections')
AND column_name IN ('subject_code', 'subject_id');

-- Check that new columns exist
SELECT column_name, table_name 
FROM information_schema.columns 
WHERE table_name IN ('cs_curriculum', 'it_curriculum', 'sections')
AND column_name IN ('course_code', 'course_id');
```

## Expected Results

After successful migration:
- `subject_code` → `course_code` in all tables
- `subject_id` → `course_id` in all tables (if they existed)
- Unique constraints updated to use new column names
- All data preserved

## Troubleshooting

### If Migration Fails
1. Check that you have the necessary permissions
2. Ensure no active connections are using the old column names
3. Check the Railway logs for detailed error messages

### If Columns Already Exist
The migration script will skip columns that have already been renamed.

### Rollback (if needed)
If you need to rollback the changes:
```sql
-- Rename columns back (NOT RECOMMENDED)
ALTER TABLE cs_curriculum RENAME COLUMN course_code TO subject_code;
ALTER TABLE it_curriculum RENAME COLUMN course_code TO subject_code;
ALTER TABLE sections RENAME COLUMN course_code TO subject_code;
```

## Important Notes

- **Backup First**: Always backup your database before running migrations
- **Test Locally**: Test the migration on a local copy first
- **Monitor Logs**: Watch Railway logs during migration
- **Verify Data**: After migration, verify that your application works correctly

## After Migration

1. Deploy your updated application code
2. Test all functionality
3. Verify that courses are loading correctly
4. Check that the web interface displays course information properly
