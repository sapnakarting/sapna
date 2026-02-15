from datetime import timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.http import HttpResponse, JsonResponse
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views import View
from django.views.generic import CreateView, ListView, TemplateView

from fleet.models import Truck, Driver, FuelLog, TireInventory
from fleet.utils.permissions import AdminRequiredMixin
from operations.models import CoalLog, MiningLog
from dashboard.models import ActivityLog, ComplianceAlert, ReportSchedule
from .forms import (
    FleetStatusFilterForm,
    FuelReportFilterForm,
    OperationsSummaryFilterForm,
    ReportScheduleForm,
    TireCostReportFilterForm,
)
from .utils.reporting import (
    generate_fleet_status_csv,
    generate_fleet_status_pdf,
    generate_fuel_consumption_csv,
    generate_fuel_consumption_pdf,
    generate_operations_summary_csv,
    generate_operations_summary_pdf,
    generate_tire_cost_csv,
    generate_tire_cost_pdf,
    get_fleet_status_data,
    get_fuel_consumption_data,
    get_operations_summary_data,
    get_tire_cost_data,
)


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Fleet metrics
        total_trucks = Truck.objects.count()
        active_trucks = Truck.objects.filter(status='ACTIVE').count()
        total_drivers = Driver.objects.count()
        active_drivers = Driver.objects.filter(status='ON_DUTY').count()

        # Fuel metrics (last 30 days)
        thirty_days_ago = timezone.now().date() - timedelta(days=30)
        fuel_logs = FuelLog.objects.filter(date__gte=thirty_days_ago)
        total_fuel = fuel_logs.aggregate(Sum('fuel_liters'))['fuel_liters__sum']
        total_fuel_cost = fuel_logs.aggregate(Sum('fuel_cost'))['fuel_cost__sum']

        # Tire metrics
        total_tires = TireInventory.objects.count()
        mounted_tires = TireInventory.objects.filter(status='MOUNTED').count()
        scrapped_tires = TireInventory.objects.filter(status='SCRAPPED').count()
        total_tire_cost = TireInventory.objects.aggregate(Sum('purchase_cost'))['purchase_cost__sum']

        # Operations metrics (last 30 days)
        coal_logs = CoalLog.objects.filter(date__gte=thirty_days_ago)
        total_coal = coal_logs.aggregate(Sum('net_weight'))['net_weight__sum']

        mining_logs = MiningLog.objects.filter(date__gte=thirty_days_ago)
        total_mining = mining_logs.aggregate(Sum('net'))['net__sum']

        # Compliance alerts
        pending_alerts = ComplianceAlert.objects.filter(is_dismissed=False).count()
        high_priority_alerts = ComplianceAlert.objects.filter(
            is_dismissed=False,
            severity='HIGH'
        ).count()

        # Recent activity (last 10)
        recent_activities = ActivityLog.objects.all()[:10]

        context.update({
            # Fleet stats
            'total_trucks': total_trucks,
            'active_trucks': active_trucks,
            'total_drivers': total_drivers,
            'active_drivers': active_drivers,

            # Fuel stats
            'total_fuel_liters': total_fuel,
            'total_fuel_cost': f"₹{total_fuel_cost:,.2f}" if total_fuel_cost else "₹0.00",

            # Tire stats
            'total_tires': total_tires,
            'mounted_tires': mounted_tires,
            'scrapped_tires': scrapped_tires,
            'total_tire_cost': f"₹{total_tire_cost:,.2f}" if total_tire_cost else "₹0.00",

            # Operations stats
            'total_coal_tons': total_coal,
            'total_mining_tons': total_mining,

            # Alerts
            'pending_alerts': pending_alerts,
            'high_priority_alerts': high_priority_alerts,

            # Activity
            'recent_activities': recent_activities,
            'last_updated': timezone.now(),
        })

        return context


