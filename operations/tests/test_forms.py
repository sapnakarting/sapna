"""
Unit tests for operations forms.
"""

from datetime import date, time
from decimal import Decimal

from django.test import TestCase
from django.contrib.auth.models import User

from fleet.models import Truck
from operations.forms import CoalLogForm, CoalLogSearchForm, MiningLogForm, MiningLogSearchForm
from operations.models import CoalLog, MiningLog


class CoalLogFormTests(TestCase):
    """Test cases for CoalLogForm."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.truck = Truck.objects.create(
            plate_number='MH12AB1234',
            transporter_name='Test Transporter',
            wheel_config=Truck.WheelConfig.TEN_WHEEL,
            fleet_type=Truck.FleetType.COAL,
            status=Truck.Status.ACTIVE
        )
    
    def test_valid_coal_log_creation(self):
        """Test creating a coal log with valid data."""
        form_data = {
            'truck': self.truck.pk,
            'date': date.today(),
            'pass_no': 'PASS123456',
            'gross_weight': 50000.00,
            'tare_weight': 15000.00,
            'diesel_liters': 100.00,
            'diesel_rate': 95.50,
            'origin_site': 'Mines A',
            'destination_site': 'Plant B',
            'trip_remarks': 'Test trip',
            'diesel_remarks': 'Test diesel',
            'diesel_adjustment': 0.00,
            'air_adjustment': 0.00,
            'air_remarks': '',
            'trip_adjustment': 0.00
        }
        form = CoalLogForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_net_weight_calculation(self):
        """Test that net weight is calculated from gross and tare."""
        form_data = {
            'truck': self.truck.pk,
            'date': date.today(),
            'pass_no': 'PASS123456',
            'gross_weight': 50000.00,
            'tare_weight': 15000.00,
            'diesel_liters': 100.00,
            'diesel_rate': 95.50,
            'origin_site': 'Mines A',
            'destination_site': 'Plant B'
        }
        form = CoalLogForm(data=form_data)
        self.assertTrue(form.is_valid())
        coal_log = form.save(commit=False)
        coal_log.created_by = self.user
        coal_log.save()
        self.assertEqual(coal_log.net_weight, Decimal('35000.00'))
    
    def test_diesel_cost_calculation(self):
        """Test that diesel cost is calculated from liters and rate."""
        form_data = {
            'truck': self.truck.pk,
            'date': date.today(),
            'pass_no': 'PASS123456',
            'gross_weight': 50000.00,
            'tare_weight': 15000.00,
            'diesel_liters': 100.00,
            'diesel_rate': 95.50,
            'origin_site': 'Mines A',
            'destination_site': 'Plant B'
        }
        form = CoalLogForm(data=form_data)
        self.assertTrue(form.is_valid())
        coal_log = form.save(commit=False)
        coal_log.created_by = self.user
        coal_log.save()
        expected_cost = Decimal('100.00') * Decimal('95.50')
        self.assertEqual(coal_log.diesel_cost, expected_cost)
    
    def test_missing_required_fields(self):
        """Test that required fields are enforced."""
        form_data = {
            'truck': self.truck.pk,
            'date': date.today()
            # Missing pass_no, gross_weight, etc.
        }
        form = CoalLogForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('pass_no', form.errors)
        self.assertIn('gross_weight', form.errors)
        self.assertIn('tare_weight', form.errors)


class CoalLogSearchFormTests(TestCase):
    """Test cases for CoalLogSearchForm."""
    
    def test_empty_search(self):
        """Test empty search form is valid."""
        form_data = {}
        form = CoalLogSearchForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_search_with_filters(self):
        """Test search with filters."""
        form_data = {
            'date_from': date.today() - __import__('datetime').timedelta(days=7),
            'date_to': date.today(),
            'pass_no': 'PASS',
            'origin_site': 'Mines'
        }
        form = CoalLogSearchForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_search_by_pass_no(self):
        """Test search by pass number."""
        form_data = {
            'pass_no': '123456'
        }
        form = CoalLogSearchForm(data=form_data)
        self.assertTrue(form.is_valid())


class MiningLogFormTests(TestCase):
    """Test cases for MiningLogForm."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.truck = Truck.objects.create(
            plate_number='MH12AB1234',
            transporter_name='Test Transporter',
            wheel_config=Truck.WheelConfig.TEN_WHEEL,
            fleet_type=Truck.FleetType.MINING,
            mining_type=Truck.MiningType.INTERNAL,
            status=Truck.Status.ACTIVE
        )
    
    def test_valid_mining_log_creation(self):
        """Test creating a mining log with valid data."""
        form_data = {
            'type': MiningLog.LogType.DISPATCH,
            'date': date.today(),
            'time': '10:30',
            'chalan_no': 'CHALAN123456',
            'customer_name': 'Test Customer',
            'truck': self.truck.pk,
            'net': 35000.00,
            'material': 'Iron Ore',
            'mining_type': MiningLog.MiningType.INTERNAL
        }
        form = MiningLogForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_valid_purchase_log(self):
        """Test creating a purchase type mining log."""
        form_data = {
            'type': MiningLog.LogType.PURCHASE,
            'date': date.today(),
            'time': '14:00',
            'chalan_no': 'CHALAN789012',
            'customer_name': 'Another Customer',
            'truck': self.truck.pk,
            'net': 25000.00,
            'material': 'Coal',
            'mining_type': MiningLog.MiningType.EXTERNAL
        }
        form = MiningLogForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_missing_required_fields(self):
        """Test that required fields are enforced."""
        form_data = {
            'type': MiningLog.LogType.DISPATCH,
            'date': date.today()
            # Missing chalan_no, customer_name, etc.
        }
        form = MiningLogForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('chalan_no', form.errors)
        self.assertIn('customer_name', form.errors)
        self.assertIn('truck', form.errors)
        self.assertIn('net', form.errors)
    
    def test_invalid_time_format(self):
        """Test that invalid time format is rejected."""
        form_data = {
            'type': MiningLog.LogType.DISPATCH,
            'date': date.today(),
            'time': 'invalid',
            'chalan_no': 'CHALAN123456',
            'customer_name': 'Test Customer',
            'truck': self.truck.pk,
            'net': 35000.00,
            'material': 'Iron Ore',
            'mining_type': MiningLog.MiningType.INTERNAL
        }
        form = MiningLogForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('time', form.errors)


class MiningLogSearchFormTests(TestCase):
    """Test cases for MiningLogSearchForm."""
    
    def test_empty_search(self):
        """Test empty search form is valid."""
        form_data = {}
        form = MiningLogSearchForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_search_with_filters(self):
        """Test search with filters."""
        form_data = {
            'date_from': date.today() - __import__('datetime').timedelta(days=7),
            'date_to': date.today(),
            'type': MiningLog.LogType.DISPATCH,
            'mining_type': MiningLog.MiningType.INTERNAL,
            'chalan_no': 'CHALAN',
            'customer_name': 'Customer'
        }
        form = MiningLogSearchForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_search_by_chalan_no(self):
        """Test search by chalan number."""
        form_data = {
            'chalan_no': '123456'
        }
        form = MiningLogSearchForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_search_by_customer_name(self):
        """Test search by customer name."""
        form_data = {
            'customer_name': 'Test Customer'
        }
        form = MiningLogSearchForm(data=form_data)
        self.assertTrue(form.is_valid())
