# Database Migration Guide

This guide covers database migration best practices, common issues, and procedures for the SAPNA CARTING Fleet Management System.

## Table of Contents

1. [Understanding Django Migrations](#understanding-django-migrations)
2. [Creating Migrations](#creating-migrations)
3. [Applying Migrations](#applying-migrations)
4. [Rollback Procedures](#rollback-procedures)
5. [Common Issues and Solutions](#common-issues-and-solutions)
6. [Best Practices](#best-practices)

---

## Understanding Django Migrations

Django migrations are Python files that describe changes to your database schema. They provide:

- Version control for your database schema
- Automated way to apply schema changes
- Ability to rollback changes if needed

### Migration Files Location

```
fleet/migrations/
├── __init__.py
├── 0001_initial.py          # Initial schema
├── 0002_add_truck_fields.py # Subsequent changes
└── 0003_add_index.py        # Performance optimization
```

> **Note:** Migration files (0*.py) are excluded from git via `.gitignore`. They should be generated during deployment.

### Migration Naming Convention

- `0001_initial.py` - First migration (auto-generated)
- `0002_description.py` - Auto-generated descriptive name
- `00XX_add_xxx.py` - Adding fields/tables
- `00XX_remove_xxx.py` - Removing fields/tables
- `00XX_alter_xxx.py` - Modifying fields

---

## Creating Migrations

### Automatic Migration Creation

After changing your models (`models.py`), run:

```bash
# Create migrations for specific app
python manage.py makemigrations fleet

# Create migrations for all apps
python manage.py makemigrations

# Dry run (show what would be created)
python manage.py makemigrations --dry-run
```

### Manual Migration Creation

For complex migrations (data migrations, custom operations):

```bash
# Create empty migration
python manage.py makemigrations --empty fleet

# Create named empty migration
python manage.py makemigrations --empty fleet --name add_indexes
```

### Data Migrations

To migrate data (not just schema):

```python
# Generated migration file
from django.db import migrations


def forwards_func(apps, schema_editor):
    """Code to run during migration."""
    Truck = apps.get_model('fleet', 'Truck')
    # Example: Populate new field from existing data
    for truck in Truck.objects.all():
        truck.new_field = truck.old_field
        truck.save()


def reverse_func(apps, schema_editor):
    """Code to run during rollback."""
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('fleet', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(forwards_func, reverse_func),
    ]
```

---

## Applying Migrations

### Local Development

```bash
# Apply all pending migrations
python manage.py migrate

# Apply migrations for specific app
python manage.py migrate fleet

# Apply migrations up to specific version
python manage.py migrate fleet 0002

# Dry run (show SQL without executing)
python manage.py migrate --plan
```

### Production Deployment

**Pre-migration Checklist:**

1. **Backup Database**
   ```bash
   python manage.py backup_database --format json --compress
   ```

2. **Test Migrations Locally**
   ```bash
   # On a copy of production data
   python manage.py migrate
   ```

3. **Check for Irreversible Migrations**
   ```bash
   python manage.py migrate --plan
   # Look for any that don't have reverse_code
   ```

4. **Prepare Rollback Plan**
   - Note current migration version
   - Ensure backup is restorable

**Production Migration:**

```bash
# Via Railway
railway run python manage.py migrate

# Or automatically via Procfile (release phase)
```

**Post-migration Verification:**

```bash
# Check migration status
python manage.py showmigrations

# Verify application functionality
# Run smoke tests
# Check error logs
```

---

## Rollback Procedures

### Identifying Current State

```bash
# Show migration status for all apps
python manage.py showmigrations

# Show specific app
python manage.py showmigrations fleet

# Show SQL for a migration
python manage.py sqlmigrate fleet 0002
```

### Rolling Back Migrations

```bash
# Roll back specific migration
python manage.py migrate fleet 0001

# Roll back all migrations for an app
python manage.py migrate fleet zero

# Roll back multiple apps
python manage.py migrate fleet 0001 operations 0002
```

### Rollback with Data Loss

⚠️ **WARNING:** Some migrations cannot be rolled back without data loss.

**Before rolling back:**
1. Check if migration is reversible
2. Backup critical data
3. Plan data recovery if needed

```bash
# Check if migration has reverse operation
python manage.py migrate --plan

# Try rollback (will fail if irreversible)
python manage.py migrate fleet 0001
```

**Emergency Rollback with Database Restore:**

If rollback fails or causes issues:

```bash
# Restore from backup
python manage.py restore_database --backup-file backups/backup_YYYYMMDD_HHMMSS.json
```

---

## Common Issues and Solutions

### Issue: Migration Conflicts

**Symptoms:**
```
Conflicting migrations detected; multiple leaf nodes in migration graph
```

**Solution:**
```bash
# Show migration graph
python manage.py showmigrations

# Option 1: Merge migrations
python manage.py makemigrations --merge

# Option 2: Fix manually by editing dependencies
# In migration files, ensure correct dependencies:
dependencies = [
    ('fleet', '0003_correct_migration'),  # Not 0002
]
```

### Issue: "No migrations to apply"

**Symptoms:**
```
No migrations to apply, but models have changes
```

**Solution:**
```bash
# Force recreation of migrations
python manage.py makemigrations fleet

# If migration already exists but not detected:
python manage.py migrate --fake fleet zero
python manage.py migrate fleet
```

### Issue: Migration Fails in Production

**Common Causes:**
1. Data doesn't meet new constraints
2. Missing default values
3. Lock timeout on large tables

**Solutions:**

```bash
# 1. Check for data issues
python manage.py shell
# Query for data that violates new constraints

# 2. Add default value temporarily
# Edit migration to add default

# 3. For large tables, use separate operations
# Consider manual SQL for large table changes
```

### Issue: "Table already exists"

**Symptoms:**
```
django.db.utils.ProgrammingError: relation "fleet_truck" already exists
```

**Solution:**
```bash
# Fake the initial migration
python manage.py migrate --fake fleet 0001

# Then apply real migrations
python manage.py migrate
```

### Issue: Circular Dependency

**Symptoms:**
```
CircularDependencyError: Circular dependency detected
```

**Solution:**
1. Identify circular imports in models.py
2. Use string references for ForeignKeys:
   ```python
   # Instead of:
   truck = models.ForeignKey(Truck, ...)
   
   # Use:
   truck = models.ForeignKey('fleet.Truck', ...)
   ```

### Issue: Migration is Too Slow

**For large tables:**

```python
# Use RunSQL with CONCURRENTLY for PostgreSQL
from django.db import migrations


class Migration(migrations.Migration):
    atomic = False  # Allow non-atomic operations
    
    operations = [
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY ...",
            reverse_sql="DROP INDEX ..."
        ),
    ]
```

---

## Best Practices

### 1. Always Backup Before Production Migrations

```bash
# Automated in deployment script
python manage.py backup_database --format json --compress
python manage.py migrate
```

### 2. Test Migrations on Production-like Data

- Use a copy of production database
- Test migration time (important for large tables)
- Verify application works after migration

### 3. Keep Migrations Reversible

```python
# Always provide reverse_code
def forwards(apps, schema_editor):
    pass

def backwards(apps, schema_editor):
    pass

migrations.RunPython(forwards, backwards)
```

### 4. One Logical Change Per Migration

**Good:**
- Migration 1: Add new field
- Migration 2: Populate new field
- Migration 3: Make field non-nullable

**Bad:**
- Migration 1: Add field, populate, make non-nullable

### 5. Don't Edit Existing Migrations

- Never edit migrations that have been applied
- Create new migrations to fix issues

### 6. Use Data Migrations for Data Changes

```python
# Don't do this in shell scripts
# Do this in migrations for version control
```

### 7. Squash Migrations Periodically

```bash
# Combine multiple migrations into one
python manage.py squashmigrations fleet 0001 0010
```

### 8. Handle Large Tables Carefully

```python
class Migration(migrations.Migration):
    atomic = False  # For PostgreSQL
    
    operations = [
        # Use CONCURRENTLY for index creation
        migrations.AddIndex(
            model_name='largemodel',
            index=models.Index(...),
        ),
    ]
```

### 9. Document Complex Migrations

```python
class Migration(migrations.Migration):
    """
    Migration to split Truck.status into status and sub_status.
    
    Data mapping:
    - ACTIVE -> status=ACTIVE, sub_status=None
    - MAINTENANCE_SCHEDULED -> status=MAINTENANCE, sub_status=SCHEDULED
    """
    ...
```

### 10. Monitor Migration Performance

```bash
# Time the migration
time python manage.py migrate

# Monitor database during migration
# Check for locks, long-running queries
```

---

## Migration Checklist

### Before Creating Migrations

- [ ] Models are correctly defined
- [ ] All changes are intentional
- [ ] Relationships use string references if circular
- [ ] Default values provided for non-nullable fields

### Before Applying to Production

- [ ] Database backed up
- [ ] Migrations tested locally
- [ ] Rollback plan prepared
- [ ] Maintenance window scheduled (if needed)
- [ ] Team notified

### After Applying

- [ ] Migration status verified
- [ ] Application smoke tests pass
- [ ] Error logs checked
- [ ] Performance monitored
- [ ] Team notified of completion

---

## Quick Reference Commands

```bash
# Create migration
python manage.py makemigrations fleet

# Apply migrations
python manage.py migrate

# Show status
python manage.py showmigrations

# Rollback one migration
python manage.py migrate fleet 0001

# Rollback all
python manage.py migrate fleet zero

# Fake migration (mark as applied without running)
python manage.py migrate --fake fleet 0001

# SQL for migration
python manage.py sqlmigrate fleet 0002

# Check for issues
python manage.py check
python manage.py migrate --plan
```

---

## Related Documentation

- [Django Migrations](https://docs.djangoproject.com/en/5.0/topics/migrations/)
- [MAINTENANCE.md](MAINTENANCE.md) - Production maintenance procedures
- [Database Backup/Restore](MAINTENANCE.md#database-management)

---

*Last Updated: February 2024*