class MetricsView(LoginRequiredMixin, TemplateView):
    template_name = None

    def get(self, request, *args, **kwargs):
        period = request.GET.get('period', '30')
        days = int(period)
        start_date = timezone.now().date() - timedelta(days=days)

        metrics = {}

        # Fuel efficiency by truck
        fuel_logs = FuelLog.objects.filter(date__gte=start_date)

        trucks = Truck.objects.all()
        truck_metrics = []

        for truck in trucks:
            truck_fuel = fuel_logs.filter(truck=truck)
            total_liters = truck_fuel.aggregate(Sum('fuel_liters'))['fuel_liters__sum'] or 0
            total_cost = truck_fuel.aggregate(Sum('fuel_cost'))['fuel_cost__sum'] or 0

            # Calculate efficiency: total kilometers traveled / total fuel used
            total_odometer_delta = 0
            for log in truck_fuel:
                delta = (log.odometer or 0) - (log.previous_odometer or 0)
                if delta > 0:
                    total_odometer_delta += delta

            avg_efficiency = total_odometer_delta / total_liters if total_liters > 0 else 0

            truck_metrics.append({
                'truck_id': truck.id,
                'plate_number': truck.plate_number,
                'total_fuel_liters': total_liters,
                'total_fuel_cost': f"₹{total_cost:,.2f}" if total_cost else "₹0.00",
                'fuel_efficiency_km_per_l': f"{avg_efficiency:.2f}",
            })

        metrics['fuel'] = truck_metrics

        # Tire costs
        tires = TireInventory.objects.all()

        tire_costs = []
        for tire in tires:
            total_cost = (tire.purchase_cost or 0) + (tire.mounting_cost or 0) + (tire.repair_costs or 0)
            total_mileage = tire.historical_mileage or 0
            cost_per_km = (total_cost / total_mileage) if total_mileage > 0 else 0

            tire_costs.append({
                'tire_id': tire.id,
                'serial_number': tire.serial_number,
                'brand': tire.brand,
                'status': tire.status,
                'total_cost': f"₹{total_cost:,.2f}",
                'cost_per_km': f"₹{cost_per_km:.2f}",
            })

        metrics['tires'] = tire_costs

        # Operations stats
        ops_start_date = timezone.now().date() - timedelta(days=days)

        coal_logs = CoalLog.objects.filter(date__gte=ops_start_date)
        coal_metrics = {
            'total_trips': coal_logs.count(),
            'total_tonnage': coal_logs.aggregate(Sum('net_weight'))['net_weight__sum'] or 0,
            'total_diesel': coal_logs.aggregate(Sum('diesel_liters'))['diesel_liters__sum'] or 0,
            'total_diesel_cost': coal_logs.aggregate(Sum('diesel_cost'))['diesel_cost__sum'] or 0,
        }

        mining_logs = MiningLog.objects.filter(date__gte=ops_start_date)
        mining_metrics = {
            'total_trips': mining_logs.count(),
            'total_tonnage': mining_logs.aggregate(Sum('net'))['net__sum'] or 0,
        }

        metrics['operations'] = {
            'coal': coal_metrics,
            'mining': mining_metrics,
        }

        return JsonResponse(metrics)


