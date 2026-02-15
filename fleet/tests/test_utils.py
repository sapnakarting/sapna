"""
Unit tests for fleet utilities.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from fleet.utils.expiry_helpers import get_expiry_color_code
from fleet.utils.fuel_attribution import calculate_attribution_date
from fleet.utils.tire_mileage import calculate_current_mileage as calc_tire_mileage
from fleet.utils.date_helpers import get_month_start_end, get_week_start_end
from fleet.models import Truck, TireInventory, FuelLog


class ExpiryHelpersTests(TestCase):
    """Test cases for expiry_helpers module."""
    
    def test_get_expiry_color_code_critical(self):
        """Test color code for critical expiry (0-7 days)."""
        expiry = date.today() + timedelta(days=5)
        result = get_expiry_color_code(expiry)
        self.assertEqual(result['color'], 'red')
        self.assertEqual(result['status'], 'CRITICAL')
    
    def test_get_expiry_color_code_warning(self):
        """Test color code for warning expiry (8-15 days)."""
        expiry = date.today() + timedelta(days=10)
        result = get_expiry_color_code(expiry)
        self.assertEqual(result['color'], 'orange')
        self.assertEqual(result['status'], 'WARNING')
    
    def test_get_expiry_color_code_info(self):
        """Test color code for info expiry (16-30 days)."""
        expiry = date.today() + timedelta(days=20)
        result = get_expiry_color_code(expiry)
        self.assertEqual(result['color'], 'yellow')
        self.assertEqual(result['status'], 'INFO')
    
    def test_get_expiry_color_code_ok(self):
        """Test color code for ok expiry (>30 days)."""
        expiry = date.today() + timedelta(days=45)
        result = get_expiry_color_code(expiry)
        self.assertEqual(result['color'], 'green')
        self.assertEqual(result['status'], 'OK')
    
    def test_get_expiry_color_code_expired(self):
        """Test color code for expired document."""
        expiry = date.today() - timedelta(days=5)
        result = get_expiry_color_code(expiry)
        self.assertEqual(result['color'], 'darkred')
        self.assertEqual(result['status'], 'EXPIRED')
    
    def test_get_expiry_color_code_none(self):
        """Test color code for None expiry."""
        result = get_expiry_color_code(None)
        self.assertEqual(result['color'], 'gray')
        self.assertEqual(result['status'], 'UNKNOWN')


class FuelAttributionTests(TestCase):
    """Test cases for fuel_attribution module."""
    
    def test_calculate_attribution_date_full_tank(self):
        """Test attribution date for full tank entry."""
        entry_date = date(2024, 1, 15)
        result = calculate_attribution_date(entry_date, FuelLog.EntryType.FULL_TANK)
        self.assertEqual(result, entry_date)
    
    def test_calculate_attribution_date_per_trip(self):
        """Test attribution date for per trip entry (previous day)."""
        entry_date = date(2024, 1, 15)
        result = calculate_attribution_date(entry_date, FuelLog.EntryType.PER_TRIP)
        self.assertEqual(result, date(2024, 1, 14))
    
    def test_calculate_attribution_date_none_date(self):
        """Test attribution date with None date."""
        result = calculate_attribution_date(None, FuelLog.EntryType.FULL_TANK)
        self.assertIsNone(result)
    
    def test_calculate_attribution_date_none_entry_type(self):
        """Test attribution date with None entry type."""
        entry_date = date(2024, 1, 15)
        result = calculate_attribution_date(entry_date, None)
        self.assertIsNone(result)


class TireMileageTests(TestCase):
    """Test cases for tire_mileage module."""
    
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
            historical_mileage=10000,
            mounted_at_odometer=40000
        )
    
    def test_calculate_current_mileage_mounted(self):
        """Test mileage calculation for mounted tire."""
        # Truck at 50000, mounted at 40000, historical 10000
        # Expected: 10000 + (50000 - 40000) = 20000
        result = calc_tire_mileage(self.tire, self.truck.current_odometer)
        self.assertEqual(result, 20000)
    
    def test_calculate_current_mileage_no_truck(self):
        """Test mileage calculation for unmounted tire."""
        self.tire.truck = None
        self.tire.save()
        result = calc_tire_mileage(self.tire, None)
        self.assertEqual(result, 10000)  # Just historical mileage
    
    def test_calculate_current_mileage_none_truck_odo(self):
        """Test mileage calculation when truck odometer is None."""
        result = calc_tire_mileage(self.tire, None)
        self.assertEqual(result, 10000)  # Just historical mileage
    
    def test_calculate_current_mileage_no_mounted_odo(self):
        """Test mileage calculation when mounted_at_odometer is None."""
        self.tire.mounted_at_odometer = None
        self.tire.save()
        result = calc_tire_mileage(self.tire, self.truck.current_odometer)
        self.assertEqual(result, 10000)  # Just historical mileage


class DateHelpersTests(TestCase):
    """Test cases for date_helpers module."""
    
    def test_get_month_start_end(self):
        """Test getting month start and end dates."""
        today = date(2024, 1, 15)
        start, end = get_month_start_end(today)
        self.assertEqual(start, date(2024, 1, 1))
        self.assertEqual(end, date(2024, 1, 31))
    
    def test_get_month_start_end_february(self):
        """Test getting month start and end for February."""
        today = date(2024, 2, 15)
        start, end = get_month_start_end(today)
        self.assertEqual(start, date(2024, 2, 1))
        self.assertEqual(end, date(2024, 2, 29))  # 2024 is a leap year
    
    def test_get_week_start_end(self):
        """Test getting week start and end dates."""
        today = date(2024, 1, 17)  # Wednesday
        start, end = get_week_start_end(today)
        self.assertEqual(start, date(2024, 1, 15))  # Monday
        self.assertEqual(end, date(2024, 1, 21))  # Sunday


class DieselPoolTests(TestCase):
    """Test cases for diesel_pool module."""
    
    def test_diesel_pool_import(self):
        """Test that diesel_pool module can be imported."""
        from fleet.utils.diesel_pool import get_pool_balance
        # This is a stub test - the actual functionality would require
        # more complex setup with the actual diesel pool implementation
        self.assertTrue(callable(get_pool_balance))


class PermissionsTests(TestCase):
    """Test cases for permissions module."""
    
    def setUp(self):
        from django.contrib.auth.models import User
        self.admin_user = User.objects.create_user(
            username='admin',
            password='adminpass123'
        )
        from fleet.models import UserProfile
        UserProfile.objects.create(
            user=self.admin_user,
            role=UserProfile.Role.ADMIN
        )
        
        self.fuel_agent = User.objects.create_user(
            username='fuelagent',
            password='fuelpass123'
        )
        UserProfile.objects.create(
            user=self.fuel_agent,
            role=UserProfile.Role.FUEL_AGENT
        )
    
    def test_is_admin_required(self):
        """Test admin permission decorator."""
        from fleet.utils.permissions import is_admin_required
        from django.http import HttpResponse
        
        @is_admin_required
        def test_view(request):
            return HttpResponse('Admin only')
        
        from django.test import RequestFactory
        factory = RequestFactory()
        
        # Test admin access
        request = factory.get('/test/')
        request.user = self.admin_user
        response = test_view(request)
        self.assertEqual(response.status_code, 200)
    
    def test_is_fuel_agent_required(self):
        """Test fuel agent permission decorator."""
        from fleet.utils.permissions import is_fuel_agent_required
        from django.http import HttpResponse
        
        @is_fuel_agent_required
        def test_view(request):
            return HttpResponse('Fuel agent only')
        
        from django.test import RequestFactory
        factory = RequestFactory()
        
        # Test fuel agent access
        request = factory.get('/test/')
        request.user = self.fuel_agent
        response = test_view(request)
        self.assertEqual(response.status_code, 200)


class UtilityIntegrationTests(TestCase):
    """Integration tests for utility modules."""
    
    def setUp(self):
        self.truck = Truck.objects.create(
            plate_number='MH12AB1234',
            transporter_name='Test Transporter',
            wheel_config=Truck.WheelConfig.TEN_WHEEL,
            fleet_type=Truck.FleetType.COAL,
            status=Truck.Status.ACTIVE,
            current_odometer=50000,
            fitness_expiry=date.today() + timedelta(days=30),
            insurance_expiry=date.today() + timedelta(days=60),
            pucc_expiry=date.today() + timedelta(days=15),
            tax_expiry=date.today() + timedelta(days=90),
            permit_expiry=date.today() + timedelta(days=45)
        )
    
    def test_truck_expiry_color_codes(self):
        """Test getting all expiry color codes for a truck."""
        colors = self.truck.get_expiry_color_code()
        
        self.assertIn('fitness', colors)
        self.assertIn('insurance', colors)
        self.assertIn('pucc', colors)
        self.assertIn('tax', colors)
        self.assertIn('permit', colors)
        
        # PUCC expires in 15 days (WARNING)
        self.assertEqual(colors['pucc']['status'], 'WARNING')
        
        # Others are OK (>30 days)
        self.assertEqual(colors['tax']['status'], 'OK')
        self.assertEqual(colors['permit']['status'], 'OK')
