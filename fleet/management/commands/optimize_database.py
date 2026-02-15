from django.core.management.base import BaseCommand, CommandError
from django.db import connection, models
from django.apps import apps
from django.conf import settings


class Command(BaseCommand):
    help = 'Analyze and optimize database performance'

    def add_arguments(self, parser):
        parser.add_argument(
            '--analyze',
            action='store_true',
            help='Show query analysis without making changes'
        )
        parser.add_argument(
            '--create-migration',
            action='store_true',
            help='Create a migration file with index suggestions'
        )
        parser.add_argument(
            '--vacuum',
            action='store_true',
            help='Run VACUUM ANALYZE on PostgreSQL database'
        )
        parser.add_argument(
            '--app',
            type=str,
            help='Only analyze specific app (e.g., fleet, operations)'
        )

    def handle(self, *args, **options):
        analyze = options['analyze']
        create_migration = options['create_migration']
        vacuum = options['vacuum']
        app_label = options['app']

        # Check database type
        db_engine = settings.DATABASES['default']['ENGINE']
        is_postgres = 'postgresql' in db_engine

        if vacuum and not is_postgres:
            self.stdout.write(self.style.WARNING('VACUUM is only available for PostgreSQL'))
            vacuum = False

        # Get models to analyze
        if app_label:
            try:
                app_config = apps.get_app_config(app_label)
                models_to_check = list(app_config.get_models())
            except LookupError:
                raise CommandError(f'App "{app_label}" not found')
        else:
            models_to_check = apps.get_models()

        # Filter out Django internal models
        models_to_check = [
            m for m in models_to_check 
            if not m._meta.app_label in ('admin', 'auth', 'contenttypes', 'sessions')
        ]

        self.stdout.write(f'Analyzing {len(models_to_check)} models...\n')

        # Analyze models
        index_suggestions = []
        table_stats = []

        for model in models_to_check:
            suggestions = self.analyze_model(model)
            if suggestions:
                index_suggestions.extend(suggestions)
            
            stats = self.get_table_stats(model)
            if stats:
                table_stats.append(stats)

        # Display results
        self.display_analysis(index_suggestions, table_stats)

        # Create migration if requested
        if create_migration and index_suggestions:
            self.create_index_migration(index_suggestions)

        # Run VACUUM ANALYZE if requested
        if vacuum:
            self.run_vacuum_analyze()

    def analyze_model(self, model):
        """Analyze a model and suggest indexes."""
        suggestions = []
        
        # Check existing indexes
        existing_indexes = set()
        for index in model._meta.indexes:
            existing_indexes.add(tuple(index.fields))
        
        # Check fields that might benefit from indexing
        fields_to_check = []
        
        for field in model._meta.fields:
            field_name = field.name
            
            # Foreign keys - almost always need indexes
            if isinstance(field, models.ForeignKey):
                if (field_name,) not in existing_indexes:
                    fields_to_check.append({
                        'field': field_name,
                        'reason': 'Foreign key - frequently used in joins',
                        'priority': 'HIGH'
                    })
            
            # Date fields - frequently filtered/ordered
            elif isinstance(field, (models.DateField, models.DateTimeField)):
                if (field_name,) not in existing_indexes:
                    fields_to_check.append({
                        'field': field_name,
                        'reason': 'Date field - frequently filtered and ordered',
                        'priority': 'MEDIUM'
                    })
            
            # Status/choice fields - frequently filtered
            elif isinstance(field, models.CharField) and field.choices:
                if (field_name,) not in existing_indexes:
                    fields_to_check.append({
                        'field': field_name,
                        'reason': 'Choice field - frequently filtered by status',
                        'priority': 'MEDIUM'
                    })
            
            # Unique fields - already indexed
            elif field.unique:
                pass  # Already has unique index

        # Check model meta for unique_together - already indexed
        for unique_together in model._meta.unique_together:
            pass  # Already has unique index

        if fields_to_check:
            suggestions.append({
                'model': model._meta.label,
                'table': model._meta.db_table,
                'fields': fields_to_check
            })

        return suggestions

    def get_table_stats(self, model):
        """Get table statistics."""
        try:
            count = model.objects.count()
            return {
                'model': model._meta.label,
                'table': model._meta.db_table,
                'count': count
            }
        except Exception:
            return None

    def display_analysis(self, suggestions, stats):
        """Display analysis results."""
        self.stdout.write('=' * 60)
        self.stdout.write(self.style.SUCCESS('TABLE STATISTICS'))
        self.stdout.write('=' * 60)
        
        total_rows = 0
        for stat in sorted(stats, key=lambda x: x['count'], reverse=True):
            self.stdout.write(f"{stat['model']:<40} {stat['count']:>10,} rows")
            total_rows += stat['count']
        
        self.stdout.write('-' * 60)
        self.stdout.write(f"{'TOTAL':<40} {total_rows:>10,} rows")
        self.stdout.write('=' * 60)

        if suggestions:
            self.stdout.write('\n')
            self.stdout.write('=' * 60)
            self.stdout.write(self.style.WARNING('INDEX SUGGESTIONS'))
            self.stdout.write('=' * 60)
            
            for suggestion in suggestions:
                self.stdout.write(f"\nModel: {suggestion['model']}")
                self.stdout.write(f"Table: {suggestion['table']}")
                
                for field in suggestion['fields']:
                    priority_color = self.style.ERROR if field['priority'] == 'HIGH' else self.style.WARNING
                    self.stdout.write(f"  [{field['priority']}] {field['field']}")
                    self.stdout.write(f"      Reason: {field['reason']}")
        else:
            self.stdout.write('\n')
            self.stdout.write(self.style.SUCCESS('No additional indexes suggested. Database looks good!'))

    def create_index_migration(self, suggestions):
        """Create a migration file with index additions."""
        self.stdout.write('\n')
        self.stdout.write('=' * 60)
        self.stdout.write('Creating migration for index additions...')
        self.stdout.write('=' * 60)

        migration_content = self.generate_migration_content(suggestions)
        
        # Find next migration number
        from fleet.models import Truck  # Use any model to find migrations
        app_path = apps.get_app_config('fleet').path
        migrations_dir = app_path / 'migrations'
        
        # Output migration content to stdout for manual creation
        self.stdout.write('\nMigration content (copy to a new migration file):\n')
        self.stdout.write('-' * 60)
        self.stdout.write(migration_content)
        self.stdout.write('-' * 60)
        
        self.stdout.write(self.style.WARNING(
            '\nNote: Copy the above content to a new migration file, e.g., '
            'fleet/migrations/00XX_add_performance_indexes.py'
        ))

    def generate_migration_content(self, suggestions):
        """Generate migration file content."""
        operations = []
        
        for suggestion in suggestions:
            model_name = suggestion['model'].split('.')[1]
            
            for field in suggestion['fields']:
                if field['priority'] == 'HIGH':
                    index_name = f"{model_name.lower()}_{field['field']}_idx"
                    operations.append(f'''        migrations.AddIndex(
            model_name='{model_name.lower()}',
            index=models.Index(fields=['{field['field']}'], name='{index_name}'),
        ),''')

        operations_str = '\n'.join(operations)

        return f'''# Generated by optimize_database command
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('fleet', '0001_initial'),
    ]

    operations = [
{operations_str}
    ]
'''

    def run_vacuum_analyze(self):
        """Run VACUUM ANALYZE on PostgreSQL database."""
        self.stdout.write('\n')
        self.stdout.write('=' * 60)
        self.stdout.write('Running VACUUM ANALYZE...')
        self.stdout.write('=' * 60)
        
        try:
            with connection.cursor() as cursor:
                # VACUUM cannot run inside a transaction block
                cursor.execute('COMMIT')
                cursor.execute('VACUUM ANALYZE')
                
            self.stdout.write(self.style.SUCCESS('VACUUM ANALYZE completed successfully!'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'VACUUM ANALYZE failed: {e}'))
            self.stdout.write(self.style.WARNING(
                'Note: VACUUM requires database superuser privileges. '
                'On Railway/Render, this is handled automatically.'
            ))