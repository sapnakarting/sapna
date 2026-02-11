from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from fleet.models import UserProfile


class Command(BaseCommand):
    help = 'Create default admin and fuel agent users'

    def handle(self, *args, **options):
        # Create default admin
        admin, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@sapnacarting.com',
                'first_name': 'System',
                'last_name': 'Administrator',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            admin.set_password('admin123')
            admin.save()
            UserProfile.objects.create(
                user=admin,
                role='ADMIN',
                phone=''
            )
            self.stdout.write(self.style.SUCCESS('Created admin user (admin/admin123)'))
        else:
            self.stdout.write(self.style.WARNING('Admin user already exists'))

        # Create default fuel agent
        agent, created = User.objects.get_or_create(
            username='fuel_agent',
            defaults={
                'email': 'agent@sapnacarting.com',
                'first_name': 'Fuel',
                'last_name': 'Agent',
            }
        )
        if created:
            agent.set_password('fuel123')
            agent.save()
            UserProfile.objects.create(
                user=agent,
                role='FUEL_AGENT',
                phone=''
            )
            self.stdout.write(self.style.SUCCESS('Created fuel agent user (fuel_agent/fuel123)'))
        else:
            self.stdout.write(self.style.WARNING('Fuel agent user already exists'))