class ChartDataView(LoginRequiredMixin, TemplateView):
    template_name = None

    def get(self, request, *args, **kwargs):
        start_date, end_date = self._get_date_range(request)

        fuel_payload = self._build_fuel_efficiency(start_date, end_date)
        tire_payload = self._build_tire_costs(start_date, end_date)
        operations_payload = self._build_operations_summary(start_date, end_date)

        return JsonResponse({
            'fuel_efficiency': fuel_payload,
            'tire_costs': tire_payload,
            'operations': operations_payload,
            'range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
            },
            'last_updated': timezone.now().isoformat(),
        })

    def _get_date_range(self, request):
        start_value = parse_date(request.GET.get('start') or '')
        end_value = parse_date(request.GET.get('end') or '')
        today = timezone.now().date()

        end_date = end_value or today
        start_date = start_value or (end_date - timedelta(days=30))

        if start_date > end_date:
            start_date, end_date = end_date, start_date

        return start_date, end_date

    def _build_fuel_efficiency(self, start_date, end_date):
        fuel_logs = FuelLog.objects.filter(date__range=(start_date, end_date))

        date_cursor = start_date
        date_range = []
        totals = {}
        while date_cursor <= end_date:
            totals[date_cursor] = {'liters': 0, 'distance': 0}
            date_range.append(date_cursor)
            date_cursor += timedelta(days=1)

        for log in fuel_logs:
            entry = totals.get(log.date)
            if entry is None:
                continue
            entry['liters'] += float(log.fuel_liters or 0)
            delta = (log.odometer or 0) - (log.previous_odometer or 0)
            if delta > 0:
                entry['distance'] += delta

        labels = [day.strftime('%b %d') for day in date_range]
        data = []
        for day in date_range:
            liters = totals[day]['liters']
            distance = totals[day]['distance']
            efficiency = distance / liters if liters > 0 else 0
            data.append(round(efficiency, 2))

        return {'labels': labels, 'data': data}

    def _build_tire_costs(self, start_date, end_date):
        tires = TireInventory.objects.filter(created_at__date__range=(start_date, end_date))
        tire_costs = []

        for tire in tires:
            cost_per_km = float(tire.calculate_cost_per_km())
            tire_costs.append((cost_per_km, tire))

        tire_costs.sort(key=lambda item: item[0], reverse=True)

        labels = []
        data = []
        for cost, tire in tire_costs[:6]:
            labels.append(tire.serial_number)
            data.append(round(cost, 2))

        return {'labels': labels, 'data': data}

    def _build_operations_summary(self, start_date, end_date):
        coal_logs = CoalLog.objects.filter(date__range=(start_date, end_date))
        mining_logs = MiningLog.objects.filter(date__range=(start_date, end_date))

        coal_tonnage = float(coal_logs.aggregate(Sum('net_weight'))['net_weight__sum'] or 0)
        mining_tonnage = float(mining_logs.aggregate(Sum('net'))['net__sum'] or 0)

        return {
            'labels': ['Coal', 'Mining'],
            'data': [round(coal_tonnage, 2), round(mining_tonnage, 2)],
            'trips': [coal_logs.count(), mining_logs.count()],
        }


class ActivityFeedView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/activity_feed_partial.html'

    def get_context_data(self, **kwargs):
        activities = ActivityLog.objects.all()[:10]
        return {'activities': activities}


class ComplianceAlertView(LoginRequiredMixin, TemplateView):
    template_name = None

    def get(self, request, *args, **kwargs):
        alerts = ComplianceAlert.objects.filter(is_dismissed=False)

        # Check document expiries
        from fleet.utils.expiry_helpers import get_expiry_color_code

        expiring_docs = []
        for truck in Truck.objects.all():
            for doc_type, date in [
                ('Fitness', truck.fitness_expiry),
                ('Insurance', truck.insurance_expiry),
                ('PUCC', truck.pucc_expiry),
                ('Tax', truck.tax_expiry),
                ('Permit', truck.permit_expiry),
            ]:
                if date:
                    days_until = (date - timezone.now().date()).days
                    if 0 <= days_until <= 7:
                        alert = {
                            'type': 'DOCUMENT_EXPIRY',
                            'message': f"{truck.plate_number} {doc_type} expires in {days_until} days",
                            'severity': 'HIGH',
                            'metadata': {
                                'truck_id': truck.id,
                                'document_type': doc_type,
                                'expiry_date': date.isoformat(),
                                'days_until': days_until,
                                'color': get_expiry_color_code(date),
                            }
                        }
                        expiring_docs.append(alert)

        # Check fuel efficiency anomalies
        fuel_alerts = []
        # Logic to check if any truck has efficiency below benchmark
        # Would use SystemSettings to get benchmarks
        try:
            from settings_app.models import SystemSettings
            settings = SystemSettings.objects.first()
            if settings:
                benchmark = settings.global_fuel_efficiency_benchmark

                # Calculate efficiency for each truck
                thirty_days_ago = timezone.now().date() - timedelta(days=30)
                fuel_logs = FuelLog.objects.filter(date__gte=thirty_days_ago)

                for truck in Truck.objects.all():
                    truck_fuel = fuel_logs.filter(truck=truck)
                    total_liters = truck_fuel.aggregate(Sum('fuel_liters'))['fuel_liters__sum'] or 0

                    total_odometer_delta = 0
                    for log in truck_fuel:
                        delta = (log.odometer or 0) - (log.previous_odometer or 0)
                        if delta > 0:
                            total_odometer_delta += delta

                    if total_liters > 0:
                        avg_efficiency = total_odometer_delta / total_liters
                        if avg_efficiency < benchmark:
                            fuel_alerts.append({
                                'type': 'FUEL_EFFICIENCY',
                                'message': f"{truck.plate_number} fuel efficiency ({avg_efficiency:.2f} km/l) below benchmark ({benchmark} km/l)",
                                'severity': 'MEDIUM',
                                'metadata': {
                                    'truck_id': truck.id,
                                    'efficiency': avg_efficiency,
                                    'benchmark': benchmark,
                                }
                            })
        except Exception:
            pass

        return JsonResponse({
            'document_alerts': expiring_docs,
            'fuel_alerts': fuel_alerts,
            'total_alerts': len(expiring_docs) + len(fuel_alerts)
        })


