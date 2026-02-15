"""
Views for reporting and analytics system.
"""

from datetime import datetime, timedelta
from decimal import Decimal

from django.shortcuts import render, get_object_or_404
from django.views import View
from django.views.generic import TemplateView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.db.models import Sum, Count, Q
from django.template.loader import render_to_string

from fleet.models import Truck, Driver, FuelLog, TireInventory, DailyOdoRegistry, Alert
from operations.models import CoalLog, MiningLog

from .forms import (
    ReportFilterForm, FuelConsumptionFilterForm, TireCostFilterForm,
    DriverPerformanceFilterForm, FleetStatusFilterForm,
    CostAnalysisFilterForm, EfficiencyFilterForm
)
from .utils.analytics import (
    calculate_cost_per_km, calculate_fuel_efficiency, 
    calculate_driver_performance_score, get_fleet_average_efficiency,
    get_all_trucks_cost_per_km, get_all_trucks_efficiency,
    get_driver_rankings, get_monthly_fuel_trend,
    get_operations_summary, get_fleet_status_summary
)
from .utils.predictive_maintenance import PredictiveMaintenanceEngine, get_maintenance_summary
from .utils.pdf_generator import (
    FuelConsumptionPDF, TireCostPDF, OperationsPDF,
    FleetStatusPDF, DriverPerformancePDF, CostPerKmPDF,
    FleetEfficiencyPDF, PredictiveMaintenancePDF
)
from .utils.csv_exporter import (
    export_fuel_consumption, export_tire_costs, export_operations,
    export_fleet_status, export_driver_performance, export_cost_per_km,
    export_fleet_efficiency, export_predictive_maintenance
)


class ReportDashboardView(LoginRequiredMixin, TemplateView):
    """Main dashboard view for reports and analytics."""
    template_name = 'reporting/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['breadcrumbs'] = [
            {'name': 'Dashboard', 'url': '/dashboard/'},
            {'name': 'Reports & Analytics', 'url': None}
        ]
        return context


class AnalyticsDashboardView(LoginRequiredMixin, TemplateView):
    """Advanced analytics dashboard with interactive charts."""
    template_name = 'reporting/analytics_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get date range from request
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        
        # Convert to datetime if provided
        start_date = datetime.strptime(date_from, '%Y-%m-%d') if date_from else None
        end_date = datetime.strptime(date_to, '%Y-%m-%d') if date_to else None
        
        # Get fleet summary
        fleet_summary = get_fleet_status_summary()
        context['fleet_summary'] = fleet_summary
        
        # Get fuel trend data for charts
        fuel_trend = get_monthly_fuel_trend(start_date, end_date)
        context['fuel_trend'] = fuel_trend
        
        # Get efficiency data
        efficiency_data = get_all_trucks_efficiency(start_date, end_date)
        context['efficiency_data'] = efficiency_data
        
        # Get cost per km data
        cost_data = get_all_trucks_cost_per_km(start_date, end_date)
        context['cost_data'] = cost_data
        
        # Get maintenance alerts
        maintenance = get_maintenance_summary()
        context['maintenance'] = maintenance
        
        # KPI Cards
        avg_efficiency = get_fleet_average_efficiency(start_date, end_date)
        avg_cost = sum(c['cost_per_km'] for c in cost_data) / len(cost_data) if cost_data else 0
        
        context['kpis'] = {
            'avg_efficiency': float(avg_efficiency),
            'avg_cost_per_km': float(avg_cost),
            'total_trucks': fleet_summary['total_trucks'],
            'active_trucks': fleet_summary['active_trucks'],
            'total_alerts': maintenance['total_alerts'],
            'critical_alerts': maintenance['priority_counts'].get('CRITICAL', 0)
        }
        
        context['breadcrumbs'] = [
            {'name': 'Dashboard', 'url': '/dashboard/'},
            {'name': 'Analytics Dashboard', 'url': None}
        ]
        
        return context


# ==================== FUEL CONSUMPTION REPORT ====================

