"""
AI-powered views for SAPNA CARTING Fleet Management System.

This module provides views for:
- Fuel efficiency insights
- Anomaly detection
- Maintenance recommendations
- OCR processing for mining chalans
"""

import json
from datetime import datetime, timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView, DetailView, ListView
from django.contrib import messages
from django.core.files.storage import default_storage

from fleet.models import Truck, Alert
from operations.models import MiningLog
from fleet.utils.permissions import AdminRequiredMixin

from .utils.gemini_ai import (
    GeminiAIService,
    GeminiAIError,
    get_fuel_efficiency_insights,
    detect_truck_anomalies,
    get_maintenance_recommendations,
    process_mining_chalan,
    get_fleet_ai_report
)


class AIInsightsDashboardView(LoginRequiredMixin, TemplateView):
    """Dashboard for AI-powered insights."""
    template_name = 'reporting/ai_insights_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get fleet overview
        active_trucks = Truck.objects.filter(status='ACTIVE')
        context['total_trucks'] = active_trucks.count()
        
        # Recent AI-generated alerts
        context['recent_alerts'] = Alert.objects.filter(
            alert_type__in=['FUEL_EFFICIENCY', 'TIRE_COST']
        ).order_by('-created_at')[:5]
        
        # Trucks with pending insights
        context['trucks_with_insights'] = active_trucks[:10]
        
        # OCR processing stats
        context['pending_ocr'] = MiningLog.objects.filter(
            ocr_processed=False,
            chalan_document__isnull=False
        ).count()
        context['processed_ocr'] = MiningLog.objects.filter(
            ocr_processed=True
        ).count()
        
        context['breadcrumbs'] = [
            {'name': 'Reports', 'url': reverse('reporting:dashboard')},
            {'name': 'AI Insights', 'url': None}
        ]
        
        return context


class FuelEfficiencyInsightsView(LoginRequiredMixin, DetailView):
    """View for AI-powered fuel efficiency insights for a specific truck."""
    model = Truck
    template_name = 'reporting/fuel_efficiency_insights.html'
    context_object_name = 'truck'
    pk_url_kwarg = 'pk'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        truck = self.object
        days = int(self.request.GET.get('days', 30))
        
        try:
            service = GeminiAIService()
            insights = service.generate_fuel_efficiency_insights(truck, days)
            
            context['insights'] = insights
            context['days'] = days
            context['days_options'] = [7, 14, 30, 60, 90]
            
        except GeminiAIError as e:
            context['error'] = str(e)
            context['insights'] = None
        
        context['breadcrumbs'] = [
            {'name': 'Reports', 'url': reverse('reporting:dashboard')},
            {'name': 'AI Insights', 'url': reverse('reporting:ai_insights')},
            {'name': f'{truck.plate_number} - Fuel Efficiency', 'url': None}
        ]
        
        return context


class FuelEfficiencyInsightsAPIView(LoginRequiredMixin, View):
    """API view for fuel efficiency insights."""
    
    def get(self, request, pk):
        try:
            truck = Truck.objects.get(pk=pk)
            days = int(request.GET.get('days', 30))
            
            service = GeminiAIService()
            insights = service.generate_fuel_efficiency_insights(truck, days)
            
            return JsonResponse({
                'success': True,
                'data': {
                    'truck_id': insights.truck_id,
                    'truck_plate': insights.truck_plate,
                    'current_efficiency': insights.current_efficiency,
                    'fleet_average': insights.fleet_average,
                    'performance_rating': insights.performance_rating,
                    'insights': insights.insights,
                    'recommendations': insights.recommendations,
                    'potential_savings': insights.potential_savings,
                    'generated_at': insights.generated_at.isoformat()
                }
            })
        except Truck.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Truck not found'}, status=404)
        except GeminiAIError as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)


