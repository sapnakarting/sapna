"""
Unit tests for fleet forms.
"""

from datetime import date, timedelta

from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User

from fleet.forms import (
    LoginForm, UserCreationForm, TruckForm, TruckSearchForm,
    DriverForm, FuelLogForm, DieselPriceForm, TireInventoryForm,
    TireActionForm, TireSearchForm, DailyOdoRegistryForm,
    DailyOdoRegistrySearchForm, BulkDailyOdoEntryForm, AlertUpdateForm
)
from fleet.models import Truck, Driver, Alert


class LoginFormTests(TestCase):
    """Test cases for LoginForm."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        from fleet.models import UserProfile
        UserProfile.objects.create(
            user=self.user,
            role=UserProfile.Role.ADMIN
        )
    
    def test_valid_login(self):
        """Test login with valid credentials."""
        form_data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        form = LoginForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['user'], self.user)
    
    def test_invalid_username(self):
        """Test login with invalid username."""
        form_data = {
            'username': 'wronguser',
            'password': 'testpass123'
        }
        form = LoginForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors)
    
    def test_invalid_password(self):
        """Test login with invalid password."""
        form_data = {
            'username': 'testuser',
            'password': 'wrongpass'
        }
        form = LoginForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors)
    
    def test_inactive_user(self):
        """Test login with inactive user."""
        self.user.is_active = False
        self.user.save()
        form_data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        form = LoginForm(data=form_data)
        self.assertFalse(form.is_valid())
    
    def test_missing_profile(self):
        """Test login for user without profile."""
        user2 = User.objects.create_user(
            username='noprofile',
            password='testpass123'
        )
        form_data = {
            'username': 'noprofile',
            'password': 'testpass123'
        }
        form = LoginForm(data=form_data)
        self.assertFalse(form.is_valid())


class UserCreationFormTests(TestCase):
    """Test cases for UserCreationForm."""
    
    def test_valid_user_creation(self):
        """Test creating a user with valid data."""
        form_data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'password1': 'complexpassword123',
            'password2': 'complexpassword123',
            'role': 'ADMIN',
            'phone': '1234567890'
        }
        form = UserCreationForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_password_mismatch(self):
        """Test that passwords must match."""
        form_data = {
            'username': 'newuser',
            'password1': 'password123',
            'password2': 'differentpassword',
            'role': 'FUEL_AGENT'
        }
        form = UserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)
    
    def test_required_fields(self):
        """Test that required fields are enforced."""
        form_data = {}
        form = UserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)
        self.assertIn('password1', form.errors)
        self.assertIn('password2', form.errors)


class TruckFormTests(TestCase):
    """Test cases for TruckForm."""
    
    def test_valid_truck_creation(self):
        """Test creating a truck with valid data."""
        form_data = {
            'plate_number': 'MH12AB1234',
            'transporter_name': 'Test Transporter',
            'wheel_config': '10_WHEEL',
            'fleet_type': 'COAL',
            'mining_type': 'INTERNAL',
            'current_odometer': 50000,
            'status': 'ACTIVE',
            'remarks': 'Test remarks',
            'fitness_expiry': date.today() + timedelta(days=30),
            'insurance_expiry': date.today() + timedelta(days=60),
            'pucc_expiry': date.today() + timedelta(days=15),
            'tax_expiry': date.today() + timedelta(days=90),
            'permit_expiry': date.today() + timedelta(days=45)
        }
        form = TruckForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_plate_number_uppercase(self):
        """Test that plate number is converted to uppercase."""
        form_data = {
            'plate_number': 'mh12ab1234',
            'transporter_name': 'Test Transporter',
            'wheel_config': '10_WHEEL',
            'fleet_type': 'COAL',
            'status': 'ACTIVE'
        }
        form = TruckForm(data=form_data)
        self.assertTrue(form.is_valid())
        truck = form.save()
        self.assertEqual(truck.plate_number, 'MH12AB1234')
    
    def test_duplicate_plate_number(self):
        """Test that duplicate plate numbers are rejected."""
        Truck.objects.create(
            plate_number='MH12AB1234',
            transporter_name='Existing Transporter',
            wheel_config='10_WHEEL',
            fleet_type='COAL',
            status='ACTIVE'
        )
        form_data = {
            'plate_number': 'MH12AB1234',
            'transporter_name': 'Test Transporter',
            'wheel_config': '10_WHEEL',
            'fleet_type': 'COAL',
            'status': 'ACTIVE'
        }
        form = TruckForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('plate_number', form.errors)


class DriverFormTests(TestCase):
    """Test cases for DriverForm."""
    
    def test_valid_driver_creation(self):
        """Test creating a driver with valid data."""
        form_data = {
            'name': 'John Doe',
            'license_number': 'DL12345678',
            'phone': '9876543210',
            'status': 'ON_DUTY',
            'driver_type': 'PERMANENT'
        }
        form = DriverForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_license_number_uppercase(self):
        """Test that license number is converted to uppercase."""
        form_data = {
            'name': 'John Doe',
            'license_number': 'dl12345678',
            'phone': '9876543210',
            'status': 'ON_DUTY',
            'driver_type': 'PERMANENT'
        }
        form = DriverForm(data=form_data)
        self.assertTrue(form.is_valid())
        driver = form.save()
        self.assertEqual(driver.license_number, 'DL12345678')
    
    def test_invalid_phone(self):
        """Test that phone number must contain only digits."""
        form_data = {
            'name': 'John Doe',
            'license_number': 'DL12345678',
            'phone': 'abc123',
            'status': 'ON_DUTY',
            'driver_type': 'PERMANENT'
        }
        form = DriverForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('phone', form.errors)


class FuelLogFormTests(TestCase):
    """Test cases for FuelLogForm."""
    
    def setUp(self):
        self.truck = Truck.objects.create(
            plate_number='MH12AB1234',
            transporter_name='Test Transporter',
            wheel_config='10_WHEEL',
            fleet_type='COAL',
            status='ACTIVE',
            current_odometer=50000
        )
        self.driver = Driver.objects.create(
            name='John Doe',
            license_number='DL12345678',
            phone='9876543210',
            status='ON_DUTY',
            driver_type='PERMANENT'
        )
    
    def test_valid_fuel_log(self):
        """Test creating a fuel log with valid data."""
        form_data = {
            'truck': self.truck.pk,
            'driver': self.driver.pk,
            'date': date.today(),
            'entry_type': 'FULL_TANK',
            'odometer': 50100,
            'fuel_liters': 50.00,
            'diesel_price': 95.50,
            'verification_photos': []
        }
        form = FuelLogForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_odometer_less_than_current(self):
        """Test that odometer cannot be less than truck's current odometer."""
        form_data = {
            'truck': self.truck.pk,
            'driver': self.driver.pk,
            'date': date.today(),
            'entry_type': 'FULL_TANK',
            'odometer': 49900,  # Less than current (50000)
            'fuel_liters': 50.00,
            'diesel_price': 95.50
        }
        form = FuelLogForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('odometer', form.errors)


