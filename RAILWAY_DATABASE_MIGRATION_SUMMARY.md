# Railway Database Migration Summary

## 🎯 Problem
The Railway PostgreSQL database still has columns named `subject_code` and `subject_id`, but the application code has been updated to use `course_code` and `course_id`.

## 🔧 Solution
I've created several migration scripts to rename the database columns on Railway:

### Files Created:
1. **`migrate_railway_simple.py`** - Full migration script with error handling
2. **`run_migration.py`** - Simple one-liner migration script  
3. **`migrate_railway.sql`** - Direct SQL commands
4. **`RAILWAY_MIGRATION_GUIDE.md`** - Complete deployment guide

## 🚀 How to Run the Migration on Railway

### Option 1: Railway Console (Recommended)
1. Go to your Railway project dashboard
2. Click on your PostgreSQL service
3. Go to "Data" tab → "Query"
4. Copy and paste this SQL:

```sql
-- Rename columns
ALTER TABLE cs_curriculum RENAME COLUMN subject_code TO course_code;
ALTER TABLE it_curriculum RENAME COLUMN subject_code TO course_code;
ALTER TABLE sections RENAME COLUMN subject_code TO course_code;

-- Update constraints
ALTER TABLE cs_curriculum DROP CONSTRAINT IF EXISTS cs_curriculum_subject_code_key;
ALTER TABLE cs_curriculum ADD CONSTRAINT cs_curriculum_course_code_key UNIQUE (course_code);
ALTER TABLE it_curriculum DROP CONSTRAINT IF EXISTS it_curriculum_subject_code_key;
ALTER TABLE it_curriculum ADD CONSTRAINT it_curriculum_course_code_key UNIQUE (course_code);
```

### Option 2: Railway CLI
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and connect
railway login
railway link

# Run migration
railway run python run_migration.py
```

### Option 3: Deploy Migration Script
1. Add `run_migration.py` to your Railway deployment
2. Run it as a one-time job in Railway

## ✅ What the Migration Does

1. **Renames Columns:**
   - `subject_code` → `course_code` in all tables
   - `subject_id` → `course_id` in all tables (if they exist)

2. **Updates Constraints:**
   - Drops old unique constraints on `subject_code`
   - Creates new unique constraints on `course_code`

3. **Preserves Data:**
   - All existing data is preserved
   - No data loss during migration

## 🔍 Verification

After migration, verify with this SQL:
```sql
-- Check that new columns exist
SELECT column_name, table_name 
FROM information_schema.columns 
WHERE table_name IN ('cs_curriculum', 'it_curriculum', 'sections')
AND column_name IN ('course_code', 'course_id')
ORDER BY table_name, column_name;
```

## ⚠️ Important Notes

- **Backup First**: Always backup your Railway database before migration
- **Test Locally**: The migration scripts work locally (tested successfully)
- **Monitor Logs**: Watch Railway logs during migration
- **Deploy Code**: After migration, deploy your updated application code

## 🎉 Expected Result

After successful migration:
- Railway database will have `course_code` and `course_id` columns
- Your application will work correctly with the new column names
- All functionality will be preserved
- No more import errors or database column mismatches

## 📞 Next Steps

1. **Run the migration** using one of the options above
2. **Deploy your updated application code** to Railway
3. **Test the application** to ensure everything works
4. **Verify** that courses are loading correctly in the web interface

The migration is straightforward and the scripts are ready to use!
