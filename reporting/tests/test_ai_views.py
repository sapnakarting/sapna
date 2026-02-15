"""
Unit tests for AI views.
"""

import json
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock

from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone

from fleet.models import Truck, Driver, FuelLog, UserProfile
from operations.models import MiningLog
from reporting.utils.gemini_ai import (
    FuelEfficiencyInsight,
    AnomalyDetectionResult,
    MaintenanceRecommendation,
    OCRResult
)


@override_settings(GEMINI_API_KEY='test-api-key')
class BaseAIViewTestCase(TestCase):
    """Base test case for AI view tests."""
    
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
        
        # Create fuel agent user
        self.fuel_agent = User.objects.create_user(
            username='fuelagent',
            password='fuelpass123'
        )
        UserProfile.objects.create(
            user=self.fuel_agent,
            role=UserProfile.Role.FUEL_AGENT
        )
        
        # Create truck
        self.truck = Truck.objects.create(
            plate_number='MH12AB1234',
            transporter_name='Test Transporter',
            wheel_config=Truck.WheelConfig.TEN_WHEEL,
            fleet_type=Truck.FleetType.COAL,
            status=Truck.Status.ACTIVE,
            current_odometer=50000
        )
        
        # Create driver
        self.driver = Driver.objects.create(
            name='John Doe',
            license_number='DL12345678',
            phone='9876543210',
            status=Driver.Status.ON_DUTY,
            driver_type=Driver.DriverType.PERMANENT
        )


