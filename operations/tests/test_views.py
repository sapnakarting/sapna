"""
Unit tests for operations views.
"""

from datetime import date, time
from decimal import Decimal

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User

from fleet.models import Truck, UserProfile
from operations.models import CoalLog, MiningLog


class BaseOperationsTestCase(TestCase):
    """Base test case for operations tests."""
    
    def setUp(self):
        self.client = Client()
        
        # Create admin user
        self.admin_user = User.objects.create_user(
            username='admin',
            password='adminpass123'
        )
        UserProfile.objects.create(
            user=self.admin_user,
            role=UserProfile.Role.ADMIN
        )
        
        # Create truck
        self.truck = Truck.objects.create(
            plate_number='MH12AB1234',
            transporter_name='Test Transporter',
            wheel_config=Truck.WheelConfig.TEN_WHEEL,
            fleet_type=Truck.FleetType.COAL,
            status=Truck.Status.ACTIVE
        )


class CoalLogViewTests(BaseOperationsTestCase):
    """Test cases for CoalLog views."""
    
    def setUp(self):
        super().setUp()
        self.coal_log = CoalLog.objects.create(
            truck=self.truck,
            date=date.today(),
            pass_no='PASS123456',
            gross_weight=Decimal('50000.00'),
            tare_weight=Decimal('15000.00'),
            diesel_liters=Decimal('100.00'),
            diesel_rate=Decimal('95.50'),
            origin_site='Mines A',
            destination_site='Plant B',
            created_by=self.admin_user
        )
    
    def test_coal_log_list_view(self):
        """Test coal log list view."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(reverse('operations:coal-log-list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'operations/coal_log_list.html')
    
    def test_coal_log_list_with_filters(self):
        """Test coal log list with filters."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(
            reverse('operations:coal-log-list'),
            {
                'date_from': date.today(),
                'date_to': date.today(),
                'pass_no': 'PASS',
                'origin_site': 'Mines'
            }
        )
        self.assertEqual(response.status_code, 200)
    
    def test_coal_log_detail_view(self):
        """Test coal log detail view."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(
            reverse('operations:coal-log-detail', kwargs={'pk': self.coal_log.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'operations/coal_log_detail.html')
        self.assertContains(response, 'PASS123456')
    
    def test_coal_log_create_view_get(self):
        """Test GET request to coal log create view."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(reverse('operations:coal-log-create'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'operations/coal_log_form.html')
    
    def test_coal_log_create_view_post(self):
        """Test POST request to coal log create view."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.post(reverse('operations:coal-log-create'), {
            'truck': self.truck.pk,
            'date': date.today(),
            'pass_no': 'PASS789012',
            'gross_weight': 45000.00,
            'tare_weight': 14000.00,
            'diesel_liters': 90.00,
            'diesel_rate': 95.50,
            'origin_site': 'Mines B',
            'destination_site': 'Plant C'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(CoalLog.objects.filter(pass_no='PASS789012').exists())
    
    def test_coal_log_update_view(self):
        """Test coal log update view."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.post(
            reverse('operations:coal-log-update', kwargs={'pk': self.coal_log.pk}),
            {
                'truck': self.truck.pk,
                'date': date.today(),
                'pass_no': 'PASS123456',
                'gross_weight': 52000.00,
                'tare_weight': 15000.00,
                'diesel_liters': 100.00,
                'diesel_rate': 95.50,
                'origin_site': 'Mines A',
                'destination_site': 'Plant B'
            }
        )
        self.assertEqual(response.status_code, 302)
        self.coal_log.refresh_from_db()
        self.assertEqual(self.coal_log.gross_weight, Decimal('52000.00'))
    
    def test_coal_log_delete_view(self):
        """Test coal log delete view."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.post(
            reverse('operations:coal-log-delete', kwargs={'pk': self.coal_log.pk})
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(CoalLog.objects.filter(pk=self.coal_log.pk).exists())
    
    def test_coal_log_search_partial(self):
        """Test coal log search partial view (HTMX)."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(
            reverse('operations:coal-log-search'),
            {'pass_no': 'PASS'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'operations/coal_log_list_partial.html')