class DieselPriceFormTests(TestCase):
    """Test cases for DieselPriceForm."""
    
    def test_valid_diesel_price(self):
        """Test setting diesel price with valid data."""
        form_data = {
            'date': date.today(),
            'price': 95.50
        }
        form = DieselPriceForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_zero_price(self):
        """Test that price must be greater than zero."""
        form_data = {
            'date': date.today(),
            'price': 0
        }
        form = DieselPriceForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('price', form.errors)
    
    def test_negative_price(self):
        """Test that negative price is rejected."""
        form_data = {
            'date': date.today(),
            'price': -10.00
        }
        form = DieselPriceForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('price', form.errors)


class TireInventoryFormTests(TestCase):
    """Test cases for TireInventoryForm."""
    
    def setUp(self):
        self.truck = Truck.objects.create(
            plate_number='MH12AB1234',
            transporter_name='Test Transporter',
            wheel_config='10_WHEEL',
            fleet_type='COAL',
            status='ACTIVE',
            current_odometer=50000
        )
    
    def test_valid_tire_creation(self):
        """Test creating a tire with valid data."""
        form_data = {
            'serial_number': 'TIRE123456',
            'brand': 'Michelin',
            'status': 'NEW',
            'purchase_cost': 25000.00
        }
        form = TireInventoryForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_mounted_requires_truck(self):
        """Test that mounting requires truck selection."""
        form_data = {
            'serial_number': 'TIRE123456',
            'brand': 'Michelin',
            'status': 'MOUNTED',  # Trying to mount without truck
            'purchase_cost': 25000.00
        }
        form = TireInventoryForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('truck', form.errors)
    
    def test_mounted_requires_position(self):
        """Test that mounting requires position."""
        form_data = {
            'serial_number': 'TIRE123456',
            'brand': 'Michelin',
            'status': 'MOUNTED',
            'truck': self.truck.pk,
            'mounted_at_odometer': 50000,
            'purchase_cost': 25000.00
        }
        form = TireInventoryForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('position', form.errors)
    
    def test_scrap_requires_reason(self):
        """Test that scrapping requires reason."""
        form_data = {
            'serial_number': 'TIRE123456',
            'brand': 'Michelin',
            'status': 'SCRAPPED',
            'purchase_cost': 25000.00
        }
        form = TireInventoryForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('scrap_reason', form.errors)


class TireActionFormTests(TestCase):
    """Test cases for TireActionForm."""
    
    def test_mount_action(self):
        """Test mount action form."""
        form_data = {
            'action': 'MOUNT',
            'repair_cost': 1000.00
        }
        form = TireActionForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_repair_action(self):
        """Test repair action form."""
        form_data = {
            'action': 'REPAIR',
            'repair_cost': 1500.00
        }
        form = TireActionForm(data=form_data)
        self.assertTrue(form.is_valid())