class FuelConsumptionReportView(LoginRequiredMixin, TemplateView):
    template_name = 'reporting/fuel_consumption_report.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        form = FuelConsumptionFilterForm(self.request.GET)
        
        # Start with all fuel logs
        fuel_logs = FuelLog.objects.select_related('truck', 'driver').order_by('-date')
        
        if form.is_valid():
            fuel_logs = form.get_filtered_queryset(fuel_logs)
        
        context['fuel_logs'] = fuel_logs[:100]  # Limit for display
        context['form'] = form
        
        # Summary stats
        context['total_liters'] = fuel_logs.aggregate(Sum('fuel_liters'))['fuel_liters__sum'] or 0
        context['total_cost'] = fuel_logs.aggregate(Sum('fuel_cost'))['fuel_cost__sum'] or 0
        context['total_trips'] = fuel_logs.count()
        
        context['breadcrumbs'] = [
            {'name': 'Dashboard', 'url': '/dashboard/'},
            {'name': 'Fuel Consumption Report', 'url': None}
        ]
        
        return context


class FuelConsumptionCSVExportView(LoginRequiredMixin, View):
    def get(self, request):
        fuel_logs = FuelLog.objects.select_related('truck', 'driver').order_by('-date')
        
        form = FuelConsumptionFilterForm(request.GET)
        if form.is_valid():
            fuel_logs = form.get_filtered_queryset(fuel_logs)
        
        date_from = request.GET.get('date_from', '')
        date_to = request.GET.get('date_to', '')
        
        return export_fuel_consumption(fuel_logs, date_from, date_to)


class FuelConsumptionPDFExportView(LoginRequiredMixin, View):
    def get(self, request):
        fuel_logs = FuelLog.objects.select_related('truck', 'driver').order_by('-date')
        
        form = FuelConsumptionFilterForm(request.GET)
        if form.is_valid():
            fuel_logs = form.get_filtered_queryset(fuel_logs)
        
        pdf_gen = FuelConsumptionPDF()
        date_from = request.GET.get('date_from', '')
        date_to = request.GET.get('date_to', '')
        user = request.user.username
        
        pdf_content = pdf_gen.generate(fuel_logs, date_from, date_to, user)
        
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="fuel_consumption_report.pdf"'
        
        return response


# ==================== TIRE COST REPORT ====================

class TireCostReportView(LoginRequiredMixin, TemplateView):
    template_name = 'reporting/tire_cost_report.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        form = TireCostFilterForm(self.request.GET)
        
        tires = TireInventory.objects.select_related('truck').order_by('-created_at')
        
        if form.is_valid():
            tires = form.get_filtered_queryset(tires)
        
        context['tires'] = tires[:100]
        context['form'] = form
        
        # Summary stats
        total_cost = sum(t.calculate_total_cost() for t in tires)
        context['total_investment'] = total_cost
        context['total_tires'] = tires.count()
        
        context['breadcrumbs'] = [
            {'name': 'Dashboard', 'url': '/dashboard/'},
            {'name': 'Tire Cost Report', 'url': None}
        ]
        
        return context


class TireCostCSVExportView(LoginRequiredMixin, View):
    def get(self, request):
        tires = TireInventory.objects.select_related('truck').order_by('-created_at')
        
        form = TireCostFilterForm(request.GET)
        if form.is_valid():
            tires = form.get_filtered_queryset(tires)
        
        return export_tire_costs(tires)


class TireCostPDFExportView(LoginRequiredMixin, View):
    def get(self, request):
        tires = TireInventory.objects.select_related('truck').order_by('-created_at')
        
        form = TireCostFilterForm(request.GET)
        if form.is_valid():
            tires = form.get_filtered_queryset(tires)
        
        pdf_gen = TireCostPDF()
        pdf_content = pdf_gen.generate(tires, request.user.username)
        
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="tire_cost_report.pdf"'
        
        return response


# ==================== OPERATIONS REPORT ====================

