# Alembic Migration Consolidation

This directory contains a consolidated migration file that represents the complete database schema. The consolidation was performed to reduce the number of migration files and simplify the migration history.

## What Changed

- All individual migration files have been consolidated into a single file: `versions/consolidated_migration.py`
- The `alembic_version` table needs to be updated to point to the new consolidated migration

## How to Apply the Changes

1. Make sure your database is up-to-date with all previous migrations
2. Run the update script to update the alembic_version table:

```bash
python migrations/update_alembic_version.py
```

## Future Migrations

For future schema changes, create new migration files as usual with:

```bash
alembic revision --autogenerate -m "description of changes"
```

These new migrations will use the consolidated migration as their base.

## Troubleshooting

If you encounter issues with the consolidated migration:

1. Check that the database URL in `update_alembic_version.py` matches your actual database connection
2. Verify that all tables in the consolidated migration match your expected schema
3. If necessary, you can manually update the alembic_version table in your database:
   ```sql
   DELETE FROM alembic_version;
   INSERT INTO alembic_version (version_num) VALUES ('consolidated_migration');
   ```