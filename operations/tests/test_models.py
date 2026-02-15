"""
Unit tests for operations models.
"""

from datetime import date, time
from decimal import Decimal

from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone

from fleet.models import Truck
from operations.models import CoalLog, MiningLog


class CoalLogModelTests(TestCase):
    """Test cases for CoalLog model."""
    
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
            trip_remarks='Test trip',
            created_by=self.user
        )
    
    def test_coal_log_creation(self):
        """Test that a coal log is created correctly."""
        self.assertEqual(self.coal_log.truck, self.truck)
        self.assertEqual(self.coal_log.pass_no, 'PASS123456')
        self.assertEqual(self.coal_log.gross_weight, Decimal('50000.00'))
        self.assertEqual(self.coal_log.tare_weight, Decimal('15000.00'))
        self.assertEqual(self.coal_log.origin_site, 'Mines A')
        self.assertEqual(self.coal_log.destination_site, 'Plant B')
    
    def test_calculate_net_weight(self):
        """Test the calculate_net_weight method."""
        expected = Decimal('50000.00') - Decimal('15000.00')
        self.assertEqual(self.coal_log.calculate_net_weight(), expected)
    
    def test_net_weight_auto_calculated(self):
        """Test that net weight is auto-calculated on save."""
        expected = Decimal('50000.00') - Decimal('15000.00')
        self.assertEqual(self.coal_log.net_weight, expected)
    
    def test_calculate_diesel_cost(self):
        """Test the calculate_diesel_cost method."""
        expected = Decimal('100.00') * Decimal('95.50')
        self.assertEqual(self.coal_log.calculate_diesel_cost(), expected)
    
    def test_diesel_cost_auto_calculated(self):
        """Test that diesel cost is auto-calculated on save."""
        expected = Decimal('100.00') * Decimal('95.50')
        self.assertEqual(self.coal_log.diesel_cost, expected)
    
    def test_calculate_total_adjustments(self):
        """Test the calculate_total_adjustments method."""
        self.coal_log.diesel_adjustment = Decimal('500.00')
        self.coal_log.air_adjustment = Decimal('200.00')
        self.coal_log.trip_adjustment = Decimal('100.00')
        self.coal_log.save()
        expected = Decimal('800.00')
        self.assertEqual(self.coal_log.calculate_total_adjustments(), expected)
    
    def test_str_representation(self):
        """Test the string representation."""
        expected = f"{self.truck.plate_number} - {self.coal_log.date} - {self.coal_log.pass_no}"
        self.assertEqual(str(self.coal_log), expected)
    
    def test_documents_default(self):
        """Test that documents defaults to empty list."""
        self.assertEqual(self.coal_log.documents, [])
    
    def test_ordering(self):
        """Test that coal logs are ordered by date and created_at descending."""
        coal_log2 = CoalLog.objects.create(
            truck=self.truck,
            date=date.today(),
            pass_no='PASS789012',
            gross_weight=Decimal('45000.00'),
            tare_weight=Decimal('14000.00'),
            diesel_liters=Decimal('90.00'),
            diesel_rate=Decimal('95.50'),
            origin_site='Mines B',
            destination_site='Plant C',
            created_by=self.user
        )
        logs = list(CoalLog.objects.all())
        # Most recently created should be first
        self.assertEqual(logs[0], coal_log2)
        self.assertEqual(logs[1], self.coal_log)


class MiningLogModelTests(TestCase):
    """Test cases for MiningLog model."""
    
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
            created_by=self.user
        )
    
    def test_mining_log_creation(self):
        """Test that a mining log is created correctly."""
        self.assertEqual(self.mining_log.type, MiningLog.LogType.DISPATCH)
        self.assertEqual(self.mining_log.chalan_no, 'CHALAN123456')
        self.assertEqual(self.mining_log.customer_name, 'Test Customer')
        self.assertEqual(self.mining_log.truck, self.truck)
        self.assertEqual(self.mining_log.net, Decimal('35000.00'))
        self.assertEqual(self.mining_log.material, 'Iron Ore')
        self.assertEqual(self.mining_log.mining_type, MiningLog.MiningType.INTERNAL)
    
    def test_chalan_no_unique(self):
        """Test that chalan number must be unique."""
        with self.assertRaises(Exception):
            MiningLog.objects.create(
                type=MiningLog.LogType.PURCHASE,
                date=date.today(),
                time=time(14, 0),
                chalan_no='CHALAN123456',  # Same chalan number
                customer_name='Another Customer',
                truck=self.truck,
                net=Decimal('25000.00'),
                material='Coal',
                mining_type=MiningLog.MiningType.EXTERNAL,
                created_by=self.user
            )
    
    def test_ocr_processed_default(self):
        """Test that ocr_processed defaults to False."""
        self.assertFalse(self.mining_log.ocr_processed)
    
    def test_ocr_data_default(self):
        """Test that ocr_data defaults to None."""
        self.assertIsNone(self.mining_log.ocr_data)
    
    def test_get_document_count(self):
        """Test the get_document_count method."""
        # Initially no documents
        self.assertEqual(self.mining_log.get_document_count(), 0)
        
        # Add documents
        self.mining_log.documents = [
            {'name': 'doc1.pdf', 'path': '/path/to/doc1'},
            {'name': 'doc2.pdf', 'path': '/path/to/doc2'}
        ]
        self.mining_log.save()
        self.assertEqual(self.mining_log.get_document_count(), 2)
    
    def test_str_representation(self):
        """Test the string representation."""
        expected = f"{self.mining_log.chalan_no} - {self.mining_log.customer_name}"
        self.assertEqual(str(self.mining_log), expected)
    
    def test_documents_default(self):
        """Test that documents defaults to empty list."""
        self.assertEqual(self.mining_log.documents, [])
    
    def test_ordering(self):
        """Test that mining logs are ordered by date, time, and created_at descending."""
        mining_log2 = MiningLog.objects.create(
            type=MiningLog.LogType.PURCHASE,
            date=date.today(),
            time=time(15, 0),
            chalan_no='CHALAN789012',
            customer_name='Another Customer',
            truck=self.truck,
            net=Decimal('25000.00'),
            material='Coal',
            mining_type=MiningLog.MiningType.EXTERNAL,
            created_by=self.user
        )
        logs = list(MiningLog.objects.all())
        # Most recent by time should be first (same date, later time)
        self.assertEqual(logs[0], mining_log2)
        self.assertEqual(logs[1], self.mining_log)
    
    def test_log_type_choices(self):
        """Test log type choices."""
        self.assertEqual(MiningLog.LogType.DISPATCH, 'DISPATCH')
        self.assertEqual(MiningLog.LogType.PURCHASE, 'PURCHASE')
    
    def test_mining_type_choices(self):
        """Test mining type choices."""
        self.assertEqual(MiningLog.MiningType.INTERNAL, 'INTERNAL')
        self.assertEqual(MiningLog.MiningType.EXTERNAL, 'EXTERNAL')
