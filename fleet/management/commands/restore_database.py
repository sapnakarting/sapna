import gzip
import json
import os
import subprocess
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import connection


class Command(BaseCommand):
    help = 'Restore the database from a backup file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--backup-file',
            type=str,
            required=True,
            help='Path to the backup file (JSON or SQL)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview what would be restored without making changes'
        )
        parser.add_argument(
            '--no-input',
            action='store_true',
            help='Bypass confirmation prompts'
        )
        parser.add_argument(
            '--append',
            action='store_true',
            help='Append data without clearing existing data (may cause conflicts)'
        )
        parser.add_argument(
            '--database',
            type=str,
            default='default',
            help='Database alias to restore to (default: default)'
        )

    def handle(self, *args, **options):
        backup_file = Path(options['backup_file'])
        dry_run = options['dry_run']
        no_input = options['no_input']
        append = options['append']
        database = options['database']

        if not backup_file.exists():
            raise CommandError(f'Backup file not found: {backup_file}')

        # Detect file format
        is_compressed = backup_file.suffix == '.gz'
        is_sql = 'sql' in backup_file.suffixes or backup_file.suffix == '.dump'
        is_json = 'json' in backup_file.suffixes or backup_file.suffix == '.json'

        if not is_sql and not is_json:
            # Try to detect from content
            if is_compressed:
                with gzip.open(backup_file, 'rt') as f:
                    first_line = f.readline()
            else:
                with open(backup_file, 'r') as f:
                    first_line = f.readline()
            
            is_json = first_line.strip().startswith('[') or first_line.strip().startswith('{')
            is_sql = not is_json

        self.stdout.write(f'Backup file: {backup_file}')
        self.stdout.write(f'Format: {"SQL" if is_sql else "JSON"}')
        self.stdout.write(f'Compressed: {is_compressed}')

        if dry_run:
            self.preview_restore(backup_file, is_sql, is_json, is_compressed)
            return

        # Confirmation
        if not no_input:
            action = 'append to' if append else 'REPLACE ALL DATA in'
            confirm = input(f'\nWARNING: This will {action} the database. Are you sure? (yes/no): ')
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.WARNING('Restore cancelled.'))
                return

        try:
            if is_sql:
                self.restore_sql(backup_file, is_compressed, database)
            else:
                self.restore_json(backup_file, is_compressed, append, database)
            
            self.stdout.write(self.style.SUCCESS('Database restore completed successfully!'))
            
        except Exception as e:
            raise CommandError(f'Restore failed: {str(e)}')

    def preview_restore(self, backup_file, is_sql, is_json, is_compressed):
        """Preview what would be restored."""
        self.stdout.write(self.style.WARNING('\n=== RESTORE PREVIEW ==='))
        
        if is_json:
            # Extract and show data summary
            try:
                if is_compressed:
                    with gzip.open(backup_file, 'rt') as f:
                        data = json.load(f)
                else:
                    with open(backup_file, 'r') as f:
                        data = json.load(f)
                
                # Count objects by model
                model_counts = {}
                for obj in data:
                    model = obj.get('model', 'unknown')
                    model_counts[model] = model_counts.get(model, 0) + 1
                
                self.stdout.write(f'Total objects: {len(data)}')
                self.stdout.write('\nObjects by model:')
                for model, count in sorted(model_counts.items()):
                    self.stdout.write(f'  {model}: {count}')
                    
            except json.JSONDecodeError as e:
                self.stdout.write(self.style.ERROR(f'Error reading JSON: {e}'))
        else:
            self.stdout.write('SQL backup - preview not available.')
            self.stdout.write('The SQL file will be executed against the database.')

    def restore_json(self, backup_file, is_compressed, append, database):
        """Restore from JSON backup using loaddata."""
        self.stdout.write('Restoring from JSON backup...')
        
        # If not appending, we should clear data first
        if not append:
            self.stdout.write(self.style.WARNING('Clearing existing data...'))
            self.clear_database_data(database)

        # Extract if compressed
        if is_compressed:
            self.stdout.write('Decompressing backup file...')
            extracted_path = backup_file.with_suffix('')
            with gzip.open(backup_file, 'rb') as f_in:
                with open(extracted_path, 'wb') as f_out:
                    f_out.write(f_in.read())
            restore_path = extracted_path
        else:
            restore_path = backup_file

        try:
            # Use loaddata
            call_command('loaddata', str(restore_path), database=database, verbosity=1)
        finally:
            # Clean up extracted file
            if is_compressed and 'extracted_path' in locals():
                extracted_path.unlink(missing_ok=True)

    def restore_sql(self, backup_file, is_compressed, database):
        """Restore from SQL backup using psql."""
        db_settings = settings.DATABASES[database]
        
        if db_settings['ENGINE'] != 'django.db.backends.postgresql':
            raise CommandError('SQL restore is only supported for PostgreSQL databases.')

        # Parse database settings
        db_url = os.environ.get('DATABASE_URL', '')
        if db_url:
            import urllib.parse
            parsed = urllib.parse.urlparse(db_url)
            db_name = parsed.path[1:]
            db_user = parsed.username
            db_host = parsed.hostname
            db_port = parsed.port or 5432
            db_password = parsed.password
        else:
            db_name = db_settings.get('NAME')
            db_user = db_settings.get('USER')
            db_host = db_settings.get('HOST', 'localhost')
            db_port = db_settings.get('PORT', 5432)
            db_password = db_settings.get('PASSWORD')

        self.stdout.write('Restoring from SQL backup using psql...')

        # Build psql command
        cmd = [
            'psql',
            '--host', str(db_host),
            '--port', str(db_port),
            '--username', str(db_user),
            '--dbname', str(db_name),
            '--file', str(backup_file),
            '--verbose',
        ]

        try:
            env = os.environ.copy()
            if db_password:
                env['PGPASSWORD'] = db_password

            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                check=True
            )

            self.stdout.write(result.stdout)
            if result.stderr:
                self.stdout.write(self.style.WARNING(result.stderr))

        except subprocess.CalledProcessError as e:
            raise CommandError(f'psql restore failed: {e.stderr}')
        except FileNotFoundError:
            raise CommandError('psql not found. Please ensure PostgreSQL client tools are installed.')

    def clear_database_data(self, database):
        """Clear all data from the database while preserving tables."""
        with connection.cursor() as cursor:
            # Disable foreign key checks temporarily
            cursor.execute('SET CONSTRAINTS ALL DEFERRED')
            
            # Get all tables
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                AND table_name NOT LIKE 'django_%'
                AND table_name NOT LIKE 'auth_%'
                AND table_name != 'sqlite_sequence'
            """)
            
            tables = [row[0] for row in cursor.fetchall()]
            
            # Truncate tables
            for table in tables:
                try:
                    cursor.execute(f'TRUNCATE TABLE "{table}" CASCADE')
                    self.stdout.write(f'  Cleared table: {table}')
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'  Could not clear {table}: {e}'))

            # Also truncate auth tables except permissions and groups
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                AND table_name LIKE 'auth_%'
            """)
            
            auth_tables = [row[0] for row in cursor.fetchall()]
            
            for table in auth_tables:
                if table not in ['auth_permission', 'auth_group', 'auth_group_permissions']:
                    try:
                        cursor.execute(f'TRUNCATE TABLE "{table}" CASCADE')
                        self.stdout.write(f'  Cleared table: {table}')
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f'  Could not clear {table}: {e}'))
            
            cursor.execute('SET CONSTRAINTS ALL IMMEDIATE')