class AIInsightsDashboardViewTests(BaseAIViewTestCase):
    """Test cases for AIInsightsDashboardView."""
    
    def test_dashboard_view(self):
        """Test AI insights dashboard view."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(reverse('reporting:ai_insights'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'reporting/ai_insights_dashboard.html')
    
    def test_dashboard_requires_login(self):
        """Test that dashboard requires login."""
        response = self.client.get(reverse('reporting:ai_insights'))
        self.assertEqual(response.status_code, 302)


class FuelEfficiencyInsightsViewTests(BaseAIViewTestCase):
    """Test cases for FuelEfficiencyInsightsView."""
    
    def test_fuel_insights_view(self):
        """Test fuel efficiency insights view."""
        self.client.login(username='admin', password='adminpass123')
        
        with patch('reporting.views_ai.GeminiAIService') as mock_service_class:
            mock_service = MagicMock()
            mock_insight = FuelEfficiencyInsight(
                truck_id=self.truck.id,
                truck_plate=self.truck.plate_number,
                current_efficiency=3.5,
                fleet_average=3.2,
                performance_rating='GOOD',
                insights=['Test insight'],
                recommendations=['Test recommendation'],
                potential_savings={'fuel': 100},
                generated_at=timezone.now()
            )
            mock_service.generate_fuel_efficiency_insights.return_value = mock_insight
            mock_service_class.return_value = mock_service
            
            response = self.client.get(
                reverse('reporting:ai_fuel_insights', kwargs={'pk': self.truck.pk})
            )
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, 'reporting/fuel_efficiency_insights.html')
    
    def test_fuel_insights_api_view(self):
        """Test fuel efficiency insights API view."""
        self.client.login(username='admin', password='adminpass123')
        
        with patch('reporting.views_ai.GeminiAIService') as mock_service_class:
            mock_service = MagicMock()
            mock_insight = FuelEfficiencyInsight(
                truck_id=self.truck.id,
                truck_plate=self.truck.plate_number,
                current_efficiency=3.5,
                fleet_average=3.2,
                performance_rating='GOOD',
                insights=['Test insight'],
                recommendations=['Test recommendation'],
                potential_savings={'fuel': 100},
                generated_at=timezone.now()
            )
            mock_service.generate_fuel_efficiency_insights.return_value = mock_insight
            mock_service_class.return_value = mock_service
            
            response = self.client.get(
                reverse('reporting:ai_fuel_insights_api', kwargs={'pk': self.truck.pk})
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertTrue(data['success'])
            self.assertEqual(data['data']['truck_plate'], self.truck.plate_number)


class AnomalyDetectionViewTests(BaseAIViewTestCase):
    """Test cases for AnomalyDetectionView."""
    
    def test_anomaly_detection_view(self):
        """Test anomaly detection view."""
        self.client.login(username='admin', password='adminpass123')
        
        with patch('reporting.views_ai.GeminiAIService') as mock_service_class:
            mock_service = MagicMock()
            mock_anomaly = AnomalyDetectionResult(
                truck_id=self.truck.id,
                truck_plate=self.truck.plate_number,
                anomaly_type='FUEL_EFFICIENCY_DROP',
                severity='HIGH',
                description='Test anomaly',
                detected_value=2.5,
                expected_range={'min': 3.0, 'max': 5.0},
                recommended_action='Check fuel system',
                detected_at=timezone.now()
            )
            mock_service.detect_anomalies.return_value = [mock_anomaly]
            mock_service_class.return_value = mock_service
            
            response = self.client.get(
                reverse('reporting:ai_anomalies', kwargs={'pk': self.truck.pk})
            )
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, 'reporting/anomaly_detection.html')
    
    def test_anomaly_detection_api_view(self):
        """Test anomaly detection API view."""
        self.client.login(username='admin', password='adminpass123')
        
        with patch('reporting.views_ai.GeminiAIService') as mock_service_class:
            mock_service = MagicMock()
            mock_anomaly = AnomalyDetectionResult(
                truck_id=self.truck.id,
                truck_plate=self.truck.plate_number,
                anomaly_type='FUEL_EFFICIENCY_DROP',
                severity='HIGH',
                description='Test anomaly',
                detected_value=2.5,
                expected_range={'min': 3.0, 'max': 5.0},
                recommended_action='Check fuel system',
                detected_at=timezone.now()
            )
            mock_service.detect_anomalies.return_value = [mock_anomaly]
            mock_service_class.return_value = mock_service
            
            response = self.client.get(
                reverse('reporting:ai_anomalies_api', kwargs={'pk': self.truck.pk})
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertTrue(data['success'])
            self.assertEqual(data['count'], 1)


class MaintenanceRecommendationsViewTests(BaseAIViewTestCase):
    """Test cases for MaintenanceRecommendationsView."""
    
    def test_maintenance_recommendations_view(self):
        """Test maintenance recommendations view."""
        self.client.login(username='admin', password='adminpass123')
        
        with patch('reporting.views_ai.GeminiAIService') as mock_service_class:
            mock_service = MagicMock()
            mock_recommendation = MaintenanceRecommendation(
                truck_id=self.truck.id,
                truck_plate=self.truck.plate_number,
                priority='HIGH',
                maintenance_type='PREVENTIVE',
                description='Oil change',
                estimated_cost=2500.0,
                estimated_downtime='2-3 hours',
                recommended_date=timezone.now(),
                rationale='Due to mileage',
                generated_at=timezone.now()
            )
            mock_service.generate_maintenance_recommendations.return_value = [mock_recommendation]
            mock_service_class.return_value = mock_service
            
            response = self.client.get(
                reverse('reporting:ai_maintenance', kwargs={'pk': self.truck.pk})
            )
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, 'reporting/maintenance_recommendations.html')
    
    def test_maintenance_recommendations_api_view(self):
        """Test maintenance recommendations API view."""
        self.client.login(username='admin', password='adminpass123')
        
        with patch('reporting.views_ai.GeminiAIService') as mock_service_class:
            mock_service = MagicMock()
            mock_recommendation = MaintenanceRecommendation(
                truck_id=self.truck.id,
                truck_plate=self.truck.plate_number,
                priority='HIGH',
                maintenance_type='PREVENTIVE',
                description='Oil change',
                estimated_cost=2500.0,
                estimated_downtime='2-3 hours',
                recommended_date=timezone.now(),
                rationale='Due to mileage',
                generated_at=timezone.now()
            )
            mock_service.generate_maintenance_recommendations.return_value = [mock_recommendation]
            mock_service_class.return_value = mock_service
            
            response = self.client.get(
                reverse('reporting:ai_maintenance_api', kwargs={'pk': self.truck.pk})
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertTrue(data['success'])
            self.assertEqual(data['count'], 1)


class ChalanOCRViewTests(BaseAIViewTestCase):
    """Test cases for ChalanOCR views."""
    
    def setUp(self):
        super().setUp()
        self.mining_log = MiningLog.objects.create(
            type=MiningLog.LogType.DISPATCH,
            date=date.today(),
            time=__import__('datetime').time(10, 30),
            chalan_no='CHALAN123456',
            customer_name='Test Customer',
            truck=self.truck,
            net=Decimal('35000.00'),
            material='Iron Ore',
            mining_type=MiningLog.MiningType.INTERNAL,
            created_by=self.admin_user
        )
    
    def test_chalan_ocr_list_view(self):
        """Test chalan OCR list view."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(reverse('reporting:ocr_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'reporting/chalan_ocr_list.html')
    
    def test_chalan_ocr_detail_view(self):
        """Test chalan OCR detail view."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(
            reverse('reporting:ocr_detail', kwargs={'pk': self.mining_log.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'reporting/chalan_ocr.html')
    
    def test_chalan_ocr_process_view(self):
        """Test chalan OCR process view."""
        self.client.login(username='admin', password='adminpass123')
        
        with patch('reporting.views_ai.GeminiAIService') as mock_service_class:
            mock_service = MagicMock()
            mock_result = OCRResult(
                success=True,
                chalan_no='CHALAN123456',
                date='2024-01-15',
                customer_name='Test Customer',
                net_weight=35.5,
                material='Iron Ore',
                confidence_score=0.85,
                raw_text='Raw OCR text',
                processed_at=timezone.now(),
                errors=[]
            )
            mock_service.process_chalan_ocr.return_value = mock_result
            mock_service_class.return_value = mock_service
            
            # Mock the file path
            with patch.object(self.mining_log.chalan_document, 'path', '/tmp/test.jpg'):
                with patch('os.path.exists', return_value=True):
                    response = self.client.post(
                        reverse('reporting:ocr_process', kwargs={'pk': self.mining_log.pk})
                    )
                    self.assertEqual(response.status_code, 200)
                    data = response.json()
                    self.assertTrue(data['success'])
    
    def test_bulk_ocr_process_view(self):
        """Test bulk OCR process view."""
        self.client.login(username='admin', password='adminpass123')
        
        with patch('reporting.views_ai.GeminiAIService') as mock_service_class:
            mock_service = MagicMock()
            mock_result = OCRResult(
                success=True,
                chalan_no='CHALAN123456',
                date='2024-01-15',
                customer_name='Test Customer',
                net_weight=35.5,
                material='Iron Ore',
                confidence_score=0.85,
                raw_text='Raw OCR text',
                processed_at=timezone.now(),
                errors=[]
            )
            mock_service.process_chalan_ocr.return_value = mock_result
            mock_service_class.return_value = mock_service
            
            response = self.client.post(
                reverse('reporting:ocr_bulk_process'),
                {'log_ids[]': [self.mining_log.pk]}
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertTrue(data['success'])


class FleetAIReportViewTests(BaseAIViewTestCase):
    """Test cases for FleetAIReport views."""
    
    def test_fleet_ai_report_view(self):
        """Test fleet AI report view."""
        self.client.login(username='admin', password='adminpass123')
        
        with patch('reporting.views_ai.GeminiAIService') as mock_service_class:
            mock_service = MagicMock()
            mock_report = {
                'executive_summary': 'Fleet is performing well',
                'key_findings': ['Finding 1'],
                'performance_analysis': {
                    'overall_rating': 'GOOD',
                    'top_performers': ['MH12AB1234'],
                    'underperformers': []
                },
                'recommendations': [],
                'cost_optimization': {}
            }
            mock_service.generate_fleet_insights_report.return_value = mock_report
            mock_service_class.return_value = mock_service
            
            response = self.client.get(reverse('reporting:ai_fleet_report'))
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, 'reporting/fleet_ai_report.html')
    
    def test_fleet_ai_report_api_view(self):
        """Test fleet AI report API view."""
        self.client.login(username='admin', password='adminpass123')
        
        with patch('reporting.views_ai.GeminiAIService') as mock_service_class:
            mock_service = MagicMock()
            mock_report = {
                'executive_summary': 'Fleet is performing well',
                'key_findings': ['Finding 1'],
                'performance_analysis': {
                    'overall_rating': 'GOOD',
                    'top_performers': ['MH12AB1234'],
                    'underperformers': []
                },
                'recommendations': [],
                'cost_optimization': {}
            }
            mock_service.generate_fleet_insights_report.return_value = mock_report
            mock_service_class.return_value = mock_service
            
            response = self.client.get(reverse('reporting:ai_fleet_report_api'))
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertTrue(data['success'])
            self.assertEqual(data['data']['executive_summary'], 'Fleet is performing well')


class AIInsightsTruckListViewTests(BaseAIViewTestCase):
    """Test cases for AIInsightsTruckListView."""
    
    def test_truck_list_view(self):
        """Test truck list view for AI insights."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(reverse('reporting:ai_insights_trucks'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'reporting/ai_insights_truck_list.html')
    
    def test_truck_list_with_fleet_type_filter(self):
        """Test truck list with fleet type filter."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(
            reverse('reporting:ai_insights_trucks'),
            {'fleet_type': Truck.FleetType.COAL}
        )
        self.assertEqual(response.status_code, 200)


class CreateAIAlertViewTests(BaseAIViewTestCase):
    """Test cases for CreateAIAlertView."""
    
    def test_create_ai_alert(self):
        """Test creating an AI alert."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.post(
            reverse('reporting:ai_alert_create'),
            {
                'truck_id': self.truck.pk,
                'alert_type': 'FUEL_EFFICIENCY',
                'title': 'Test AI Alert',
                'description': 'Test alert description',
                'alert_level': 'WARNING'
            }
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('alert_id', data)