class AnomalyDetectionView(LoginRequiredMixin, DetailView):
    """View for AI-powered anomaly detection for a specific truck."""
    model = Truck
    template_name = 'reporting/anomaly_detection.html'
    context_object_name = 'truck'
    pk_url_kwarg = 'pk'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        truck = self.object
        days = int(self.request.GET.get('days', 30))
        
        try:
            service = GeminiAIService()
            anomalies = service.detect_anomalies(truck, days)
            
            context['anomalies'] = anomalies
            context['days'] = days
            context['days_options'] = [7, 14, 30, 60, 90]
            context['anomaly_count'] = len(anomalies)
            context['critical_count'] = sum(1 for a in anomalies if a.severity == 'CRITICAL')
            
        except GeminiAIError as e:
            context['error'] = str(e)
            context['anomalies'] = []
        
        context['breadcrumbs'] = [
            {'name': 'Reports', 'url': reverse('reporting:dashboard')},
            {'name': 'AI Insights', 'url': reverse('reporting:ai_insights')},
            {'name': f'{truck.plate_number} - Anomaly Detection', 'url': None}
        ]
        
        return context


class AnomalyDetectionAPIView(LoginRequiredMixin, View):
    """API view for anomaly detection."""
    
    def get(self, request, pk):
        try:
            truck = Truck.objects.get(pk=pk)
            days = int(request.GET.get('days', 30))
            
            service = GeminiAIService()
            anomalies = service.detect_anomalies(truck, days)
            
            return JsonResponse({
                'success': True,
                'data': [
                    {
                        'truck_id': a.truck_id,
                        'truck_plate': a.truck_plate,
                        'anomaly_type': a.anomaly_type,
                        'severity': a.severity,
                        'description': a.description,
                        'detected_value': a.detected_value,
                        'expected_range': a.expected_range,
                        'recommended_action': a.recommended_action,
                        'detected_at': a.detected_at.isoformat()
                    }
                    for a in anomalies
                ],
                'count': len(anomalies)
            })
        except Truck.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Truck not found'}, status=404)
        except GeminiAIError as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)


class MaintenanceRecommendationsView(LoginRequiredMixin, DetailView):
    """View for AI-powered maintenance recommendations for a specific truck."""
    model = Truck
    template_name = 'reporting/maintenance_recommendations.html'
    context_object_name = 'truck'
    pk_url_kwarg = 'pk'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        truck = self.object
        
        try:
            service = GeminiAIService()
            recommendations = service.generate_maintenance_recommendations(truck)
            
            # Sort by priority
            priority_order = {'CRITICAL': 1, 'HIGH': 2, 'MEDIUM': 3, 'LOW': 4}
            recommendations.sort(key=lambda x: priority_order.get(x.priority, 5))
            
            context['recommendations'] = recommendations
            context['critical_count'] = sum(1 for r in recommendations if r.priority == 'CRITICAL')
            context['high_count'] = sum(1 for r in recommendations if r.priority == 'HIGH')
            context['total_estimated_cost'] = sum(r.estimated_cost for r in recommendations)
            
        except GeminiAIError as e:
            context['error'] = str(e)
            context['recommendations'] = []
        
        context['breadcrumbs'] = [
            {'name': 'Reports', 'url': reverse('reporting:dashboard')},
            {'name': 'AI Insights', 'url': reverse('reporting:ai_insights')},
            {'name': f'{truck.plate_number} - Maintenance', 'url': None}
        ]
        
        return context


class MaintenanceRecommendationsAPIView(LoginRequiredMixin, View):
    """API view for maintenance recommendations."""
    
    def get(self, request, pk):
        try:
            truck = Truck.objects.get(pk=pk)
            
            service = GeminiAIService()
            recommendations = service.generate_maintenance_recommendations(truck)
            
            return JsonResponse({
                'success': True,
                'data': [
                    {
                        'truck_id': r.truck_id,
                        'truck_plate': r.truck_plate,
                        'priority': r.priority,
                        'maintenance_type': r.maintenance_type,
                        'description': r.description,
                        'estimated_cost': r.estimated_cost,
                        'estimated_downtime': r.estimated_downtime,
                        'recommended_date': r.recommended_date.isoformat(),
                        'rationale': r.rationale,
                        'generated_at': r.generated_at.isoformat()
                    }
                    for r in recommendations
                ],
                'count': len(recommendations)
            })
        except Truck.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Truck not found'}, status=404)
        except GeminiAIError as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)