class OperationsSummaryReportView(LoginRequiredMixin, TemplateView):
    template_name = 'reporting/operations_summary_report.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        
        # Get coal logs
        coal_logs = CoalLog.objects.select_related('truck').order_by('-date')
        if date_from:
            coal_logs = coal_logs.filter(date__gte=date_from)
        if date_to:
            coal_logs = coal_logs.filter(date__lte=date_to)
        
        # Get mining logs
        mining_logs = MiningLog.objects.select_related('truck').order_by('-date')
        if date_from:
            mining_logs = mining_logs.filter(date__gte=date_from)
        if date_to:
            mining_logs = mining_logs.filter(date__lte=date_to)
        
        context['coal_logs'] = coal_logs[:50]
        context['mining_logs'] = mining_logs[:50]
        
        # Summary
        summary = get_operations_summary(date_from, date_to)
        context['summary'] = summary
        
        context['breadcrumbs'] = [
            {'name': 'Dashboard', 'url': '/dashboard/'},
            {'name': 'Operations Summary', 'url': None}
        ]
        
        return context


class OperationsCSVExportView(LoginRequiredMixin, View):
    def get(self, request):
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        
        coal_logs = CoalLog.objects.select_related('truck').order_by('-date')
        mining_logs = MiningLog.objects.select_related('truck').order_by('-date')
        
        if date_from:
            coal_logs = coal_logs.filter(date__gte=date_from)
            mining_logs = mining_logs.filter(date__gte=date_from)
        if date_to:
            coal_logs = coal_logs.filter(date__lte=date_to)
            mining_logs = mining_logs.filter(date__lte=date_to)
        
        return export_operations(coal_logs, mining_logs, date_from, date_to)


class OperationsPDFExportView(LoginRequiredMixin, View):
    def get(self, request):
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        
        coal_logs = CoalLog.objects.select_related('truck').order_by('-date')
        mining_logs = MiningLog.objects.select_related('truck').order_by('-date')
        
        if date_from:
            coal_logs = coal_logs.filter(date__gte=date_from)
            mining_logs = mining_logs.filter(date__gte=date_from)
        if date_to:
            coal_logs = coal_logs.filter(date__lte=date_to)
            mining_logs = mining_logs.filter(date__lte=date_to)
        
        pdf_gen = OperationsPDF()
        pdf_content = pdf_gen.generate(coal_logs, mining_logs, date_from, date_to, request.user.username)
        
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="operations_report.pdf"'
        
        return response


# ==================== FLEET STATUS REPORT ====================

class FleetStatusReportView(LoginRequiredMixin, TemplateView):
    template_name = 'reporting/fleet_status_report.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        form = FleetStatusFilterForm(self.request.GET)
        
        trucks = Truck.objects.all().order_by('plate_number')
        
        if form.is_valid():
            trucks = form.get_filtered_queryset(trucks)
        
        context['trucks'] = trucks
        context['form'] = form
        
        # Summary
        summary = get_fleet_status_summary()
        context['summary'] = summary
        context['expiring_docs'] = summary['expiring_documents'][:20]
        
        context['breadcrumbs'] = [
            {'name': 'Dashboard', 'url': '/dashboard/'},
            {'name': 'Fleet Status', 'url': None}
        ]
        
        return context


class FleetStatusCSVExportView(LoginRequiredMixin, View):
    def get(self, request):
        trucks = Truck.objects.all().order_by('plate_number')
        
        form = FleetStatusFilterForm(request.GET)
        if form.is_valid():
            trucks = form.get_filtered_queryset(trucks)
        
        return export_fleet_status(trucks)


class FleetStatusPDFExportView(LoginRequiredMixin, View):
    def get(self, request):
        trucks = Truck.objects.all().order_by('plate_number')
        
        form = FleetStatusFilterForm(request.GET)
        if form.is_valid():
            trucks = form.get_filtered_queryset(trucks)
        
        pdf_gen = FleetStatusPDF()
        pdf_content = pdf_gen.generate(trucks, request.user.username)
        
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="fleet_status_report.pdf"'
        
        return response