class RegenerateInsightsViewTests(BaseAIViewTestCase):
    """Test cases for RegenerateInsightsView."""
    
    def test_regenerate_insights(self):
        """Test regenerating AI insights."""
        self.client.login(username='admin', password='adminpass123')
        
        with patch('reporting.views_ai.GeminiAIService') as mock_service_class:
            mock_service = MagicMock()
            mock_insight = FuelEfficiencyInsight(
                truck_id=self.truck.id,
                truck_plate=self.truck.plate_number,
                current_efficiency=3.5,
                fleet_average=3.2,
                performance_rating='GOOD',
                insights=[],
                recommendations=[],
                potential_savings={},
                generated_at=timezone.now()
            )
            mock_anomaly = AnomalyDetectionResult(
                truck_id=self.truck.id,
                truck_plate=self.truck.plate_number,
                anomaly_type='TEST',
                severity='LOW',
                description='Test',
                detected_value=1.0,
                expected_range={'min': 0, 'max': 2},
                recommended_action='Test',
                detected_at=timezone.now()
            )
            mock_recommendation = MaintenanceRecommendation(
                truck_id=self.truck.id,
                truck_plate=self.truck.plate_number,
                priority='LOW',
                maintenance_type='PREVENTIVE',
                description='Test',
                estimated_cost=0.0,
                estimated_downtime='0',
                recommended_date=timezone.now(),
                rationale='Test',
                generated_at=timezone.now()
            )
            
            mock_service.generate_fuel_efficiency_insights.return_value = mock_insight
            mock_service.detect_anomalies.return_value = [mock_anomaly]
            mock_service.generate_maintenance_recommendations.return_value = [mock_recommendation]
            mock_service_class.return_value = mock_service
            
            response = self.client.post(
                reverse('reporting:ai_regenerate_insights', kwargs={'pk': self.truck.pk}),
                {'days': 30}
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertTrue(data['success'])
            self.assertEqual(data['anomalies_detected'], 1)
            self.assertEqual(data['recommendations_generated'], 1)


class AIViewErrorHandlingTests(BaseAIViewTestCase):
    """Test cases for error handling in AI views."""
    
    def test_fuel_insights_api_truck_not_found(self):
        """Test fuel insights API with non-existent truck."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(
            reverse('reporting:ai_fuel_insights_api', kwargs={'pk': 99999})
        )
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertFalse(data['success'])
    
    def test_anomaly_detection_api_truck_not_found(self):
        """Test anomaly detection API with non-existent truck."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(
            reverse('reporting:ai_anomalies_api', kwargs={'pk': 99999})
        )
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertFalse(data['success'])
    
    def test_maintenance_api_truck_not_found(self):
        """Test maintenance API with non-existent truck."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(
            reverse('reporting:ai_maintenance_api', kwargs={'pk': 99999})
        )
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertFalse(data['success'])
