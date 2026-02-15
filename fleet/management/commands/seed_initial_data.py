import random
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.db import transaction

from fleet.models import (
    Truck, Driver, UserProfile, TireInventory, DieselPrice, DailyOdoRegistry
)
from operations.models import CoalLog, MiningLog
from settings_app.models import SystemSettings


class Command(BaseCommand):
    help = 'Seed initial data for the fleet management system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--mode',
            type=str,
            choices=['minimal', 'demo', 'production'],
            default='minimal',
            help='Seeding mode: minimal (system settings only), demo (sample data), production (essential configs)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before seeding (with confirmation)'
        )
        parser.add_argument(
            '--no-input',
            action='store_true',
            help='Bypass confirmation prompts'
        )

    def handle(self, *args, **options):
        mode = options['mode']
        clear = options['clear']
        no_input = options['no_input']

        if clear:
            if not no_input:
                confirm = input('This will DELETE ALL DATA. Are you sure? (yes/no): ')
                if confirm.lower() != 'yes':
                    self.stdout.write(self.style.WARNING('Seeding cancelled.'))
                    return
            self.clear_data()

        created_summary = {}

        with transaction.atomic():
            # Always create system settings
            created_summary['system_settings'] = self.create_system_settings()

            if mode == 'demo':
                created_summary['users'] = self.create_demo_users()
                created_summary['diesel_prices'] = self.create_diesel_prices()
                created_summary['trucks'] = self.create_demo_trucks()
                created_summary['drivers'] = self.create_demo_drivers()
                created_summary['tires'] = self.create_demo_tires()
                created_summary['daily_odos'] = self.create_demo_daily_odos()
                created_summary['coal_logs'] = self.create_demo_coal_logs()
                created_summary['mining_logs'] = self.create_demo_mining_logs()
            elif mode == 'production':
                created_summary['users'] = self.create_production_users()
                created_summary['diesel_prices'] = self.create_diesel_prices()

        self.print_summary(created_summary, mode)

    def clear_data(self):
        """Clear all data from the database."""
        self.stdout.write(self.style.WARNING('Clearing all data...'))
        MiningLog.objects.all().delete()
        CoalLog.objects.all().delete()
        DailyOdoRegistry.objects.all().delete()
        TireInventory.objects.all().delete()
        FuelLog = __import__('fleet.models', fromlist=['FuelLog']).FuelLog
        FuelLog.objects.all().delete()
        Driver.objects.all().delete()
        Truck.objects.all().delete()
        UserProfile.objects.filter(user__is_superuser=False).delete()
        User.objects.filter(is_superuser=False).delete()
        DieselPrice.objects.all().delete()
        self.stdout.write(self.style.SUCCESS('All data cleared.'))

    def create_system_settings(self):
        """Create or update system settings."""
        settings, created = SystemSettings.objects.get_or_create(
            pk=1,
            defaults={
                'compliance_alert_email': 'admin@sapnacarting.com',
                'global_fuel_efficiency_benchmark': Decimal('3.50'),
                'per_trip_diesel_benchmark': Decimal('150.00'),
                'per_tonnage_diesel_benchmark': Decimal('2.50'),
                'fleet_efficiency_threshold_min': Decimal('3.00'),
                'fleet_efficiency_threshold_max': Decimal('5.00'),
                'fuel_efficiency_check_frequency': 'DAILY',
            }
        )
        return {'created': created, 'name': 'System Settings'}

    def create_production_users(self):
        """Create essential production users."""
        created_items = []

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
        
        profile, prof_created = UserProfile.objects.get_or_create(
            user=admin,
            defaults={'role': 'ADMIN', 'phone': ''}
        )
        created_items.append({'name': f'Admin user ({admin.username})', 'created': created})

        return created_items

    def create_demo_users(self):
        """Create demo users for testing."""
        created_items = []

        # Admin user
        admin, created = User.objects.get_or_create(
            username='demo_admin',
            defaults={
                'email': 'admin@demo.com',
                'first_name': 'Demo',
                'last_name': 'Admin',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            admin.set_password('demo123')
            admin.save()
        UserProfile.objects.get_or_create(user=admin, defaults={'role': 'ADMIN', 'phone': '9999999999'})
        created_items.append({'name': f'Demo Admin ({admin.username})', 'created': created})

        # Fuel agents
        for i in range(1, 4):
            agent, created = User.objects.get_or_create(
                username=f'fuel_agent_{i}',
                defaults={
                    'email': f'agent{i}@demo.com',
                    'first_name': f'Agent',
                    'last_name': f'{i}',
                }
            )
            if created:
                agent.set_password('demo123')
                agent.save()
            UserProfile.objects.get_or_create(user=agent, defaults={'role': 'FUEL_AGENT', 'phone': f'999999999{i}'})
            created_items.append({'name': f'Fuel Agent {i} ({agent.username})', 'created': created})

        return created_items

    def create_diesel_prices(self):
        """Create diesel price history for the last 30 days."""
        created_items = []
        base_price = Decimal('94.50')
        
        for i in range(30):
            price_date = date.today() - timedelta(days=i)
            # Random fluctuation between -1.00 and +1.00
            fluctuation = Decimal(random.uniform(-1.0, 1.0)).quantize(Decimal('0.01'))
            price = base_price + fluctuation
            
            _, created = DieselPrice.objects.get_or_create(
                date=price_date,
                defaults={'price': price}
            )
            if created:
                created_items.append({'name': f'Diesel price for {price_date}', 'created': True})

        return created_items

    def create_demo_trucks(self):
        """Create demo trucks."""
        created_items = []
        
        truck_data = [
            {'plate': 'MH12AB1234', 'transporter': 'Sharma Transport', 'wheel': '10_WHEEL', 'fleet': 'COAL'},
            {'plate': 'MH12CD5678', 'transporter': 'Sharma Transport', 'wheel': '14_WHEEL', 'fleet': 'COAL'},
            {'plate': 'MH12EF9012', 'transporter': 'Patel Logistics', 'wheel': '10_WHEEL', 'fleet': 'MINING', 'mining': 'INTERNAL'},
            {'plate': 'MH12GH3456', 'transporter': 'Patel Logistics', 'wheel': '16_WHEEL', 'fleet': 'MINING', 'mining': 'EXTERNAL'},
            {'plate': 'MH12IJ7890', 'transporter': 'Kumar Freight', 'wheel': '10_WHEEL', 'fleet': 'COAL'},
            {'plate': 'MH12KL4321', 'transporter': 'Kumar Freight', 'wheel': '14_WHEEL', 'fleet': 'COAL'},
            {'plate': 'MH12MN8765', 'transporter': 'Singh Carriers', 'wheel': '10_WHEEL', 'fleet': 'MINING', 'mining': 'INTERNAL'},
            {'plate': 'MH12OP2198', 'transporter': 'Singh Carriers', 'wheel': '14_WHEEL', 'fleet': 'MINING', 'mining': 'EXTERNAL'},
        ]
        
        for data in truck_data:
            truck, created = Truck.objects.get_or_create(
                plate_number=data['plate'],
                defaults={
                    'transporter_name': data['transporter'],
                    'wheel_config': data['wheel'],
                    'fleet_type': data['fleet'],
                    'mining_type': data.get('mining'),
                    'current_odometer': random.randint(50000, 200000),
                    'status': 'ACTIVE',
                    'fitness_expiry': date.today() + timedelta(days=random.randint(30, 365)),
                    'insurance_expiry': date.today() + timedelta(days=random.randint(30, 365)),
                    'pucc_expiry': date.today() + timedelta(days=random.randint(15, 180)),
                    'tax_expiry': date.today() + timedelta(days=random.randint(60, 365)),
                    'permit_expiry': date.today() + timedelta(days=random.randint(90, 365)),
                }
            )
            created_items.append({'name': f'Truck {truck.plate_number}', 'created': created})

        return created_items

    def create_demo_drivers(self):
        """Create demo drivers."""
        created_items = []
        
        driver_names = [
            'Rajesh Kumar', 'Suresh Patel', 'Amit Sharma', 'Vijay Singh',
            'Ramesh Yadav', 'Mahesh Gupta', 'Dinesh Verma', 'Nitin Shah',
            'Prakash Rao', 'Sunil Joshi', 'Anil Mehta', 'Sanjay Desai',
            'Deepak Tiwari', 'Vikram Choudhary', 'Mohammed Khan'
        ]
        
        for i, name in enumerate(driver_names):
            driver, created = Driver.objects.get_or_create(
                license_number=f'DL{100000 + i}',
                defaults={
                    'name': name,
                    'phone': f'98765432{i:02d}',
                    'status': random.choice(['ON_DUTY', 'OFF_DUTY']),
                    'driver_type': 'PERMANENT' if i < 10 else 'TEMPORARY',
                }
            )
            created_items.append({'name': f'Driver {driver.name}', 'created': created})

        return created_items

    def create_demo_tires(self):
        """Create demo tire inventory."""
        created_items = []
        brands = ['MRF', 'Apollo', 'CEAT', 'Bridgestone', 'Goodyear', 'JK Tyre']
        statuses = ['NEW', 'MOUNTED', 'SPARE', 'REPAIR']
        
        for i in range(50):
            status = random.choice(statuses)
            truck = None
            position = ''
            
            if status == 'MOUNTED':
                trucks = list(Truck.objects.all())
                if trucks:
                    truck = random.choice(trucks)
                    position = f'Position {random.randint(1, 10)}'
            
            tire, created = TireInventory.objects.get_or_create(
                serial_number=f'TIRE{20240000 + i}',
                defaults={
                    'brand': random.choice(brands),
                    'status': status,
                    'truck': truck,
                    'position': position,
                    'purchase_cost': Decimal(random.uniform(15000, 35000)).quantize(Decimal('0.01')),
                    'mounting_cost': Decimal(random.uniform(500, 1500)).quantize(Decimal('0.01')) if status == 'MOUNTED' else Decimal('0'),
                    'repair_costs': Decimal(random.uniform(0, 2000)).quantize(Decimal('0.01')) if status == 'REPAIR' else Decimal('0'),
                    'historical_mileage': random.randint(0, 50000) if status == 'SCRAPPED' else 0,
                }
            )
            created_items.append({'name': f'Tire {tire.serial_number}', 'created': created})

        return created_items

    def create_demo_daily_odos(self):
        """Create demo daily odometer entries."""
        created_items = []
        
        for truck in Truck.objects.all():
            base_odo = truck.current_odometer - 5000
            for day in range(14):
                entry_date = date.today() - timedelta(days=day)
                opening = base_odo + (day * 150)
                closing = opening + random.randint(50, 300)
                
                _, created = DailyOdoRegistry.objects.get_or_create(
                    truck=truck,
                    date=entry_date,
                    defaults={
                        'opening_odometer': opening,
                        'closing_odometer': closing,
                    }
                )
                if created:
                    created_items.append({'name': f'Odo entry for {truck.plate_number} on {entry_date}', 'created': True})

        return created_items

    def create_demo_coal_logs(self):
        """Create demo coal logs."""
        created_items = []
        FuelLog = __import__('fleet.models', fromlist=['FuelLog']).FuelLog
        
        trucks = list(Truck.objects.filter(fleet_type='COAL'))
        drivers = list(Driver.objects.all())
        admin_user = User.objects.filter(is_superuser=True).first()
        
        if not trucks or not drivers or not admin_user:
            return created_items
        
        for i in range(30):
            truck = random.choice(trucks)
            driver = random.choice(drivers)
            log_date = date.today() - timedelta(days=random.randint(0, 14))
            
            log, created = CoalLog.objects.get_or_create(
                pass_no=f'PASS{20240000 + i}',
                defaults={
                    'truck': truck,
                    'date': log_date,
                    'gross_weight': Decimal(random.uniform(30000, 45000)).quantize(Decimal('0.01')),
                    'tare_weight': Decimal(random.uniform(8000, 12000)).quantize(Decimal('0.01')),
                    'diesel_liters': Decimal(random.uniform(40, 80)).quantize(Decimal('0.01')),
                    'diesel_rate': Decimal('94.50'),
                    'origin_site': random.choice(['Mine A', 'Mine B', 'Mine C']),
                    'destination_site': random.choice(['Plant X', 'Plant Y', 'Power Station']),
                    'created_by': admin_user,
                }
            )
            if created:
                created_items.append({'name': f'Coal log {log.pass_no}', 'created': True})

        return created_items

    def create_demo_mining_logs(self):
        """Create demo mining logs."""
        created_items = []
        
        trucks = list(Truck.objects.filter(fleet_type='MINING'))
        admin_user = User.objects.filter(is_superuser=True).first()
        
        if not trucks or not admin_user:
            return created_items
        
        materials = ['Iron Ore', 'Coal', 'Limestone', 'Bauxite', 'Copper Ore']
        customers = ['Steel Plant Ltd', 'Power Corp', 'Cement Industries', 'Mining Corp']
        
        for i in range(40):
            truck = random.choice(trucks)
            log_date = date.today() - timedelta(days=random.randint(0, 14))
            
            log, created = MiningLog.objects.get_or_create(
                chalan_no=f'CH{20240000 + i}',
                defaults={
                    'type': random.choice(['DISPATCH', 'PURCHASE']),
                    'date': log_date,
                    'time': f'{random.randint(8, 18):02d}:{random.randint(0, 59):02d}:00',
                    'customer_name': random.choice(customers),
                    'truck': truck,
                    'net': Decimal(random.uniform(20000, 40000)).quantize(Decimal('0.01')),
                    'material': random.choice(materials),
                    'mining_type': truck.mining_type or 'INTERNAL',
                    'created_by': admin_user,
                }
            )
            if created:
                created_items.append({'name': f'Mining log {log.chalan_no}', 'created': True})

        return created_items

    def print_summary(self, summary, mode):
        """Print summary of created data."""
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(self.style.SUCCESS(f'SEEDING COMPLETE - Mode: {mode.upper()}'))
        self.stdout.write('=' * 50)
        
        for category, items in summary.items():
            if isinstance(items, dict):
                status = 'Created' if items.get('created') else 'Already exists'
                self.stdout.write(f'  {category}: {items.get("name", "N/A")} ({status})')
            elif isinstance(items, list):
                created_count = sum(1 for item in items if item.get('created'))
                existing_count = len(items) - created_count
                self.stdout.write(f'  {category}: {created_count} created, {existing_count} existing')
        
        self.stdout.write('=' * 50)
        
        if mode == 'demo':
            self.stdout.write(self.style.WARNING('\nDemo credentials:'))
            self.stdout.write('  Admin: demo_admin / demo123')
            self.stdout.write('  Agents: fuel_agent_1, fuel_agent_2, fuel_agent_3 / demo123')
        elif mode == 'production':
            self.stdout.write(self.style.WARNING('\nProduction credentials:'))
            self.stdout.write('  Admin: admin / admin123')
            self.stdout.write(self.style.WARNING('  Please change default passwords after login!'))