# ==================== DRIVER PERFORMANCE REPORT ====================

class DriverPerformanceReportView(LoginRequiredMixin, TemplateView):
    template_name = 'reporting/driver_performance_report.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        form = DriverPerformanceFilterForm(self.request.GET)
        
        drivers = Driver.objects.all().order_by('name')
        
        # Get fuel logs for calculations
        fuel_logs = FuelLog.objects.select_related('truck', 'driver')
        
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        
        if date_from:
            fuel_logs = fuel_logs.filter(date__gte=date_from)
        if date_to:
            fuel_logs = fuel_logs.filter(date__lte=date_to)
        
        # Calculate performance for each driver
        driver_performance = []
        for driver in drivers:
            perf = calculate_driver_performance_score(driver, 
                datetime.strptime(date_from, '%Y-%m-%d') if date_from else None,
                datetime.strptime(date_to, '%Y-%m-%d') if date_to else None
            )
            if perf['total_trips'] > 0:
                driver_performance.append(perf)
        
        # Sort by total score
        driver_performance.sort(key=lambda x: x['total_score'], reverse=True)
        
        context['driver_performance'] = driver_performance[:50]
        context['form'] = form
        
        # Summary
        context['total_drivers'] = len(driver_performance)
        if driver_performance:
            avg_score = sum(d['total_score'] for d in driver_performance) / len(driver_performance)
            context['avg_performance_score'] = avg_score
        
        context['breadcrumbs'] = [
            {'name': 'Dashboard', 'url': '/dashboard/'},
            {'name': 'Driver Performance', 'url': None}
        ]
        
        return context


class DriverPerformanceCSVExportView(LoginRequiredMixin, View):
    def get(self, request):
        drivers = Driver.objects.all().order_by('name')
        
        fuel_logs = FuelLog.objects.select_related('truck', 'driver')
        
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        
        if date_from:
            fuel_logs = fuel_logs.filter(date__gte=date_from)
        if date_to:
            fuel_logs = fuel_logs.filter(date__lte=date_to)
        
        return export_driver_performance(drivers, fuel_logs, date_from, date_to)


class DriverPerformancePDFExportView(LoginRequiredMixin, View):
    def get(self, request):
        drivers = Driver.objects.all().order_by('name')
        
        fuel_logs = FuelLog.objects.select_related('truck', 'driver')
        
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        
        if date_from:
            fuel_logs = fuel_logs.filter(date__gte=date_from)
        if date_to:
            fuel_logs = fuel_logs.filter(date__lte=date_to)
        
        pdf_gen = DriverPerformancePDF()
        pdf_content = pdf_gen.generate(drivers, fuel_logs, date_from, date_to, request.user.username)
        
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="driver_performance_report.pdf"'
        
        return response


# ==================== COST PER KM ANALYSIS ====================

class CostPerKmAnalysisView(LoginRequiredMixin, TemplateView):
    template_name = 'reporting/cost_per_km_analysis.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        
        start_date = datetime.strptime(date_from, '%Y-%m-%d') if date_from else None
        end_date = datetime.strptime(date_to, '%Y-%m-%d') if date_to else None
        
        # Get cost per km for all trucks
        truck_metrics = get_all_trucks_cost_per_km(start_date, end_date)
        
        context['truck_metrics'] = truck_metrics
        
        # Summary stats
        if truck_metrics:
            avg_cost = sum(t['cost_per_km'] for t in truck_metrics) / len(truck_metrics)
            context['avg_cost_per_km'] = float(avg_cost)
            context['best_truck'] = min(truck_metrics, key=lambda x: x['cost_per_km'])
            context['worst_truck'] = max(truck_metrics, key=lambda x: x['cost_per_km'])
        
        context['breadcrumbs'] = [
            {'name': 'Dashboard', 'url': '/dashboard/'},
            {'name': 'Cost Per KM Analysis', 'url': None}
        ]
        
        return context


