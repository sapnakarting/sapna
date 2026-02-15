"""
Unit tests for fleet models.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone

from fleet.models import (
    UserProfile, Truck, Driver, FuelLog, TireInventory, 
    DailyOdoRegistry, DieselPrice, Alert
)


class UserProfileModelTests(TestCase):
    """Test cases for UserProfile model."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.profile = UserProfile.objects.create(
            user=self.user,
            role=UserProfile.Role.ADMIN,
            phone='1234567890'
        )
    
    def test_profile_creation(self):
        """Test that a user profile is created correctly."""
        self.assertEqual(self.profile.user, self.user)
        self.assertEqual(self.profile.role, UserProfile.Role.ADMIN)
        self.assertEqual(self.profile.phone, '1234567890')
    
    def test_is_admin_method(self):
        """Test the is_admin method."""
        self.assertTrue(self.profile.is_admin())
        self.profile.role = UserProfile.Role.FUEL_AGENT
        self.profile.save()
        self.assertFalse(self.profile.is_admin())
    
    def test_is_fuel_agent_method(self):
        """Test the is_fuel_agent method."""
        self.assertFalse(self.profile.is_fuel_agent())
        self.profile.role = UserProfile.Role.FUEL_AGENT
        self.profile.save()
        self.assertTrue(self.profile.is_fuel_agent())
    
    def test_str_representation(self):
        """Test the string representation."""
        expected = f"{self.user.username} - {self.profile.role}"
        self.assertEqual(str(self.profile), expected)


class TruckModelTests(TestCase):
    """Test cases for Truck model."""
    
    def setUp(self):
        self.truck = Truck.objects.create(
            plate_number='MH12AB1234',
            transporter_name='Test Transporter',
            wheel_config=Truck.WheelConfig.TEN_WHEEL,
            fleet_type=Truck.FleetType.COAL,
            mining_type=Truck.MiningType.INTERNAL,
            current_odometer=50000,
            status=Truck.Status.ACTIVE,
            remarks='Test truck',
            fitness_expiry=date.today() + timedelta(days=30),
            insurance_expiry=date.today() + timedelta(days=60),
            pucc_expiry=date.today() + timedelta(days=15),
            tax_expiry=date.today() + timedelta(days=90),
            permit_expiry=date.today() + timedelta(days=45)
        )
    
    def test_truck_creation(self):
        """Test that a truck is created correctly."""
        self.assertEqual(self.truck.plate_number, 'MH12AB1234')
        self.assertEqual(self.truck.transporter_name, 'Test Transporter')
        self.assertEqual(self.truck.wheel_config, Truck.WheelConfig.TEN_WHEEL)
        self.assertEqual(self.truck.fleet_type, Truck.FleetType.COAL)
        self.assertEqual(self.truck.current_odometer, 50000)
        self.assertEqual(self.truck.status, Truck.Status.ACTIVE)
    
    def test_plate_number_unique(self):
        """Test that plate number must be unique."""
        with self.assertRaises(Exception):
            Truck.objects.create(
                plate_number='MH12AB1234',  # Same plate number
                transporter_name='Another Transporter',
                wheel_config=Truck.WheelConfig.FOURTEEN_WHEEL,
                fleet_type=Truck.FleetType.MINING,
                status=Truck.Status.ACTIVE
            )
    
    def test_get_expiry_color_code(self):
        """Test the get_expiry_color_code method."""
        # Test with specific date
        near_expiry = date.today() + timedelta(days=5)
        color = self.truck.get_expiry_color_code(near_expiry)
        self.assertIsNotNone(color)
        
        # Test all expiry fields
        colors = self.truck.get_expiry_color_code()
        self.assertIn('fitness', colors)
        self.assertIn('insurance', colors)
        self.assertIn('pucc', colors)
        self.assertIn('tax', colors)
        self.assertIn('permit', colors)
    
    def test_str_representation(self):
        """Test the string representation."""
        self.assertEqual(str(self.truck), 'MH12AB1234')
    
    def test_status_history_default(self):
        """Test that status history defaults to empty list."""
        self.assertEqual(self.truck.status_history, [])
    
    def test_documents_default(self):
        """Test that documents defaults to empty dict."""
        self.assertEqual(self.truck.documents, {})


