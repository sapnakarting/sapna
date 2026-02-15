import gzip
import json
import os
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings


class Command(BaseCommand):
    help = 'Backup the database to a JSON or SQL file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            type=str,
            help='Output file path (default: backups/backup_YYYYMMDD_HHMMSS.json)'
        )
        parser.add_argument(
            '--format',
            type=str,
            choices=['json', 'sql'],
            default='json',
            help='Backup format: json (Django dumpdata) or sql (pg_dump for PostgreSQL)'
        )
        parser.add_argument(
            '--compress',
            action='store_true',
            help='Compress the backup using gzip'
        )
        parser.add_argument(
            '--exclude',
            type=str,
            nargs='+',
            default=['auth.Permission', 'admin.LogEntry', 'sessions.Session', 'contenttypes.ContentType'],
            help='Models to exclude from backup (default: auth.Permission, admin.LogEntry, sessions.Session)'
        )
        parser.add_argument(
            '--models',
            type=str,
            nargs='+',
            help='Specific models to backup (format: app_label.ModelName)'
        )
        parser.add_argument(
            '--natural-primary',
            action='store_true',
            help='Use natural primary keys'
        )
        parser.add_argument(
            '--natural-foreign',
            action='store_true',
            help='Use natural foreign keys'
        )

    def handle(self, *args, **options):
        output_path = options['output']
        format_type = options['format']
        compress = options['compress']
        exclude = options['exclude']
        models = options['models']
        natural_primary = options['natural_primary']
        natural_foreign = options['natural_foreign']

        # Create backup directory
        backup_dir = Path(settings.BASE_DIR) / 'backups'
        backup_dir.mkdir(exist_ok=True)

        # Generate default filename if not provided
        if not output_path:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            extension = 'sql' if format_type == 'sql' else 'json'
            output_path = backup_dir / f'backup_{timestamp}.{extension}'
        else:
            output_path = Path(output_path)

        if format_type == 'json':
            self.backup_json(output_path, compress, exclude, models, natural_primary, natural_foreign)
        else:
            self.backup_sql(output_path, compress)

    def backup_json(self, output_path, compress, exclude, models, natural_primary, natural_foreign):
        """Backup database using Django's dumpdata command."""
        self.stdout.write(f'Creating JSON backup to {output_path}...')

        # Build dumpdata arguments
        dump_args = ['dumpdata']
        
        if natural_primary or natural_foreign:
            dump_args.append('--natural-primary' if natural_primary else '--natural-foreign')
        else:
            dump_args.extend(['--natural-primary', '--natural-foreign'])
        
        # Add excludes
        for model in exclude:
            dump_args.extend(['--exclude', model])
        
        # Add specific models if provided
        if models:
            dump_args.extend(models)
        else:
            dump_args.extend(['fleet', 'operations', 'settings_app', 'auth.User'])

        # Create temporary file
        if compress:
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
            temp_path = temp_file.name
            temp_file.close()
        else:
            temp_path = str(output_path)

        dump_args.extend(['--indent', '2'])
        dump_args.extend(['--output', temp_path])

        try:
            call_command(*dump_args)
            
            if compress:
                compressed_path = str(output_path) + '.gz'
                self.stdout.write(f'Compressing to {compressed_path}...')
                
                with open(temp_path, 'rb') as f_in:
                    with gzip.open(compressed_path, 'wb') as f_out:
                        f_out.writelines(f_in)
                
                os.unlink(temp_path)
                final_path = compressed_path
            else:
                final_path = str(output_path)

            # Get file size
            file_size = os.path.getsize(final_path)
            file_size_mb = file_size / (1024 * 1024)

            self.stdout.write(self.style.SUCCESS(
                f'Backup created successfully: {final_path}\n'
                f'  Size: {file_size_mb:.2f} MB ({file_size:,} bytes)'
            ))

            # Log backup metadata
            self.log_backup_metadata(final_path, 'json', file_size)

        except Exception as e:
            if compress and os.path.exists(temp_path):
                os.unlink(temp_path)
            raise CommandError(f'Backup failed: {str(e)}')

    def backup_sql(self, output_path, compress):
        """Backup database using pg_dump (PostgreSQL only)."""
        db_settings = settings.DATABASES['default']
        
        if db_settings['ENGINE'] != 'django.db.backends.postgresql':
            raise CommandError('SQL backup is only supported for PostgreSQL databases.')

        # Parse database URL or use individual settings
        db_url = db_settings.get('URL', '')
        if db_url:
            import urllib.parse
            parsed = urllib.parse.urlparse(db_url)
            db_name = parsed.path[1:]
            db_user = parsed.username
            db_host = parsed.hostname
            db_port = parsed.port or 5432
        else:
            db_name = db_settings.get('NAME')
            db_user = db_settings.get('USER')
            db_host = db_settings.get('HOST', 'localhost')
            db_port = db_settings.get('PORT', 5432)

        if compress:
            output_path = str(output_path) + '.gz'

        self.stdout.write(f'Creating SQL backup using pg_dump to {output_path}...')

        # Build pg_dump command
        cmd = [
            'pg_dump',
            '--host', str(db_host),
            '--port', str(db_port),
            '--username', str(db_user),
            '--dbname', str(db_name),
            '--format', 'custom' if not compress else 'plain',
            '--verbose',
        ]

        if compress:
            cmd.extend(['--compress', '9'])

        cmd.extend(['--file', str(output_path)])

        try:
            env = os.environ.copy()
            if db_settings.get('PASSWORD'):
                env['PGPASSWORD'] = db_settings['PASSWORD']

            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                check=True
            )

            file_size = os.path.getsize(output_path)
            file_size_mb = file_size / (1024 * 1024)

            self.stdout.write(self.style.SUCCESS(
                f'SQL backup created successfully: {output_path}\n'
                f'  Size: {file_size_mb:.2f} MB ({file_size:,} bytes)'
            ))

            self.log_backup_metadata(output_path, 'sql', file_size)

        except subprocess.CalledProcessError as e:
            raise CommandError(f'pg_dump failed: {e.stderr}')
        except FileNotFoundError:
            raise CommandError('pg_dump not found. Please ensure PostgreSQL client tools are installed.')

    def log_backup_metadata(self, path, format_type, size):
        """Log backup metadata to a log file."""
        log_path = Path(settings.BASE_DIR) / 'backups' / 'backup_log.json'
        
        metadata = {
            'timestamp': datetime.now().isoformat(),
            'path': str(path),
            'format': format_type,
            'size_bytes': size,
            'database': settings.DATABASES['default'].get('NAME', 'unknown')
        }

        # Read existing log
        log_entries = []
        if log_path.exists():
            try:
                with open(log_path, 'r') as f:
                    log_entries = json.load(f)
            except (json.JSONDecodeError, IOError):
                log_entries = []

        # Add new entry and keep last 100
        log_entries.append(metadata)
        log_entries = log_entries[-100:]

        # Write back
        with open(log_path, 'w') as f:
            json.dump(log_entries, f, indent=2)

        self.stdout.write(f'Backup logged to {log_path}')