class CostPerKmCSVExportView(LoginRequiredMixin, View):
    def get(self, request):
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        
        start_date = datetime.strptime(date_from, '%Y-%m-%d') if date_from else None
        end_date = datetime.strptime(date_to, '%Y-%m-%d') if date_to else None
        
        truck_metrics = get_all_trucks_cost_per_km(start_date, end_date)
        
        return export_cost_per_km(truck_metrics)


class CostPerKmPDFExportView(LoginRequiredMixin, View):
    def get(self, request):
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        
        start_date = datetime.strptime(date_from, '%Y-%m-%d') if date_from else None
        end_date = datetime.strptime(date_to, '%Y-%m-%d') if date_to else None
        
        truck_metrics = get_all_trucks_cost_per_km(start_date, end_date)
        
        pdf_gen = CostPerKmPDF()
        pdf_content = pdf_gen.generate(truck_metrics, request.user.username)
        
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="cost_per_km_report.pdf"'
        
        return response


# ==================== FLEET EFFICIENCY COMPARISON ====================

class FleetEfficiencyComparisonView(LoginRequiredMixin, TemplateView):
    template_name = 'reporting/fleet_efficiency_comparison.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        
        start_date = datetime.strptime(date_from, '%Y-%m-%d') if date_from else None
        end_date = datetime.strptime(date_to, '%Y-%m-%d') if date_to else None
        
        efficiency_data = get_all_trucks_efficiency(start_date, end_date)
        
        # Sort by efficiency
        sort_by = self.request.GET.get('sort_by', 'efficiency_desc')
        if sort_by == 'efficiency_asc':
            efficiency_data.sort(key=lambda x: x['efficiency'])
        elif sort_by == 'plate_asc':
            efficiency_data.sort(key=lambda x: x['truck'].plate_number)
        elif sort_by == 'plate_desc':
            efficiency_data.sort(key=lambda x: x['truck'].plate_number, reverse=True)
        # Default: efficiency_desc
        
        context['efficiency_data'] = efficiency_data
        
        # Summary
        fleet_avg = get_fleet_average_efficiency(start_date, end_date)
        context['fleet_average'] = float(fleet_avg)
        
        if efficiency_data:
            context['best_performer'] = efficiency_data[0]
            context['worst_performer'] = efficiency_data[-1]
        
        context['breadcrumbs'] = [
            {'name': 'Dashboard', 'url': '/dashboard/'},
            {'name': 'Fleet Efficiency Comparison', 'url': None}
        ]
        
        return context


class FleetEfficiencyCSVExportView(LoginRequiredMixin, View):
    def get(self, request):
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        
        start_date = datetime.strptime(date_from, '%Y-%m-%d') if date_from else None
        end_date = datetime.strptime(date_to, '%Y-%m-%d') if date_to else None
        
        efficiency_data = get_all_trucks_efficiency(start_date, end_date)
        
        return export_fleet_efficiency(efficiency_data)


class FleetEfficiencyPDFExportView(LoginRequiredMixin, View):
    def get(self, request):
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        
        start_date = datetime.strptime(date_from, '%Y-%m-%d') if date_from else None
        end_date = datetime.strptime(date_to, '%Y-%m-%d') if date_to else None
        
        efficiency_data = get_all_trucks_efficiency(start_date, end_date)
        
        pdf_gen = FleetEfficiencyPDF()
        pdf_content = pdf_gen.generate(efficiency_data, request.user.username)
        
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="fleet_efficiency_report.pdf"'
        
        return response


# ==================== DRIVER PERFORMANCE ANALYTICS ====================