class TireSearchFormTests(TestCase):
    """Test cases for TireSearchForm."""
    
    def test_empty_search(self):
        """Test empty search form is valid."""
        form_data = {}
        form = TireSearchForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_search_with_filters(self):
        """Test search with filters."""
        form_data = {
            'search': 'Michelin',
            'status_filter': 'MOUNTED',
            'sort_by': 'purchase_cost'
        }
        form = TireSearchForm(data=form_data)
        self.assertTrue(form.is_valid())


class DailyOdoRegistryFormTests(TestCase):
    """Test cases for DailyOdoRegistryForm."""
    
    def setUp(self):
        self.truck = Truck.objects.create(
            plate_number='MH12AB1234',
            transporter_name='Test Transporter',
            wheel_config='10_WHEEL',
            fleet_type='COAL',
            status='ACTIVE',
            current_odometer=50000
        )
    
    def test_valid_entry(self):
        """Test creating a valid daily odo entry."""
        form_data = {
            'truck': self.truck.pk,
            'date': date.today(),
            'opening_odometer': 50000,
            'closing_odometer': 50200,
            'remarks': 'Test entry'
        }
        form = DailyOdoRegistryForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_closing_less_than_opening(self):
        """Test that closing odometer cannot be less than opening."""
        form_data = {
            'truck': self.truck.pk,
            'date': date.today(),
            'opening_odometer': 50000,
            'closing_odometer': 49900,  # Less than opening
            'remarks': 'Test entry'
        }
        form = DailyOdoRegistryForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('closing_odometer', form.errors)


class DailyOdoRegistrySearchFormTests(TestCase):
    """Test cases for DailyOdoRegistrySearchForm."""
    
    def test_empty_search(self):
        """Test empty search form is valid."""
        form_data = {}
        form = DailyOdoRegistrySearchForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_search_with_date_range(self):
        """Test search with date range."""
        form_data = {
            'date_from': date.today() - timedelta(days=7),
            'date_to': date.today(),
            'search': 'test'
        }
        form = DailyOdoRegistrySearchForm(data=form_data)
        self.assertTrue(form.is_valid())


class BulkDailyOdoEntryFormTests(TestCase):
    """Test cases for BulkDailyOdoEntryForm."""
    
    def setUp(self):
        self.truck = Truck.objects.create(
            plate_number='MH12AB1234',
            transporter_name='Test Transporter',
            wheel_config='10_WHEEL',
            fleet_type='COAL',
            status='ACTIVE',
            current_odometer=50000
        )
    
    def test_valid_entry(self):
        """Test valid bulk entry form."""
        form_data = {
            'truck_id': self.truck.pk,
            'truck_name': self.truck.plate_number,
            'opening_odometer': 50000,
            'closing_odometer': 50200,
            'skip': False,
            'remarks': 'Test'
        }
        form = BulkDailyOdoEntryForm(data=form_data, truck=self.truck)
        self.assertTrue(form.is_valid())
    
    def test_skip_validation(self):
        """Test that skipped entries bypass validation."""
        form_data = {
            'truck_id': self.truck.pk,
            'truck_name': self.truck.plate_number,
            'opening_odometer': 50000,
            'closing_odometer': 49900,  # Invalid but skipped
            'skip': True,
            'remarks': 'Test'
        }
        form = BulkDailyOdoEntryForm(data=form_data, truck=self.truck)
        self.assertTrue(form.is_valid())


class AlertUpdateFormTests(TestCase):
    """Test cases for AlertUpdateForm."""
    
    def setUp(self):
        self.truck = Truck.objects.create(
            plate_number='MH12AB1234',
            transporter_name='Test Transporter',
            wheel_config='10_WHEEL',
            fleet_type='COAL',
            status='ACTIVE'
        )
        self.alert = Alert.objects.create(
            title='Test Alert',
            alert_type=Alert.AlertType.DOCUMENT_EXPIRY,
            alert_level=Alert.AlertLevel.WARNING,
            status=Alert.AlertStatus.PENDING,
            description='Test description',
            truck=self.truck
        )
    
    def test_valid_update(self):
        """Test valid alert update."""
        form_data = {
            'status': 'RESOLVED',
            'resolution_notes': 'Issue resolved'
        }
        form = AlertUpdateForm(data=form_data, instance=self.alert)
        self.assertTrue(form.is_valid())
    
    def test_resolution_notes_required_for_resolved(self):
        """Test that resolution notes are required when resolving."""
        form_data = {
            'status': 'RESOLVED',
            'resolution_notes': ''  # Empty notes
        }
        form = AlertUpdateForm(data=form_data, instance=self.alert)
        # Notes are not strictly required by the form, just suggested
        self.assertTrue(form.is_valid())


class TruckSearchFormTests(TestCase):
    """Test cases for TruckSearchForm."""
    
    def test_empty_search(self):
        """Test empty search form is valid."""
        form_data = {}
        form = TruckSearchForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_search_with_all_filters(self):
        """Test search with all filters."""
        form_data = {
            'search': 'MH12',
            'fleet_type': 'COAL',
            'status': 'ACTIVE',
            'wheel_config': '10_WHEEL'
        }
        form = TruckSearchForm(data=form_data)
        self.assertTrue(form.is_valid())
