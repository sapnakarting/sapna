from django.db.models import Sum, Avg
from fleet.models import FuelLog, TireInventory


def calculate_fuel_efficiency(fuel_logs):
    """Calculate fuel efficiency metrics"""
    if not fuel_logs.exists():
        return {
            'avg_km_per_liter': 0,
            'total_fuel': 0,
            'total_cost': 0,
        }

    total_fuel = fuel_logs.aggregate(Sum('fuel_liters'))['fuel_liters__sum'] or 0
    total_cost = fuel_logs.aggregate(Sum('fuel_cost'))['fuel_cost__sum'] or 0

    total_odometer_delta = 0
    for log in fuel_logs:
        delta = (log.odometer or 0) - (log.previous_odometer or 0)
        if delta > 0:
            total_odometer_delta += delta

    avg_efficiency = total_odometer_delta / total_fuel if total_fuel > 0 else 0

    return {
        'avg_km_per_liter': avg_efficiency,
        'total_fuel': total_fuel,
        'total_cost': total_cost,
        'avg_cost_per_liter': total_cost / total_fuel if total_fuel > 0 else 0,
    }


def calculate_tire_metrics(tires):
    """Calculate tire cost and mileage metrics"""
    if not tires.exists():
        return {
            'total_tires': 0,
            'avg_cost_per_km': 0,
            'avg_cost_per_tire': 0,
        }

    total_cost = 0
    total_mileage = 0

    for tire in tires:
        tire_cost = (tire.purchase_cost or 0) + (tire.mounting_cost or 0) + (tire.repair_costs or 0)
        total_cost += tire_cost
        if tire.historical_mileage:
            total_mileage += tire.historical_mileage

    avg_cost_per_km = (total_cost / total_mileage) if total_mileage > 0 else 0

    return {
        'total_tires': tires.count(),
        'total_cost': total_cost,
        'avg_cost_per_km': avg_cost_per_km,
        'avg_cost_per_tire': total_cost / tires.count() if tires.count() > 0 else 0,
    }
