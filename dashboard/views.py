from django.views.generic import TemplateView
from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse

from fleet.models import Truck, Driver, FuelLog, TireInventory
from operations.models import CoalLog, MiningLog
from dashboard.models import ActivityLog, ComplianceAlert
from dashboard.utils.metrics import calculate_fuel_efficiency, calculate_tire_metrics
from .utils.permissions import is_admin_required


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
