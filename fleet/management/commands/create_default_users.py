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
        
        # Create or update admin profile
        profile, profile_created = UserProfile.objects.get_or_create(
            user=admin,
            defaults={
                'role': 'ADMIN',
                'phone': ''
            }
        )
        # Ensure the profile has the correct role
        if profile.role != 'ADMIN':
            profile.role = 'ADMIN'
            profile.save()
        
        if created and profile_created:
            self.stdout.write(self.style.SUCCESS('Created admin user (admin/admin123)'))
        elif created:
            self.stdout.write(self.style.SUCCESS('Created admin user (admin/admin123), profile already existed'))
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
        
        # Create or update fuel agent profile
        profile, profile_created = UserProfile.objects.get_or_create(
            user=agent,
            defaults={
                'role': 'FUEL_AGENT',
                'phone': ''
            }
        )
        # Ensure the profile has the correct role
        if profile.role != 'FUEL_AGENT':
            profile.role = 'FUEL_AGENT'
            profile.save()
        
        if created and profile_created:
            self.stdout.write(self.style.SUCCESS('Created fuel agent user (fuel_agent/fuel123)'))
        elif created:
            self.stdout.write(self.style.SUCCESS('Created fuel agent user (fuel_agent/fuel123), profile already existed'))
        else:
            self.stdout.write(self.style.WARNING('Fuel agent user already exists'))