class DismissAlertView(LoginRequiredMixin, TemplateView):
    template_name = None

    def post(self, request, *args, **kwargs):
        alert_id = request.POST.get('alert_id')
        try:
            alert = ComplianceAlert.objects.get(pk=alert_id)
            alert.is_dismissed = True
            alert.dismissed_at = timezone.now()
            alert.dismissed_by = request.user
            alert.save()

            # Log activity
            ActivityLog.objects.create(
                action='ALERT_DISMISSED',
                description=f"Alert dismissed: {alert.message}",
                actor=request.user,
            )

            return JsonResponse({'success': True})
        except ComplianceAlert.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Alert not found'}, status=404)


class ReportIndexView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/report_index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['breadcrumbs'] = [
            {'name': 'Reports', 'url': None}
        ]
        return context


class FuelConsumptionReportView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/fuel_consumption_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = FuelReportFilterForm(self.request.GET)
        filters = form.cleaned_data if form.is_valid() else {}
        data = get_fuel_consumption_data(filters)

        truck_summary = sorted(
            data['truck_summary'].values(),
            key=lambda item: item['truck'].plate_number,
        )
        context.update({
            'filter_form': form,
            'summary': data['summary'],
            'entries': data['entries'],
            'truck_summary': truck_summary,
            'breadcrumbs': [
                {'name': 'Reports', 'url': reverse_lazy('dashboard:report-index')},
                {'name': 'Fuel Consumption', 'url': None},
            ],
        })
        return context


class FuelConsumptionReportPDFView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        form = FuelReportFilterForm(request.GET)
        filters = form.cleaned_data if form.is_valid() else {}
        pdf = generate_fuel_consumption_pdf(filters)
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="fuel_consumption_report.pdf"'
        return response


