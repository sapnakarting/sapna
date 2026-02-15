"""
Unit tests for Gemini AI integration.
"""

import json
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock

from django.test import TestCase, override_settings
from django.contrib.auth.models import User
from django.utils import timezone

from fleet.models import Truck, Driver, FuelLog, TireInventory, DailyOdoRegistry
from operations.models import MiningLog
from reporting.utils.gemini_ai import (
    GeminiAIService,
    GeminiAIError,
    FuelEfficiencyInsight,
    AnomalyDetectionResult,
    MaintenanceRecommendation,
    OCRResult,
    get_fuel_efficiency_insights,
    detect_truck_anomalies,
    get_maintenance_recommendations,
    process_mining_chalan,
    get_fleet_ai_report
)


@override_settings(GEMINI_API_KEY='test-api-key')
class GeminiAIServiceTests(TestCase):
    """Test cases for GeminiAIService."""
    
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
    
    def test_service_initialization(self):
        """Test that service initializes correctly with API key."""
        service = GeminiAIService()
        self.assertEqual(service.api_key, 'test-api-key')
    
    @override_settings(GEMINI_API_KEY='')
    def test_service_initialization_no_api_key(self):
        """Test that service raises error without API key."""
        with self.assertRaises(GeminiAIError):
            GeminiAIService()
    
    @patch('reporting.utils.gemini_ai.genai.GenerativeModel')
    def test_generate_fuel_efficiency_insights(self, mock_model_class):
        """Test fuel efficiency insights generation."""
        # Create mock model and response
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            'performance_rating': 'GOOD',
            'insights': ['Insight 1', 'Insight 2'],
            'recommendations': ['Recommendation 1'],
            'potential_savings': {
                'fuel_liters_per_month': 100.0,
                'cost_savings_per_month_inr': 9550.0,
                'efficiency_improvement_percent': 5.0
            }
        })
        mock_model.generate_content.return_value = mock_response
        
        # Create fuel logs for the truck
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
        
        service = GeminiAIService()
        insights = service.generate_fuel_efficiency_insights(self.truck, days=30)
        
        self.assertIsInstance(insights, FuelEfficiencyInsight)
        self.assertEqual(insights.truck_id, self.truck.id)
        self.assertEqual(insights.performance_rating, 'GOOD')
        self.assertEqual(len(insights.insights), 2)
        self.assertEqual(len(insights.recommendations), 1)
    
    @patch('reporting.utils.gemini_ai.genai.GenerativeModel')
    def test_detect_anomalies(self, mock_model_class):
        """Test anomaly detection."""
        # Create mock model and response
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            'anomalies': [
                {
                    'anomaly_type': 'FUEL_EFFICIENCY_DROP',
                    'severity': 'HIGH',
                    'description': 'Fuel efficiency dropped significantly',
                    'detected_value': 2.5,
                    'expected_range': {'min': 3.0, 'max': 5.0},
                    'recommended_action': 'Check fuel system'
                }
            ]
        })
        mock_model.generate_content.return_value = mock_response
        
        # Create daily odometer entries
        DailyOdoRegistry.objects.create(
            truck=self.truck,
            date=date.today() - timedelta(days=1),
            opening_odometer=49800,
            closing_odometer=50000
        )
        
        service = GeminiAIService()
        anomalies = service.detect_anomalies(self.truck, days=30)
        
        self.assertIsInstance(anomalies, list)
        self.assertEqual(len(anomalies), 1)
        self.assertIsInstance(anomalies[0], AnomalyDetectionResult)
        self.assertEqual(anomalies[0].anomaly_type, 'FUEL_EFFICIENCY_DROP')
        self.assertEqual(anomalies[0].severity, 'HIGH')
    
    @patch('reporting.utils.gemini_ai.genai.GenerativeModel')
    def test_generate_maintenance_recommendations(self, mock_model_class):
        """Test maintenance recommendations generation."""
        # Create mock model and response
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            'recommendations': [
                {
                    'priority': 'HIGH',
                    'maintenance_type': 'PREVENTIVE',
                    'description': 'Oil change due',
                    'estimated_cost_inr': 2500.0,
                    'estimated_downtime': '2-3 hours',
                    'recommended_date': (timezone.now() + timedelta(days=7)).strftime('%Y-%m-%d'),
                    'rationale': 'Based on mileage'
                }
            ]
        })
        mock_model.generate_content.return_value = mock_response
        
        service = GeminiAIService()
        recommendations = service.generate_maintenance_recommendations(self.truck)
        
        self.assertIsInstance(recommendations, list)
        self.assertEqual(len(recommendations), 1)
        self.assertIsInstance(recommendations[0], MaintenanceRecommendation)
        self.assertEqual(recommendations[0].priority, 'HIGH')
        self.assertEqual(recommendations[0].maintenance_type, 'PREVENTIVE')
    
    @patch('reporting.utils.gemini_ai.genai.GenerativeModel')
    @patch('reporting.utils.gemini_ai.genai.upload_file')
    @patch('os.path.exists')
    def test_process_chalan_ocr(self, mock_exists, mock_upload, mock_model_class):
        """Test OCR processing for mining chalan."""
        mock_exists.return_value = True
        mock_upload.return_value = MagicMock()
        
        # Create mock model and response
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            'chalan_no': 'CHALAN123456',
            'date': '2024-01-15',
            'customer_name': 'Test Customer',
            'net_weight': 35.5,
            'material': 'Iron Ore',
            'confidence_score': 0.85,
            'raw_text': 'Raw OCR text content'
        })
        mock_model.generate_content.return_value = mock_response
        
        service = GeminiAIService()
        result = service.process_chalan_ocr('/path/to/image.jpg')
        
        self.assertIsInstance(result, OCRResult)
        self.assertTrue(result.success)
        self.assertEqual(result.chalan_no, 'CHALAN123456')
        self.assertEqual(result.customer_name, 'Test Customer')
        self.assertEqual(result.net_weight, 35.5)
        self.assertEqual(result.material, 'Iron Ore')
        self.assertEqual(result.confidence_score, 0.85)
    
    def test_process_chalan_ocr_file_not_found(self):
        """Test OCR processing when file doesn't exist."""
        service = GeminiAIService()
        result = service.process_chalan_ocr('/nonexistent/path.jpg')
        
        self.assertIsInstance(result, OCRResult)
        self.assertFalse(result.success)
        self.assertIn('Image file not found', result.errors)
    
    @patch('reporting.utils.gemini_ai.genai.GenerativeModel')
    def test_generate_fleet_insights_report(self, mock_model_class):
        """Test fleet insights report generation."""
        # Create mock model and response
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            'executive_summary': 'Fleet is performing well',
            'key_findings': ['Finding 1', 'Finding 2'],
            'performance_analysis': {
                'overall_rating': 'GOOD',
                'top_performers': ['MH12AB1234'],
                'underperformers': []
            },
            'recommendations': [
                {
                    'category': 'FUEL_EFFICIENCY',
                    'priority': 'HIGH',
                    'action': 'Optimize routes',
                    'expected_impact': '10% fuel savings'
                }
            ],
            'cost_optimization': {
                'potential_savings_monthly_inr': 50000.0,
                'fuel_efficiency_targets': 'Target 4 km/l',
                'action_items': ['Item 1', 'Item 2']
            }
        })
        mock_model.generate_content.return_value = mock_response
        
        # Create fuel logs
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
        
        service = GeminiAIService()
        report = service.generate_fleet_insights_report(days=30)
        
        self.assertIsInstance(report, dict)
        self.assertIn('executive_summary', report)
        self.assertIn('key_findings', report)
        self.assertIn('performance_analysis', report)
        self.assertIn('recommendations', report)
        self.assertIn('cost_optimization', report)
    
    @patch('reporting.utils.gemini_ai.genai.GenerativeModel')
    def test_invalid_json_response(self, mock_model_class):
        """Test handling of invalid JSON response."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model
        mock_response = MagicMock()
        mock_response.text = 'Invalid JSON response'
        mock_model.generate_content.return_value = mock_response
        
        service = GeminiAIService()
        
        with self.assertRaises(GeminiAIError):
            service.generate_fuel_efficiency_insights(self.truck)


class DataClassTests(TestCase):
    """Test cases for data classes."""
    
    def test_fuel_efficiency_insight(self):
        """Test FuelEfficiencyInsight data class."""
        insight = FuelEfficiencyInsight(
            truck_id=1,
            truck_plate='MH12AB1234',
            current_efficiency=3.5,
            fleet_average=3.2,
            performance_rating='GOOD',
            insights=['Insight 1'],
            recommendations=['Rec 1'],
            potential_savings={'fuel': 100},
            generated_at=timezone.now()
        )
        self.assertEqual(insight.truck_plate, 'MH12AB1234')
        self.assertEqual(insight.performance_rating, 'GOOD')
    
    def test_anomaly_detection_result(self):
        """Test AnomalyDetectionResult data class."""
        result = AnomalyDetectionResult(
            truck_id=1,
            truck_plate='MH12AB1234',
            anomaly_type='FUEL_EFFICIENCY_DROP',
            severity='HIGH',
            description='Test anomaly',
            detected_value=2.5,
            expected_range={'min': 3.0, 'max': 5.0},
            recommended_action='Check fuel system',
            detected_at=timezone.now()
        )
        self.assertEqual(result.anomaly_type, 'FUEL_EFFICIENCY_DROP')
        self.assertEqual(result.severity, 'HIGH')
    
    def test_maintenance_recommendation(self):
        """Test MaintenanceRecommendation data class."""
        rec = MaintenanceRecommendation(
            truck_id=1,
            truck_plate='MH12AB1234',
            priority='HIGH',
            maintenance_type='PREVENTIVE',
            description='Oil change',
            estimated_cost=2500.0,
            estimated_downtime='2-3 hours',
            recommended_date=timezone.now(),
            rationale='Due to mileage',
            generated_at=timezone.now()
        )
        self.assertEqual(rec.priority, 'HIGH')
        self.assertEqual(rec.estimated_cost, 2500.0)
    
    def test_ocr_result(self):
        """Test OCRResult data class."""
        result = OCRResult(
            success=True,
            chalan_no='CHALAN123',
            date='2024-01-15',
            customer_name='Test',
            net_weight=35.5,
            material='Iron Ore',
            confidence_score=0.85,
            raw_text='Raw text',
            processed_at=timezone.now(),
            errors=[]
        )
        self.assertTrue(result.success)
        self.assertEqual(result.confidence_score, 0.85)
    
    def test_ocr_result_failure(self):
        """Test OCRResult with failure."""
        result = OCRResult(
            success=False,
            chalan_no=None,
            date=None,
            customer_name=None,
            net_weight=None,
            material=None,
            confidence_score=0.0,
            raw_text='',
            processed_at=timezone.now(),
            errors=['File not found']
        )
        self.assertFalse(result.success)
        self.assertIn('File not found', result.errors)


class ConvenienceFunctionTests(TestCase):
    """Test cases for convenience functions."""
    
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
    
    @patch('reporting.utils.gemini_ai.GeminiAIService')
    def test_get_fuel_efficiency_insights(self, mock_service_class):
        """Test get_fuel_efficiency_insights convenience function."""
        mock_service = MagicMock()
        mock_insight = MagicMock(spec=FuelEfficiencyInsight)
        mock_service.generate_fuel_efficiency_insights.return_value = mock_insight
        mock_service_class.return_value = mock_service
        
        result = get_fuel_efficiency_insights(self.truck.id, days=30)
        
        self.assertEqual(result, mock_insight)
        mock_service.generate_fuel_efficiency_insights.assert_called_once_with(self.truck, 30)
    
    @patch('reporting.utils.gemini_ai.GeminiAIService')
    def test_detect_truck_anomalies(self, mock_service_class):
        """Test detect_truck_anomalies convenience function."""
        mock_service = MagicMock()
        mock_anomalies = [MagicMock(spec=AnomalyDetectionResult)]
        mock_service.detect_anomalies.return_value = mock_anomalies
        mock_service_class.return_value = mock_service
        
        result = detect_truck_anomalies(self.truck.id, days=30)
        
        self.assertEqual(result, mock_anomalies)
        mock_service.detect_anomalies.assert_called_once_with(self.truck, 30)
    
    @patch('reporting.utils.gemini_ai.GeminiAIService')
    def test_get_maintenance_recommendations(self, mock_service_class):
        """Test get_maintenance_recommendations convenience function."""
        mock_service = MagicMock()
        mock_recommendations = [MagicMock(spec=MaintenanceRecommendation)]
        mock_service.generate_maintenance_recommendations.return_value = mock_recommendations
        mock_service_class.return_value = mock_service
        
        result = get_maintenance_recommendations(self.truck.id)
        
        self.assertEqual(result, mock_recommendations)
        mock_service.generate_maintenance_recommendations.assert_called_once_with(self.truck)
    
    @patch('reporting.utils.gemini_ai.GeminiAIService')
    @patch('os.path.exists')
    def test_process_mining_chalan(self, mock_exists, mock_service_class):
        """Test process_mining_chalan convenience function."""
        mock_exists.return_value = True
        mock_service = MagicMock()
        mock_result = MagicMock(spec=OCRResult)
        mock_service.process_chalan_ocr.return_value = mock_result
        mock_service_class.return_value = mock_service
        
        result = process_mining_chalan('/path/to/image.jpg')
        
        self.assertEqual(result, mock_result)
        mock_service.process_chalan_ocr.assert_called_once()
    
    @patch('reporting.utils.gemini_ai.GeminiAIService')
    def test_get_fleet_ai_report(self, mock_service_class):
        """Test get_fleet_ai_report convenience function."""
        mock_service = MagicMock()
        mock_report = {'executive_summary': 'Test'}
        mock_service.generate_fleet_insights_report.return_value = mock_report
        mock_service_class.return_value = mock_service
        
        result = get_fleet_ai_report(days=30)
        
        self.assertEqual(result, mock_report)
        mock_service.generate_fleet_insights_report.assert_called_once_with(30)