class DriverPerformanceAnalyticsView(LoginRequiredMixin, TemplateView):
    template_name = 'reporting/driver_analytics.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        
        start_date = datetime.strptime(date_from, '%Y-%m-%d') if date_from else None
        end_date = datetime.strptime(date_to, '%Y-%m-%d') if date_to else None
        
        # Get driver rankings
        rankings = get_driver_rankings(start_date, end_date)
        
        context['rankings'] = rankings
        context['top_3'] = rankings[:3]
        context['bottom_3'] = rankings[-3:] if len(rankings) >= 3 else []
        
        # Summary
        if rankings:
            context['avg_score'] = sum(r['total_score'] for r in rankings) / len(rankings)
        
        context['breadcrumbs'] = [
            {'name': 'Dashboard', 'url': '/dashboard/'},
            {'name': 'Driver Analytics', 'url': None}
        ]
        
        return context


# ==================== PREDICTIVE MAINTENANCE ====================

class PredictiveMaintenanceView(LoginRequiredMixin, TemplateView):
    template_name = 'reporting/predictive_maintenance.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get maintenance alerts
        maintenance = get_maintenance_summary()
        
        context['alerts'] = maintenance['alerts']
        context['summary'] = maintenance
        
        context['breadcrumbs'] = [
            {'name': 'Dashboard', 'url': '/dashboard/'},
            {'name': 'Predictive Maintenance', 'url': None}
        ]
        
        return context


class PredictiveMaintenanceCSVExportView(LoginRequiredMixin, View):
    def get(self, request):
        maintenance = get_maintenance_summary()
        
        return export_predictive_maintenance(maintenance['alerts'])


class PredictiveMaintenancePDFExportView(LoginRequiredMixin, View):
    def get(self, request):
        maintenance = get_maintenance_summary()
        
        pdf_gen = PredictiveMaintenancePDF()
        pdf_content = pdf_gen.generate(maintenance['alerts'], request.user.username)
        
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="predictive_maintenance_report.pdf"'
        
        return response


# ==================== API ENDPOINTS FOR CHARTS ====================

class CostPerKmChartAPIView(LoginRequiredMixin, View):
    def get(self, request):
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        
        start_date = datetime.strptime(date_from, '%Y-%m-%d') if date_from else None
        end_date = datetime.strptime(date_to, '%Y-%m-%d') if date_to else None
        
        truck_metrics = get_all_trucks_cost_per_km(start_date, end_date)
        
        data = {
            'labels': [m['truck'].plate_number for m in truck_metrics],
            'values': [float(m['cost_per_km']) for m in truck_metrics]
        }
        
        return JsonResponse(data)


class EfficiencyChartAPIView(LoginRequiredMixin, View):
    def get(self, request):
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        
        start_date = datetime.strptime(date_from, '%Y-%m-%d') if date_from else None
        end_date = datetime.strptime(date_to, '%Y-%m-%d') if date_to else None
        
        efficiency_data = get_all_trucks_efficiency(start_date, end_date)
        
        data = {
            'labels': [d['truck'].plate_number for d in efficiency_data],
            'values': [float(d['efficiency']) for d in efficiency_data]
        }
        
        return JsonResponse(data)


class FuelTrendChartAPIView(LoginRequiredMixin, View):
    def get(self, request):
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        
        start_date = datetime.strptime(date_from, '%Y-%m-%d') if date_from else None
        end_date = datetime.strptime(date_to, '%Y-%m-%d') if date_to else None
        
        fuel_trend = get_monthly_fuel_trend(start_date, end_date)
        
        data = {
            'labels': [f['month'] for f in fuel_trend],
            'liters': [f['total_liters'] for f in fuel_trend],
            'costs': [f['total_cost'] for f in fuel_trend]
        }
        
        return JsonResponse(data)


class DriverPerformanceChartAPIView(LoginRequiredMixin, View):
    def get(self, request):
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        
        start_date = datetime.strptime(date_from, '%Y-%m-%d') if date_from else None
        end_date = datetime.strptime(date_to, '%Y-%m-%d') if date_to else None
        
        rankings = get_driver_rankings(start_date, end_date)
        
        data = {
            'labels': [r['driver'].name for r in rankings],
            'scores': [r['total_score'] for r in rankings],
            'efficiencies': [float(r['avg_efficiency']) for r in rankings]
        }
        
        return JsonResponse(data)