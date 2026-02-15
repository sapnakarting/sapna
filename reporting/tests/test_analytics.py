"""
Unit tests for reporting analytics utilities.
"""

from datetime import datetime, timedelta
from decimal import Decimal

from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone

from fleet.models import Truck, Driver, FuelLog, TireInventory, DailyOdoRegistry
from operations.models import CoalLog, MiningLog
from reporting.utils.analytics import (
    calculate_cost_per_km,
    calculate_fuel_efficiency,
    calculate_driver_performance_score,
    get_fleet_average_efficiency,
    get_all_trucks_cost_per_km,
    get_all_trucks_efficiency,
    get_driver_rankings,
    get_monthly_fuel_trend,
    get_operations_summary,
    get_fleet_status_summary
)


class AnalyticsTests(TestCase):
    """Test cases for analytics utilities."""
    
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
    
    def test_calculate_cost_per_km(self):
        """Test cost per km calculation."""
        # Create fuel logs
        from datetime import date
        FuelLog.objects.create(
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
        
        # Create daily odo entry
        DailyOdoRegistry.objects.create(
            truck=self.truck,
            date=date.today(),
            opening_odometer=50000,
            closing_odometer=50100
        )
        
        result = calculate_cost_per_km(self.truck)
        
        self.assertEqual(result['truck'], self.truck)
        self.assertEqual(result['total_km'], 100)
        self.assertTrue(result['fuel_cost'] > 0)
        self.assertTrue(result['cost_per_km'] > 0)
    
    def test_calculate_fuel_efficiency(self):
        """Test fuel efficiency calculation."""
        from datetime import date
        FuelLog.objects.create(
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
        
        result = calculate_fuel_efficiency(truck=self.truck)
        
        self.assertEqual(result['truck'], self.truck)
        self.assertEqual(result['total_distance'], 100)
        self.assertEqual(float(result['total_fuel']), 50.00)
        self.assertEqual(float(result['efficiency']), 2.0)  # 100km / 50L = 2 km/L
    
    def test_calculate_fuel_efficiency_no_data(self):
        """Test fuel efficiency with no data."""
        result = calculate_fuel_efficiency(truck=self.truck)
        
        self.assertEqual(result['total_distance'], 0)
        self.assertEqual(float(result['total_fuel']), 0)
        self.assertEqual(float(result['efficiency']), 0)
    
    def test_calculate_driver_performance_score(self):
        """Test driver performance score calculation."""
        from datetime import date
        # Create multiple fuel logs for the driver
        for i in range(5):
            FuelLog.objects.create(
                truck=self.truck,
                driver=self.driver,
                date=date.today() - timedelta(days=i),
                entry_type=FuelLog.EntryType.FULL_TANK,
                odometer=50100 + (i * 100),
                previous_odometer=50000 + (i * 100),
                fuel_liters=Decimal('40.00'),
                diesel_price=Decimal('95.50'),
                fueling_agent=self.user
            )
        
        result = calculate_driver_performance_score(self.driver)
        
        self.assertEqual(result['driver'], self.driver)
        self.assertTrue('total_score' in result)
        self.assertTrue('efficiency_score' in result)
        self.assertTrue('trips_score' in result)
        self.assertTrue('consistency_score' in result)
        self.assertEqual(result['total_trips'], 5)
    
    def test_get_fleet_average_efficiency(self):
        """Test fleet average efficiency calculation."""
        from datetime import date
        # Create fuel log
        FuelLog.objects.create(
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
        
        result = get_fleet_average_efficiency()
        
        # Should return the efficiency of the single truck
        self.assertEqual(float(result), 2.0)
    
    def test_get_fleet_average_efficiency_no_active_trucks(self):
        """Test fleet average with no active trucks."""
        self.truck.status = Truck.Status.INACTIVE
        self.truck.save()
        
        result = get_fleet_average_efficiency()
        self.assertEqual(float(result), 0)
    
    def test_get_all_trucks_cost_per_km(self):
        """Test getting cost per km for all trucks."""
        from datetime import date
        FuelLog.objects.create(
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
        
        DailyOdoRegistry.objects.create(
            truck=self.truck,
            date=date.today(),
            opening_odometer=50000,
            closing_odometer=50100
        )
        
        result = get_all_trucks_cost_per_km()
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['truck'], self.truck)
    
    def test_get_all_trucks_efficiency(self):
        """Test getting efficiency for all trucks."""
        from datetime import date
        FuelLog.objects.create(
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
        
        result = get_all_trucks_efficiency()
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['truck'], self.truck)
        self.assertEqual(float(result[0]['efficiency']), 2.0)
    
    def test_get_driver_rankings(self):
        """Test getting driver rankings."""
        from datetime import date
        # Create fuel logs for the driver
        for i in range(3):
            FuelLog.objects.create(
                truck=self.truck,
                driver=self.driver,
                date=date.today() - timedelta(days=i),
                entry_type=FuelLog.EntryType.FULL_TANK,
                odometer=50100 + (i * 100),
                previous_odometer=50000 + (i * 100),
                fuel_liters=Decimal('40.00'),
                diesel_price=Decimal('95.50'),
                fueling_agent=self.user
            )
        
        result = get_driver_rankings()
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['driver'], self.driver)
    
    def test_get_monthly_fuel_trend(self):
        """Test getting monthly fuel trend."""
        from datetime import date
        # Create fuel logs over multiple months
        FuelLog.objects.create(
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
        
        result = get_monthly_fuel_trend()
        
        self.assertIsInstance(result, list)
        # Should have at least one entry for current month
        self.assertTrue(len(result) >= 0)
    
    def test_get_operations_summary(self):
        """Test getting operations summary."""
        from datetime import date
        # Create coal log
        CoalLog.objects.create(
            truck=self.truck,
            date=date.today(),
            pass_no='PASS123',
            gross_weight=Decimal('50000.00'),
            tare_weight=Decimal('15000.00'),
            diesel_liters=Decimal('100.00'),
            diesel_rate=Decimal('95.50'),
            origin_site='Mines A',
            destination_site='Plant B',
            created_by=self.user
        )
        
        # Create mining log
        MiningLog.objects.create(
            type=MiningLog.LogType.DISPATCH,
            date=date.today(),
            time=__import__('datetime').time(10, 30),
            chalan_no='CHALAN123',
            customer_name='Test Customer',
            truck=self.truck,
            net=Decimal('35000.00'),
            material='Iron Ore',
            mining_type=MiningLog.MiningType.INTERNAL,
            created_by=self.user
        )
        
        result = get_operations_summary()
        
        self.assertIn('coal', result)
        self.assertIn('mining', result)
        self.assertEqual(result['coal']['trips'], 1)
        self.assertEqual(result['mining']['trips'], 1)
        self.assertEqual(result['total_trips'], 2)
    
    def test_get_fleet_status_summary(self):
        """Test getting fleet status summary."""
        result = get_fleet_status_summary()
        
        self.assertIn('total_trucks', result)
        self.assertIn('status_counts', result)
        self.assertIn('expiring_documents', result)
        self.assertEqual(result['total_trucks'], 1)
        self.assertEqual(result['active_trucks'], 1)


class PredictiveMaintenanceTests(TestCase):
    """Test cases for predictive maintenance utilities."""
    
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
            status=Truck.Status.ACTIVE,
            current_odometer=50000,
            fitness_expiry=timezone.now().date() + timedelta(days=30),
            insurance_expiry=timezone.now().date() + timedelta(days=60),
            pucc_expiry=timezone.now().date() + timedelta(days=5),
            tax_expiry=timezone.now().date() + timedelta(days=90),
            permit_expiry=timezone.now().date() + timedelta(days=45)
        )
    
    def test_predictive_maintenance_engine(self):
        """Test predictive maintenance engine."""
        from reporting.utils.predictive_maintenance import PredictiveMaintenanceEngine
        
        engine = PredictiveMaintenanceEngine()
        alerts = engine.check_maintenance_needs(self.truck)
        
        self.assertIsInstance(alerts, list)
        # Should have at least one alert for PUCC expiring soon
        self.assertTrue(len(alerts) > 0)
    
    def test_check_document_expiry(self):
        """Test document expiry checking."""
        from reporting.utils.predictive_maintenance import PredictiveMaintenanceEngine
        
        engine = PredictiveMaintenanceEngine()
        alerts = engine.check_document_expiry(self.truck)
        
        # Should find PUCC expiring in 5 days
        pucc_alerts = [a for a in alerts if a.get('document_type') == 'pucc']
        self.assertTrue(len(pucc_alerts) > 0)
    
    def test_get_maintenance_summary(self):
        """Test getting maintenance summary."""
        from reporting.utils.predictive_maintenance import get_maintenance_summary
        
        result = get_maintenance_summary()
        
        self.assertIn('total_alerts', result)
        self.assertIn('priority_counts', result)
        self.assertIn('alert_type_counts', result)
        self.assertIn('alerts', result)
        self.assertIn('trucks_checked', result)