class DriverModelTests(TestCase):
    """Test cases for Driver model."""
    
    def setUp(self):
        self.driver = Driver.objects.create(
            name='John Doe',
            license_number='DL12345678',
            phone='9876543210',
            status=Driver.Status.ON_DUTY,
            driver_type=Driver.DriverType.PERMANENT
        )
    
    def test_driver_creation(self):
        """Test that a driver is created correctly."""
        self.assertEqual(self.driver.name, 'John Doe')
        self.assertEqual(self.driver.license_number, 'DL12345678')
        self.assertEqual(self.driver.phone, '9876543210')
        self.assertEqual(self.driver.status, Driver.Status.ON_DUTY)
        self.assertEqual(self.driver.driver_type, Driver.DriverType.PERMANENT)
    
    def test_license_number_unique(self):
        """Test that license number must be unique."""
        with self.assertRaises(Exception):
            Driver.objects.create(
                name='Jane Doe',
                license_number='DL12345678',  # Same license number
                phone='9876543211',
                status=Driver.Status.OFF_DUTY,
                driver_type=Driver.DriverType.TEMPORARY
            )
    
    def test_str_representation(self):
        """Test the string representation."""
        self.assertEqual(str(self.driver), 'John Doe')


class FuelLogModelTests(TestCase):
    """Test cases for FuelLog model."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='fuelagent',
            password='testpass123'
        )
        self.truck = Truck.objects.create(
            plate_number='MH12AB1234',
            transporter_name='Test Transporter',
            wheel_config=Truck.WheelConfig.TEN_WHEEL,
            fleet_type=Truck.FleetType.COAL,
            status=Truck.Status.ACTIVE,
            current_odometer=50000
        )
        self.driver = Driver.objects.create(
            name='John Doe',
            license_number='DL12345678',
            phone='9876543210',
            status=Driver.Status.ON_DUTY,
            driver_type=Driver.DriverType.PERMANENT
        )
        self.fuel_log = FuelLog.objects.create(
            truck=self.truck,
            driver=self.driver,
            date=date.today(),
            entry_type=FuelLog.EntryType.FULL_TANK,
            odometer=50100,
            previous_odometer=50000,
            fuel_liters=Decimal('50.00'),
            diesel_price=Decimal('95.50'),
            fueling_agent=self.user
        )
    
    def test_fuel_log_creation(self):
        """Test that a fuel log is created correctly."""
        self.assertEqual(self.fuel_log.truck, self.truck)
        self.assertEqual(self.fuel_log.driver, self.driver)
        self.assertEqual(self.fuel_log.odometer, 50100)
        self.assertEqual(self.fuel_log.fuel_liters, Decimal('50.00'))
        self.assertEqual(self.fuel_log.diesel_price, Decimal('95.50'))
    
    def test_calculate_fuel_cost(self):
        """Test the calculate_fuel_cost method."""
        expected_cost = Decimal('50.00') * Decimal('95.50')
        self.assertEqual(self.fuel_log.calculate_fuel_cost(), expected_cost)
    
    def test_fuel_cost_auto_calculated(self):
        """Test that fuel cost is auto-calculated on save."""
        expected_cost = Decimal('50.00') * Decimal('95.50')
        self.assertEqual(self.fuel_log.fuel_cost, expected_cost)
    
    def test_attribution_date_auto_set(self):
        """Test that attribution date is auto-set on save."""
        self.assertIsNotNone(self.fuel_log.attribution_date)
        self.assertEqual(self.fuel_log.attribution_date, self.fuel_log.date)
    
    def test_str_representation(self):
        """Test the string representation."""
        expected = f"{self.truck.plate_number} - {self.fuel_log.date}"
        self.assertEqual(str(self.fuel_log), expected)
    
    def test_verification_photos_default(self):
        """Test that verification photos defaults to empty list."""
        self.assertEqual(self.fuel_log.verification_photos, [])


class TireInventoryModelTests(TestCase):
    """Test cases for TireInventory model."""
    
    def setUp(self):
        self.truck = Truck.objects.create(
            plate_number='MH12AB1234',
            transporter_name='Test Transporter',
            wheel_config=Truck.WheelConfig.TEN_WHEEL,
            fleet_type=Truck.FleetType.COAL,
            status=Truck.Status.ACTIVE,
            current_odometer=50000
        )
        self.tire = TireInventory.objects.create(
            serial_number='TIRE123456',
            brand='Michelin',
            status=TireInventory.Status.MOUNTED,
            truck=self.truck,
            position='FL',
            purchase_cost=Decimal('25000.00'),
            mounting_cost=Decimal('500.00'),
            repair_costs=Decimal('0.00'),
            historical_mileage=10000,
            mounted_at_odometer=40000
        )
    
    def test_tire_creation(self):
        """Test that a tire is created correctly."""
        self.assertEqual(self.tire.serial_number, 'TIRE123456')
        self.assertEqual(self.tire.brand, 'Michelin')
        self.assertEqual(self.tire.status, TireInventory.Status.MOUNTED)
        self.assertEqual(self.tire.truck, self.truck)
        self.assertEqual(self.tire.position, 'FL')
    
    def test_calculate_current_mileage(self):
        """Test the calculate_current_mileage method."""
        # Truck odometer: 50000, mounted at: 40000
        expected_mileage = 10000 + (50000 - 40000)
        self.assertEqual(self.tire.calculate_current_mileage(), expected_mileage)
    
    def test_calculate_current_mileage_no_truck(self):
        """Test calculate_current_mileage when tire is not mounted."""
        self.tire.truck = None
        self.tire.save()
        self.assertEqual(self.tire.calculate_current_mileage(), 10000)
    
    def test_calculate_total_cost(self):
        """Test the calculate_total_cost method."""
        expected = Decimal('25000.00') + Decimal('500.00') + Decimal('0.00')
        self.assertEqual(self.tire.calculate_total_cost(), expected)
    
    def test_calculate_cost_per_km(self):
        """Test the calculate_cost_per_km method."""
        total_cost = self.tire.calculate_total_cost()
        mileage = self.tire.calculate_current_mileage()
        expected = total_cost / Decimal(mileage)
        self.assertEqual(self.tire.calculate_cost_per_km(), expected)
    
    def test_calculate_cost_per_km_zero_mileage(self):
        """Test calculate_cost_per_km when mileage is zero."""
        self.tire.historical_mileage = 0
        self.tire.mounted_at_odometer = self.truck.current_odometer
        self.tire.save()
        self.assertEqual(self.tire.calculate_cost_per_km(), Decimal('0.00'))
    
    def test_serial_number_unique(self):
        """Test that serial number must be unique."""
        with self.assertRaises(Exception):
            TireInventory.objects.create(
                serial_number='TIRE123456',  # Same serial number
                brand='Bridgestone',
                status=TireInventory.Status.NEW,
                purchase_cost=Decimal('20000.00')
            )
    
    def test_str_representation(self):
        """Test the string representation."""
        self.assertEqual(str(self.tire), 'TIRE123456')
    
    def test_history_default(self):
        """Test that history defaults to empty list."""
        self.assertEqual(self.tire.history, [])


class DailyOdoRegistryModelTests(TestCase):
    """Test cases for DailyOdoRegistry model."""
    
    def setUp(self):
        self.truck = Truck.objects.create(
            plate_number='MH12AB1234',
            transporter_name='Test Transporter',
            wheel_config=Truck.WheelConfig.TEN_WHEEL,
            fleet_type=Truck.FleetType.COAL,
            status=Truck.Status.ACTIVE,
            current_odometer=50000
        )
        self.entry = DailyOdoRegistry.objects.create(
            truck=self.truck,
            date=date.today(),
            opening_odometer=50000,
            closing_odometer=50200,
            remarks='Daily entry'
        )
    
    def test_entry_creation(self):
        """Test that a daily odo entry is created correctly."""
        self.assertEqual(self.entry.truck, self.truck)
        self.assertEqual(self.entry.opening_odometer, 50000)
        self.assertEqual(self.entry.closing_odometer, 50200)
        self.assertEqual(self.entry.remarks, 'Daily entry')
    
    def test_daily_mileage_auto_calculated(self):
        """Test that daily mileage is auto-calculated on save."""
        self.assertEqual(self.entry.daily_mileage, 200)
    
    def test_daily_mileage_zero_if_invalid(self):
        """Test that daily mileage is zero if closing < opening."""
        self.entry.closing_odometer = 49900
        self.entry.save()
        self.assertEqual(self.entry.daily_mileage, 0)
    
    def test_unique_together_constraint(self):
        """Test that truck and date must be unique together."""
        with self.assertRaises(Exception):
            DailyOdoRegistry.objects.create(
                truck=self.truck,
                date=date.today(),  # Same date
                opening_odometer=50200,
                closing_odometer=50500
            )
    
    def test_str_representation(self):
        """Test the string representation."""
        expected = f"{self.truck.plate_number} - {self.entry.date}"
        self.assertEqual(str(self.entry), expected)


class DieselPriceModelTests(TestCase):
    """Test cases for DieselPrice model."""
    
    def setUp(self):
        self.diesel_price = DieselPrice.objects.create(
            date=date.today(),
            price=Decimal('95.50')
        )
    
    def test_diesel_price_creation(self):
        """Test that a diesel price entry is created correctly."""
        self.assertEqual(self.diesel_price.date, date.today())
        self.assertEqual(self.diesel_price.price, Decimal('95.50'))
    
    def test_date_unique(self):
        """Test that date must be unique."""
        with self.assertRaises(Exception):
            DieselPrice.objects.create(
                date=date.today(),  # Same date
                price=Decimal('96.00')
            )
    
    def test_str_representation(self):
        """Test the string representation."""
        expected = f"₹{self.diesel_price.price}/L on {self.diesel_price.date}"
        self.assertEqual(str(self.diesel_price), expected)


class AlertModelTests(TestCase):
    """Test cases for Alert model."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='admin',
            password='adminpass123'
        )
        self.truck = Truck.objects.create(
            plate_number='MH12AB1234',
            transporter_name='Test Transporter',
            wheel_config=Truck.WheelConfig.TEN_WHEEL,
            fleet_type=Truck.FleetType.COAL,
            status=Truck.Status.ACTIVE
        )
        self.alert = Alert.objects.create(
            title='Test Alert',
            alert_type=Alert.AlertType.DOCUMENT_EXPIRY,
            alert_level=Alert.AlertLevel.WARNING,
            status=Alert.AlertStatus.PENDING,
            description='Test alert description',
            truck=self.truck,
            related_object_id=1,
            related_content_type='fleet.Truck',
            metadata={'key': 'value'}
        )
    
    def test_alert_creation(self):
        """Test that an alert is created correctly."""
        self.assertEqual(self.alert.title, 'Test Alert')
        self.assertEqual(self.alert.alert_type, Alert.AlertType.DOCUMENT_EXPIRY)
        self.assertEqual(self.alert.alert_level, Alert.AlertLevel.WARNING)
        self.assertEqual(self.alert.status, Alert.AlertStatus.PENDING)
        self.assertEqual(self.alert.description, 'Test alert description')
        self.assertEqual(self.alert.truck, self.truck)
    
    def test_str_representation(self):
        """Test the string representation."""
        expected = f"[{self.alert.get_alert_type_display()}] {self.alert.title} - {self.alert.get_status_display()}"
        self.assertEqual(str(self.alert), expected)
    
    def test_metadata_default(self):
        """Test that metadata defaults to empty dict."""
        alert = Alert.objects.create(
            title='Another Alert',
            alert_type=Alert.AlertType.GENERAL,
            description='Another description'
        )
        self.assertEqual(alert.metadata, {})
    
    def test_ordering(self):
        """Test that alerts are ordered by created_at descending."""
        alert2 = Alert.objects.create(
            title='Newer Alert',
            alert_type=Alert.AlertType.GENERAL,
            description='Newer description'
        )
        alerts = list(Alert.objects.all())
        self.assertEqual(alerts[0], alert2)
        self.assertEqual(alerts[1], self.alert)