class MiningLogViewTests(BaseOperationsTestCase):
    """Test cases for MiningLog views."""
    
    def setUp(self):
        super().setUp()
        self.truck.mining_type = Truck.MiningType.INTERNAL
        self.truck.fleet_type = Truck.FleetType.MINING
        self.truck.save()
        
        self.mining_log = MiningLog.objects.create(
            type=MiningLog.LogType.DISPATCH,
            date=date.today(),
            time=time(10, 30),
            chalan_no='CHALAN123456',
            customer_name='Test Customer',
            truck=self.truck,
            net=Decimal('35000.00'),
            material='Iron Ore',
            mining_type=MiningLog.MiningType.INTERNAL,
            created_by=self.admin_user
        )
    
    def test_mining_log_list_view(self):
        """Test mining log list view."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(reverse('operations:mining-log-list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'operations/mining_log_list.html')
    
    def test_mining_log_list_with_filters(self):
        """Test mining log list with filters."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(
            reverse('operations:mining-log-list'),
            {
                'date_from': date.today(),
                'date_to': date.today(),
                'type': MiningLog.LogType.DISPATCH,
                'mining_type': MiningLog.MiningType.INTERNAL,
                'chalan_no': 'CHALAN'
            }
        )
        self.assertEqual(response.status_code, 200)
    
    def test_mining_log_detail_view(self):
        """Test mining log detail view."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(
            reverse('operations:mining-log-detail', kwargs={'pk': self.mining_log.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'operations/mining_log_detail.html')
        self.assertContains(response, 'CHALAN123456')
    
    def test_mining_log_create_view_get(self):
        """Test GET request to mining log create view."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(reverse('operations:mining-log-create'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'operations/mining_log_form.html')
    
    def test_mining_log_create_view_post(self):
        """Test POST request to mining log create view."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.post(reverse('operations:mining-log-create'), {
            'type': MiningLog.LogType.PURCHASE,
            'date': date.today(),
            'time': '14:00',
            'chalan_no': 'CHALAN789012',
            'customer_name': 'Another Customer',
            'truck': self.truck.pk,
            'net': 25000.00,
            'material': 'Coal',
            'mining_type': MiningLog.MiningType.EXTERNAL
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(MiningLog.objects.filter(chalan_no='CHALAN789012').exists())
    
    def test_mining_log_update_view(self):
        """Test mining log update view."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.post(
            reverse('operations:mining-log-update', kwargs={'pk': self.mining_log.pk}),
            {
                'type': MiningLog.LogType.DISPATCH,
                'date': date.today(),
                'time': '11:00',
                'chalan_no': 'CHALAN123456',
                'customer_name': 'Updated Customer',
                'truck': self.truck.pk,
                'net': 36000.00,
                'material': 'Iron Ore',
                'mining_type': MiningLog.MiningType.INTERNAL
            }
        )
        self.assertEqual(response.status_code, 302)
        self.mining_log.refresh_from_db()
        self.assertEqual(self.mining_log.customer_name, 'Updated Customer')
        self.assertEqual(self.mining_log.net, Decimal('36000.00'))
    
    def test_mining_log_delete_view(self):
        """Test mining log delete view."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.post(
            reverse('operations:mining-log-delete', kwargs={'pk': self.mining_log.pk})
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(MiningLog.objects.filter(pk=self.mining_log.pk).exists())
    
    def test_mining_log_search_partial(self):
        """Test mining log search partial view (HTMX)."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(
            reverse('operations:mining-log-search'),
            {'chalan_no': 'CHALAN'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'operations/mining_log_list_partial.html')


class CoalLogAPITests(BaseOperationsTestCase):
    """Test cases for CoalLog API endpoints."""
    
    def setUp(self):
        super().setUp()
        self.coal_log = CoalLog.objects.create(
            truck=self.truck,
            date=date.today(),
            pass_no='PASS123456',
            gross_weight=Decimal('50000.00'),
            tare_weight=Decimal('15000.00'),
            diesel_liters=Decimal('100.00'),
            diesel_rate=Decimal('95.50'),
            origin_site='Mines A',
            destination_site='Plant B',
            created_by=self.admin_user
        )
    
    def test_get_coal_summary(self):
        """Test coal summary API endpoint."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(reverse('operations:get-coal-summary'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('total_trips', data)
        self.assertIn('total_net_weight', data)
        self.assertIn('total_diesel_liters', data)
        self.assertIn('total_diesel_cost', data)
    
    def test_get_coal_summary_with_date_range(self):
        """Test coal summary API with date range."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(
            reverse('operations:get-coal-summary'),
            {
                'date_from': date.today(),
                'date_to': date.today()
            }
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['total_trips'], 1)
    
    def test_calculate_net_weight_ajax(self):
        """Test net weight calculation AJAX endpoint."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.post(
            reverse('operations:calculate-net-weight'),
            {'gross_weight': 50000.00, 'tare_weight': 15000.00}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['net_weight'], 35000.00)
    
    def test_calculate_diesel_cost_ajax(self):
        """Test diesel cost calculation AJAX endpoint."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.post(
            reverse('operations:calculate-diesel-cost'),
            {'diesel_liters': 100.00, 'diesel_rate': 95.50}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        expected_cost = 100.00 * 95.50
        self.assertEqual(data['diesel_cost'], expected_cost)


class MiningLogAPITests(BaseOperationsTestCase):
    """Test cases for MiningLog API endpoints."""
    
    def setUp(self):
        super().setUp()
        self.truck.mining_type = Truck.MiningType.INTERNAL
        self.truck.fleet_type = Truck.FleetType.MINING
        self.truck.save()
        
        self.mining_log = MiningLog.objects.create(
            type=MiningLog.LogType.DISPATCH,
            date=date.today(),
            time=time(10, 30),
            chalan_no='CHALAN123456',
            customer_name='Test Customer',
            truck=self.truck,
            net=Decimal('35000.00'),
            material='Iron Ore',
            mining_type=MiningLog.MiningType.INTERNAL,
            created_by=self.admin_user
        )
    
    def test_get_mining_summary(self):
        """Test mining summary API endpoint."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(reverse('operations:get-mining-summary'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('total_entries', data)
        self.assertIn('total_tonnage', data)
        self.assertIn('dispatch_count', data)
        self.assertIn('purchase_count', data)
        self.assertIn('internal_count', data)
        self.assertIn('external_count', data)
    
    def test_get_mining_summary_with_date_range(self):
        """Test mining summary API with date range."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(
            reverse('operations:get-mining-summary'),
            {
                'date_from': date.today(),
                'date_to': date.today()
            }
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['total_entries'], 1)
        self.assertEqual(data['dispatch_count'], 1)


class PermissionTests(BaseOperationsTestCase):
    """Test cases for permission-based access."""
    
    def test_anonymous_access_redirect(self):
        """Test that anonymous users are redirected to login."""
        response = self.client.get(reverse('operations:coal-log-list'))
        self.assertEqual(response.status_code, 302)
    
    def test_authenticated_access_coal_logs(self):
        """Test authenticated access to coal logs."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(reverse('operations:coal-log-list'))
        self.assertEqual(response.status_code, 200)
    
    def test_authenticated_access_mining_logs(self):
        """Test authenticated access to mining logs."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(reverse('operations:mining-log-list'))
        self.assertEqual(response.status_code, 200)
