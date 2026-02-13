from django.db.models import Sum
from datetime import timedelta
from django.utils import timezone


def calculate_fuel_efficiency(truck, days=30):
    """Calculate fuel efficiency for a truck over the last N days"""
    from fleet.models import FuelLog
    
    start_date = timezone.now().date() - timedelta(days=days)
    fuel_logs = FuelLog.objects.filter(truck=truck, date__gte=start_date)
    
    total_liters = fuel_logs.aggregate(Sum('fuel_liters'))['fuel_liters__sum'] or 0
    
    total_odometer_delta = 0
    for log in fuel_logs:
        delta = (log.odometer or 0) - (log.previous_odometer or 0)
        if delta > 0:
            total_odometer_delta += delta
    
    if total_liters > 0:
        return total_odometer_delta / total_liters
    return 0


def calculate_tire_metrics(tire):
    """Calculate tire metrics including cost per km"""
    total_cost = (tire.purchase_cost or 0) + (tire.mounting_cost or 0) + (tire.repair_costs or 0)
    total_mileage = tire.calculate_current_mileage()
    
    cost_per_km = (total_cost / total_mileage) if total_mileage > 0 else 0
    
    return {
        'total_cost': total_cost,
        'total_mileage': total_mileage,
        'cost_per_km': cost_per_km
    }
