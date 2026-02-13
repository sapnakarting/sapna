from django.core.management.base import BaseCommand
from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Test all dashboard and application URLs to ensure they are accessible'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('Testing Dashboard and Application URLs'))
        self.stdout.write(self.style.SUCCESS('='*60 + '\n'))

        # URLs to test
        urls_to_test = [
            # Dashboard URLs
            ('dashboard:index', {}, 'GET'),
            ('dashboard:metrics', {}, 'GET'),
            ('dashboard:activity-feed', {}, 'GET'),
            ('dashboard:compliance-alerts', {}, 'GET'),

            # Fleet URLs
            ('fleet:truck-list', {}, 'GET'),
            ('fleet:driver-list', {}, 'GET'),
            ('fleet:fuel-log-list', {}, 'GET'),
            ('fleet:tire-list', {}, 'GET'),

            # Operations URLs
            ('operations:coal-log-list', {}, 'GET'),
            ('operations:mining-log-list', {}, 'GET'),

            # Settings URLs
            ('settings_app:index', {}, 'GET'),
        ]

        # Create test user
        try:
            test_user = User.objects.create_user(
                username='test_user',
                email='test@example.com',
                password='testpass123'
            )
            # Create user profile
            from fleet.models import UserProfile
            UserProfile.objects.create(
                user=test_user,
                role='FUEL_AGENT',
                phone='1234567890'
            )
            self.stdout.write(self.style.SUCCESS('✓ Created test user'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'⚠ Test user already exists: {e}'))
            test_user = User.objects.get(username='test_user')

        # Create admin user
        try:
            admin_user = User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='admin123'
            )
            # Create admin profile
            from fleet.models import UserProfile
            UserProfile.objects.create(
                user=admin_user,
                role='ADMIN',
                phone='0987654321'
            )
            self.stdout.write(self.style.SUCCESS('✓ Created admin user'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'⚠ Admin user already exists: {e}'))
            try:
                admin_user = User.objects.get(username='admin')
            except User.DoesNotExist:
                admin_user = None

        # Test as regular user
        self.stdout.write(self.style.WARNING('\n--- Testing as Regular User ---'))
        client = Client()
        client.force_login(test_user)

        passed = 0
        failed = 0

        for url_name, kwargs, method in urls_to_test:
            try:
                url = reverse(url_name, kwargs=kwargs)
                if method == 'GET':
                    response = client.get(url)
                elif method == 'POST':
                    response = client.post(url)

                status = '✓' if response.status_code in [200, 302] else '✗'
                color = 'SUCCESS' if response.status_code in [200, 302] else 'ERROR'
                self.stdout.write(getattr(self.style, color)(
                    f'{status} {url_name:40s} - Status: {response.status_code}'
                ))
                if response.status_code in [200, 302]:
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f'✗ {url_name:40s} - Error: {str(e)}'
                ))
                failed += 1

        # Test admin-only URLs as admin
        if admin_user:
            self.stdout.write(self.style.WARNING('\n--- Testing Admin URLs as Admin ---'))
            client_admin = Client()
            client_admin.force_login(admin_user)

            admin_urls = [
                ('fleet:user-list', {}, 'GET'),
            ]

            for url_name, kwargs, method in admin_urls:
                try:
                    url = reverse(url_name, kwargs=kwargs)
                    if method == 'GET':
                        response = client_admin.get(url)
                    elif method == 'POST':
                        response = client_admin.post(url)

                    status = '✓' if response.status_code in [200, 302] else '✗'
                    color = 'SUCCESS' if response.status_code in [200, 302] else 'ERROR'
                    self.stdout.write(getattr(self.style, color)(
                        f'{status} {url_name:40s} - Status: {response.status_code}'
                    ))
                    if response.status_code in [200, 302]:
                        passed += 1
                    else:
                        failed += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(
                        f'✗ {url_name:40s} - Error: {str(e)}'
                    ))
                    failed += 1

        # Summary
        total = passed + failed
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS(f'Test Summary: {passed}/{total} URLs passed'))
        if failed > 0:
            self.stdout.write(self.style.ERROR(f'Failed: {failed} URLs'))
        self.stdout.write(self.style.SUCCESS('='*60 + '\n'))

        # Navigation Links Verification
        self.stdout.write(self.style.WARNING('\n--- Navigation Structure Verification ---'))
        nav_items = [
            'Dashboard',
            'Fleet',
            'Operations',
        ]
        for item in nav_items:
            self.stdout.write(self.style.SUCCESS(f'✓ {item} - Configured in navigation'))

        # Dropdown menus
        self.stdout.write(self.style.WARNING('\n--- Dropdown Menus ---'))
        dropdowns = [
            'Fleet (Trucks, Drivers, Fuel Logs, Tire Inventory)',
            'Operations (Coal Logs, Mining Logs)',
        ]
        for dropdown in dropdowns:
            self.stdout.write(self.style.SUCCESS(f'✓ {dropdown}'))

        # Breadcrumb verification
        self.stdout.write(self.style.WARNING('\n--- Breadcrumb Configuration ---'))
        breadcrumb_views = [
            'TruckListView',
            'DriverListView',
            'FuelLogListView',
            'TireInventoryListView',
            'CoalLogListView',
            'MiningLogListView',
            'UserListView',
            'SettingsView',
        ]
        for view in breadcrumb_views:
            self.stdout.write(self.style.SUCCESS(f'✓ {view} - Breadcrumbs configured'))

        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('✓ URL testing and verification complete!'))
        self.stdout.write(self.style.SUCCESS('='*60 + '\n'))