class FuelConsumptionReportCSVView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        form = FuelReportFilterForm(request.GET)
        filters = form.cleaned_data if form.is_valid() else {}
        csv_data = generate_fuel_consumption_csv(filters)
        response = HttpResponse(csv_data, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="fuel_consumption_report.csv"'
        return response


class TireCostReportView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/tire_cost_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = TireCostReportFilterForm(self.request.GET)
        filters = form.cleaned_data if form.is_valid() else {}
        data = get_tire_cost_data(filters)

        context.update({
            'filter_form': form,
            'summary': data['summary'],
            'tires': data['tires'],
            'status_counts': data['status_counts'],
            'breadcrumbs': [
                {'name': 'Reports', 'url': reverse_lazy('dashboard:report-index')},
                {'name': 'Tire Cost Analysis', 'url': None},
            ],
        })
        return context


class TireCostReportPDFView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        form = TireCostReportFilterForm(request.GET)
        filters = form.cleaned_data if form.is_valid() else {}
        pdf = generate_tire_cost_pdf(filters)
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="tire_cost_report.pdf"'
        return response


class TireCostReportCSVView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        form = TireCostReportFilterForm(request.GET)
        filters = form.cleaned_data if form.is_valid() else {}
        csv_data = generate_tire_cost_csv(filters)
        response = HttpResponse(csv_data, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="tire_cost_report.csv"'
        return response


class OperationsSummaryReportView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/operations_summary_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = OperationsSummaryFilterForm(self.request.GET)
        filters = form.cleaned_data if form.is_valid() else {}
        data = get_operations_summary_data(filters)

        context.update({
            'filter_form': form,
            'coal_summary': data['coal_summary'],
            'mining_summary': data['mining_summary'],
            'coal_logs': data['coal_logs'],
            'mining_logs': data['mining_logs'],
            'breadcrumbs': [
                {'name': 'Reports', 'url': reverse_lazy('dashboard:report-index')},
                {'name': 'Operations Summary', 'url': None},
            ],
        })
        return context


class OperationsSummaryReportPDFView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        form = OperationsSummaryFilterForm(request.GET)
        filters = form.cleaned_data if form.is_valid() else {}
        pdf = generate_operations_summary_pdf(filters)
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="operations_summary_report.pdf"'
        return response


class OperationsSummaryReportCSVView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        form = OperationsSummaryFilterForm(request.GET)
        filters = form.cleaned_data if form.is_valid() else {}
        csv_data = generate_operations_summary_csv(filters)
        response = HttpResponse(csv_data, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="operations_summary_report.csv"'
        return response


class FleetStatusReportView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/fleet_status_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = FleetStatusFilterForm(self.request.GET)
        filters = form.cleaned_data if form.is_valid() else {}
        data = get_fleet_status_data(filters)

        context.update({
            'filter_form': form,
            'summary': data['summary'],
            'driver_summary': data['driver_summary'],
            'tire_summary': data['tire_summary'],
            'trucks': data['trucks'],
            'upcoming_docs': data['upcoming_docs'],
            'pending_alerts': data['pending_alerts'],
            'breadcrumbs': [
                {'name': 'Reports', 'url': reverse_lazy('dashboard:report-index')},
                {'name': 'Fleet Status', 'url': None},
            ],
        })
        return context


class FleetStatusReportPDFView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        form = FleetStatusFilterForm(request.GET)
        filters = form.cleaned_data if form.is_valid() else {}
        pdf = generate_fleet_status_pdf(filters)
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="fleet_status_report.pdf"'
        return response


class FleetStatusReportCSVView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        form = FleetStatusFilterForm(request.GET)
        filters = form.cleaned_data if form.is_valid() else {}
        csv_data = generate_fleet_status_csv(filters)
        response = HttpResponse(csv_data, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="fleet_status_report.csv"'
        return response


class ReportScheduleListView(AdminRequiredMixin, ListView):
    model = ReportSchedule
    template_name = 'dashboard/report_schedule_list.html'
    context_object_name = 'schedules'
    paginate_by = 20
    ordering = ['next_run_at']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['breadcrumbs'] = [
            {'name': 'Reports', 'url': reverse_lazy('dashboard:report-index')},
            {'name': 'Schedules', 'url': None},
        ]
        return context


class ReportScheduleCreateView(AdminRequiredMixin, CreateView):
    model = ReportSchedule
    form_class = ReportScheduleForm
    template_name = 'dashboard/report_schedule_form.html'
    success_url = reverse_lazy('dashboard:report-schedule-list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['breadcrumbs'] = [
            {'name': 'Reports', 'url': reverse_lazy('dashboard:report-index')},
            {'name': 'Schedules', 'url': reverse_lazy('dashboard:report-schedule-list')},
            {'name': 'Create', 'url': None},
        ]
        return context
