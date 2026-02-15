"""
Unit tests for fleet views.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase, Client, RequestFactory
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone

from fleet.models import (
    UserProfile, Truck, Driver, FuelLog, TireInventory,
    DailyOdoRegistry, DieselPrice, Alert
)
from fleet.views import (
    TruckListView, TruckDetailView, TruckCreateView,
    DriverListView, DriverDetailView,
    FuelLogListView, FuelLogDetailView,
    TireInventoryListView, TireInventoryDetailView,
    DailyOdoRegistryListView, DailyOdoRegistryDetailView
)


class BaseViewTestCase(TestCase):
    """Base test case for view tests."""
    
    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()
        
        # Create admin user
        self.admin_user = User.objects.create_user(
            username='admin',
            password='adminpass123'
        )
        UserProfile.objects.create(
            user=self.admin_user,
            role=UserProfile.Role.ADMIN
        )
        
        # Create fuel agent user
        self.fuel_agent = User.objects.create_user(
            username='fuelagent',
            password='fuelpass123'
        )
        UserProfile.objects.create(
            user=self.fuel_agent,
            role=UserProfile.Role.FUEL_AGENT
        )


class LoginViewTests(BaseViewTestCase):
    """Test cases for LoginView."""
    
    def test_login_page_get(self):
        """Test GET request to login page."""
        response = self.client.get(reverse('fleet:login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'fleet/login.html')
    
    def test_valid_login(self):
        """Test valid login."""
        response = self.client.post(reverse('fleet:login'), {
            'username': 'admin',
            'password': 'adminpass123'
        })
        self.assertEqual(response.status_code, 302)  # Redirect after login
    
    def test_invalid_login(self):
        """Test invalid login credentials."""
        response = self.client.post(reverse('fleet:login'), {
            'username': 'admin',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 200)  # Stay on login page
        self.assertContains(response, 'Invalid username or password')


class UserManagementViewTests(BaseViewTestCase):
    """Test cases for user management views."""
    
    def test_user_list_requires_admin(self):
        """Test that user list requires admin access."""
        self.client.login(username='fuelagent', password='fuelpass123')
        response = self.client.get(reverse('fleet:user-list'))
        self.assertEqual(response.status_code, 403)
    
    def test_user_list_as_admin(self):
        """Test user list as admin."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(reverse('fleet:user-list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'fleet/user_list.html')
    
    def test_user_create_as_admin(self):
        """Test user creation as admin."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(reverse('fleet:user-create'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'fleet/user_form.html')


class TruckViewTests(BaseViewTestCase):
    """Test cases for truck views."""
    
    def setUp(self):
        super().setUp()
        self.truck = Truck.objects.create(
            plate_number='MH12AB1234',
            transporter_name='Test Transporter',
            wheel_config=Truck.WheelConfig.TEN_WHEEL,
            fleet_type=Truck.FleetType.COAL,
            status=Truck.Status.ACTIVE,
            current_odometer=50000
        )
    
    def test_truck_list_authenticated(self):
        """Test truck list for authenticated user."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(reverse('fleet:truck-list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'fleet/truck_list.html')
        self.assertContains(response, 'MH12AB1234')
    
    def test_truck_list_search(self):
        """Test truck list with search filter."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(reverse('fleet:truck-list'), {'search': 'MH12'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'MH12AB1234')
    
    def test_truck_list_fleet_type_filter(self):
        """Test truck list with fleet type filter."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(
            reverse('fleet:truck-list'),
            {'fleet_type': Truck.FleetType.COAL}
        )
        self.assertEqual(response.status_code, 200)
    
    def test_truck_detail_view(self):
        """Test truck detail view."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(
            reverse('fleet:truck-detail', kwargs={'pk': self.truck.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'fleet/truck_detail.html')
        self.assertContains(response, 'MH12AB1234')
    
    def test_truck_create_view_get(self):
        """Test GET request to truck create view."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(reverse('fleet:truck-create'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'fleet/truck_form.html')
    
    def test_truck_create_view_post(self):
        """Test POST request to truck create view."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.post(reverse('fleet:truck-create'), {
            'plate_number': 'MH12CD5678',
            'transporter_name': 'New Transporter',
            'wheel_config': Truck.WheelConfig.TEN_WHEEL,
            'fleet_type': Truck.FleetType.MINING,
            'status': Truck.Status.ACTIVE,
            'current_odometer': 10000
        })
        self.assertEqual(response.status_code, 302)  # Redirect after creation
        self.assertTrue(Truck.objects.filter(plate_number='MH12CD5678').exists())
    
    def test_truck_update_view(self):
        """Test truck update view."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.post(
            reverse('fleet:truck-update', kwargs={'pk': self.truck.pk}),
            {
                'plate_number': 'MH12AB1234',
                'transporter_name': 'Updated Transporter',
                'wheel_config': Truck.WheelConfig.TEN_WHEEL,
                'fleet_type': Truck.FleetType.COAL,
                'status': Truck.Status.MAINTENANCE,
                'current_odometer': 55000
            }
        )
        self.assertEqual(response.status_code, 302)
        self.truck.refresh_from_db()
        self.assertEqual(self.truck.transporter_name, 'Updated Transporter')
        self.assertEqual(self.truck.status, Truck.Status.MAINTENANCE)