class ChalanOCRView(LoginRequiredMixin, DetailView):
    """View for processing mining chalan with OCR."""
    model = MiningLog
    template_name = 'reporting/chalan_ocr.html'
    context_object_name = 'mining_log'
    pk_url_kwarg = 'pk'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        mining_log = self.object
        
        context['has_document'] = bool(mining_log.chalan_document)
        context['ocr_processed'] = mining_log.ocr_processed
        context['ocr_data'] = mining_log.ocr_data
        
        context['breadcrumbs'] = [
            {'name': 'Operations', 'url': None},
            {'name': 'Mining Logs', 'url': reverse('operations:mining-log-list')},
            {'name': f'Chalan {mining_log.chalan_no}', 'url': reverse('operations:mining-log-detail', kwargs={'pk': mining_log.pk})},
            {'name': 'OCR Processing', 'url': None}
        ]
        
        return context


class ChalanOCRProcessView(LoginRequiredMixin, View):
    """View to process chalan OCR."""
    
    def post(self, request, pk):
        try:
            mining_log = MiningLog.objects.get(pk=pk)
            
            if not mining_log.chalan_document:
                return JsonResponse({
                    'success': False,
                    'error': 'No document attached to this mining log'
                }, status=400)
            
            # Get the file path
            file_path = mining_log.chalan_document.path
            
            # Process OCR
            service = GeminiAIService()
            result = service.process_chalan_ocr(file_path, mining_log)
            
            if result.success:
                messages.success(request, 'OCR processing completed successfully!')
            else:
                messages.warning(request, f'OCR processing completed with warnings: {", ".join(result.errors)}')
            
            return JsonResponse({
                'success': result.success,
                'data': {
                    'chalan_no': result.chalan_no,
                    'date': result.date,
                    'customer_name': result.customer_name,
                    'net_weight': result.net_weight,
                    'material': result.material,
                    'confidence_score': result.confidence_score,
                    'raw_text': result.raw_text,
                    'errors': result.errors
                }
            })
            
        except MiningLog.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Mining log not found'}, status=404)
        except GeminiAIError as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)


class ChalanOCRListView(LoginRequiredMixin, ListView):
    """List view for mining logs pending OCR processing."""
    model = MiningLog
    template_name = 'reporting/chalan_ocr_list.html'
    context_object_name = 'mining_logs'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = MiningLog.objects.all().select_related('truck')
        
        # Filter by OCR status
        status = self.request.GET.get('status', 'pending')
        if status == 'pending':
            queryset = queryset.filter(ocr_processed=False, chalan_document__isnull=False)
        elif status == 'processed':
            queryset = queryset.filter(ocr_processed=True)
        elif status == 'no_document':
            queryset = queryset.filter(chalan_document__isnull=True)
        
        return queryset.order_by('-date', '-time')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context['pending_count'] = MiningLog.objects.filter(
            ocr_processed=False, chalan_document__isnull=False
        ).count()
        context['processed_count'] = MiningLog.objects.filter(ocr_processed=True).count()
        context['no_document_count'] = MiningLog.objects.filter(chalan_document__isnull=True).count()
        
        context['current_status'] = self.request.GET.get('status', 'pending')
        
        context['breadcrumbs'] = [
            {'name': 'Reports', 'url': reverse('reporting:dashboard')},
            {'name': 'OCR Processing', 'url': None}
        ]
        
        return context


class BulkOCRProcessView(AdminRequiredMixin, View):
    """View to process OCR for multiple mining logs."""
    
    def post(self, request):
        log_ids = request.POST.getlist('log_ids[]')
        processed_count = 0
        error_count = 0
        
        service = GeminiAIService()
        
        for log_id in log_ids:
            try:
                mining_log = MiningLog.objects.get(pk=log_id)
                if mining_log.chalan_document and not mining_log.ocr_processed:
                    file_path = mining_log.chalan_document.path
                    result = service.process_chalan_ocr(file_path, mining_log)
                    if result.success:
                        processed_count += 1
                    else:
                        error_count += 1
            except Exception:
                error_count += 1
        
        messages.success(
            request,
            f'Processed {processed_count} documents. {error_count} errors.'
        )
        
        return JsonResponse({
            'success': True,
            'processed': processed_count,
            'errors': error_count
        })