class DriverViewTests(BaseViewTestCase):
    """Test cases for driver views."""
    
    def setUp(self):
        super().setUp()
        self.driver = Driver.objects.create(
            name='John Doe',
            license_number='DL12345678',
            phone='9876543210',
            status=Driver.Status.ON_DUTY,
            driver_type=Driver.DriverType.PERMANENT
        )
    
    def test_driver_list_view(self):
        """Test driver list view."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(reverse('fleet:driver-list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'fleet/driver_list.html')
        self.assertContains(response, 'John Doe')
    
    def test_driver_detail_view(self):
        """Test driver detail view."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(
            reverse('fleet:driver-detail', kwargs={'pk': self.driver.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'fleet/driver_detail.html')
        self.assertContains(response, 'John Doe')
    
    def test_driver_create_view(self):
        """Test driver create view."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.post(reverse('fleet:driver-create'), {
            'name': 'Jane Doe',
            'license_number': 'DL87654321',
            'phone': '9876543211',
            'status': Driver.Status.OFF_DUTY,
            'driver_type': Driver.DriverType.TEMPORARY
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Driver.objects.filter(license_number='DL87654321').exists())


class FuelLogViewTests(BaseViewTestCase):
    """Test cases for fuel log views."""
    
    def setUp(self):
        super().setUp()
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
            fueling_agent=self.admin_user
        )
    
    def test_fuel_log_list_view(self):
        """Test fuel log list view."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(reverse('fleet:fuel-log-list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'fleet/fuel_log_list.html')
    
    def test_fuel_log_detail_view(self):
        """Test fuel log detail view."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(
            reverse('fleet:fuel-log-detail', kwargs={'pk': self.fuel_log.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'fleet/fuel_log_detail.html')
    
    def test_fuel_log_create_view(self):
        """Test fuel log create view."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.post(reverse('fleet:fuel-log-create'), {
            'truck': self.truck.pk,
            'driver': self.driver.pk,
            'date': date.today(),
            'entry_type': FuelLog.EntryType.PER_TRIP,
            'odometer': 50200,
            'fuel_liters': 25.00,
            'diesel_price': 95.50
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(FuelLog.objects.count(), 2)


class TireInventoryViewTests(BaseViewTestCase):
    """Test cases for tire inventory views."""
    
    def setUp(self):
        super().setUp()
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
            status=TireInventory.Status.NEW,
            purchase_cost=Decimal('25000.00')
        )
    
    def test_tire_list_view(self):
        """Test tire list view."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(reverse('fleet:tire-list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'fleet/tire_list.html')
    
    def test_tire_detail_view(self):
        """Test tire detail view."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(
            reverse('fleet:tire-detail', kwargs={'pk': self.tire.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'fleet/tire_detail.html')
    
    def test_tire_create_view(self):
        """Test tire create view."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.post(reverse('fleet:tire-create'), {
            'serial_number': 'TIRE789012',
            'brand': 'Bridgestone',
            'status': TireInventory.Status.NEW,
            'purchase_cost': 20000.00
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(TireInventory.objects.filter(serial_number='TIRE789012').exists())


class DailyOdoRegistryViewTests(BaseViewTestCase):
    """Test cases for daily odometer registry views."""
    
    def setUp(self):
        super().setUp()
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
            remarks='Test entry'
        )
    
    def test_daily_odo_list_view(self):
        """Test daily odometer list view."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(reverse('fleet:daily-odo-list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'fleet/daily_odo_list.html')
    
    def test_daily_odo_detail_view(self):
        """Test daily odometer detail view."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(
            reverse('fleet:daily-odo-detail', kwargs={'pk': self.entry.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'fleet/daily_odo_detail.html')
    
    def test_daily_odo_create_view(self):
        """Test daily odometer create view."""
        self.client.login(username='admin', password='adminpass123')
        tomorrow = date.today() + timedelta(days=1)
        response = self.client.post(reverse('fleet:daily-odo-create'), {
            'truck': self.truck.pk,
            'date': tomorrow,
            'opening_odometer': 50200,
            'closing_odometer': 50500,
            'remarks': 'New entry'
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(DailyOdoRegistry.objects.count(), 2)


class AlertViewTests(BaseViewTestCase):
    """Test cases for alert views."""
    
    def setUp(self):
        super().setUp()
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
            truck=self.truck
        )
    
    def test_alert_list_view(self):
        """Test alert list view."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(reverse('fleet:alert-list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'fleet/alert_list.html')
    
    def test_alert_detail_view(self):
        """Test alert detail view."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(
            reverse('fleet:alert-detail', kwargs={'pk': self.alert.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'fleet/alert_detail.html')


class UtilityViewTests(BaseViewTestCase):
    """Test cases for utility views."""
    
    def setUp(self):
        super().setUp()
        self.truck = Truck.objects.create(
            plate_number='MH12AB1234',
            transporter_name='Test Transporter',
            wheel_config=Truck.WheelConfig.TEN_WHEEL,
            fleet_type=Truck.FleetType.COAL,
            status=Truck.Status.ACTIVE,
            current_odometer=50000
        )
    
    def test_get_truck_current_odometer(self):
        """Test API endpoint for getting truck odometer."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(
            reverse('fleet:get-truck-odometer', kwargs={'truck_id': self.truck.pk})
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['current_odometer'], 50000)
    
    def test_get_today_diesel_price(self):
        """Test API endpoint for getting today's diesel price."""
        self.client.login(username='admin', password='adminpass123')
        # Create a diesel price entry
        DieselPrice.objects.create(date=date.today(), price=Decimal('95.50'))
        response = self.client.get(reverse('fleet:fuel-diesel-price'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['price'], 95.50)
    
    def test_update_diesel_price(self):
        """Test API endpoint for updating diesel price."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.post(
            reverse('fleet:fuel-update-diesel-price'),
            {'date': date.today(), 'price': 96.00}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertTrue(DieselPrice.objects.filter(price=Decimal('96.00')).exists())


class PermissionViewTests(BaseViewTestCase):
    """Test cases for permission-based access."""
    
    def test_anonymous_access_redirect(self):
        """Test that anonymous users are redirected to login."""
        response = self.client.get(reverse('fleet:truck-list'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_fuel_agent_can_access_fuel_logs(self):
        """Test that fuel agents can access fuel logs."""
        self.client.login(username='fuelagent', password='fuelpass123')
        response = self.client.get(reverse('fleet:fuel-log-list'))
        self.assertEqual(response.status_code, 200)