class FleetAIReportView(LoginRequiredMixin, TemplateView):
    """View for comprehensive AI-powered fleet report."""
    template_name = 'reporting/fleet_ai_report.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        days = int(self.request.GET.get('days', 30))
        
        try:
            service = GeminiAIService()
            report = service.generate_fleet_insights_report(days)
            
            context['report'] = report
            context['days'] = days
            context['days_options'] = [7, 14, 30, 60, 90]
            context['generated_at'] = timezone.now()
            
        except GeminiAIError as e:
            context['error'] = str(e)
            context['report'] = None
        
        context['breadcrumbs'] = [
            {'name': 'Reports', 'url': reverse('reporting:dashboard')},
            {'name': 'AI Fleet Report', 'url': None}
        ]
        
        return context


class FleetAIReportAPIView(LoginRequiredMixin, View):
    """API view for fleet AI report."""
    
    def get(self, request):
        try:
            days = int(request.GET.get('days', 30))
            
            service = GeminiAIService()
            report = service.generate_fleet_insights_report(days)
            
            return JsonResponse({
                'success': True,
                'data': report,
                'generated_at': timezone.now().isoformat()
            })
        except GeminiAIError as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)


class AIInsightsTruckListView(LoginRequiredMixin, ListView):
    """List view for trucks with AI insights."""
    model = Truck
    template_name = 'reporting/ai_insights_truck_list.html'
    context_object_name = 'trucks'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Truck.objects.filter(status='ACTIVE').order_by('plate_number')
        
        # Apply fleet type filter
        fleet_type = self.request.GET.get('fleet_type')
        if fleet_type:
            queryset = queryset.filter(fleet_type=fleet_type)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context['fleet_types'] = Truck.FleetType.choices
        context['current_fleet_type'] = self.request.GET.get('fleet_type', '')
        
        # Get recent insights count
        thirty_days_ago = timezone.now() - timedelta(days=30)
        context['recent_insights_count'] = Alert.objects.filter(
            alert_type__in=['FUEL_EFFICIENCY', 'TIRE_COST'],
            created_at__gte=thirty_days_ago
        ).count()
        
        context['breadcrumbs'] = [
            {'name': 'Reports', 'url': reverse('reporting:dashboard')},
            {'name': 'AI Insights', 'url': None}
        ]
        
        return context


class CreateAIAlertView(AdminRequiredMixin, View):
    """View to create an AI-generated alert."""
    
    def post(self, request):
        try:
            truck_id = request.POST.get('truck_id')
            alert_type = request.POST.get('alert_type')
            title = request.POST.get('title')
            description = request.POST.get('description')
            alert_level = request.POST.get('alert_level', 'WARNING')
            
            truck = Truck.objects.get(pk=truck_id)
            
            alert = Alert.objects.create(
                title=title,
                alert_type=alert_type,
                alert_level=alert_level,
                description=description,
                truck=truck,
                metadata={'source': 'AI_GENERATED', 'created_by': request.user.username}
            )
            
            messages.success(request, 'AI alert created successfully!')
            
            return JsonResponse({
                'success': True,
                'alert_id': alert.id
            })
            
        except Truck.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Truck not found'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)


class RegenerateInsightsView(AdminRequiredMixin, View):
    """View to regenerate AI insights for a truck."""
    
    def post(self, request, pk):
        try:
            truck = Truck.objects.get(pk=pk)
            days = int(request.POST.get('days', 30))
            
            # This will trigger regeneration of insights
            service = GeminiAIService()
            
            # Generate fuel efficiency insights
            fuel_insights = service.generate_fuel_efficiency_insights(truck, days)
            
            # Detect anomalies
            anomalies = service.detect_anomalies(truck, days)
            
            # Generate maintenance recommendations
            recommendations = service.generate_maintenance_recommendations(truck)
            
            messages.success(
                request,
                f'AI insights regenerated for {truck.plate_number}. '
                f'Found {len(anomalies)} anomalies and {len(recommendations)} recommendations.'
            )
            
            return JsonResponse({
                'success': True,
                'fuel_insights_generated': True,
                'anomalies_detected': len(anomalies),
                'recommendations_generated': len(recommendations)
            })
            
        except Truck.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Truck not found'}, status=404)
        except GeminiAIError as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
