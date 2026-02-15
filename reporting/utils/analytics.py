"""
Analytics utility module for calculating fleet metrics and performance indicators.
"""

from decimal import Decimal
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta

from django.db.models import Sum, Count, Avg, Q
from django.db.models.functions import TruncDate, TruncMonth

from fleet.models import Truck, Driver, FuelLog, TireInventory, DailyOdoRegistry
from operations.models import CoalLog, MiningLog


def calculate_cost_per_km(truck: Truck, start_date: datetime = None, end_date: datetime = None) -> Dict[str, Any]:
    """
    Calculate cost per km for a specific truck.
    
    Returns dict with:
    - fuel_cost: Total fuel cost for period
    - tire_cost: Total tire cost (depreciated)
    - total_cost: Combined cost
    - total_km: Total kilometers driven
    - cost_per_km: Calculated cost per kilometer
    """
    # Filter fuel logs by date range if provided
    fuel_query = Q(truck=truck)
    if start_date:
        fuel_query &= Q(date__gte=start_date.date())
    if end_date:
        fuel_query &= Q(date__lte=end_date.date())
    
    fuel_logs = FuelLog.objects.filter(fuel_query)
    fuel_cost = fuel_logs.aggregate(total=Sum('fuel_cost'))['total'] or Decimal('0')
    
    # Calculate tire cost (depreciated based on mileage)
    tires = TireInventory.objects.filter(truck=truck, status__in=['MOUNTED', 'NEW'])
    tire_cost = Decimal('0')
    for tire in tires:
        tire_cost += tire.calculate_total_cost() * Decimal(str(min(tire.calculate_current_mileage() / 50000, 1)))
    
    # Calculate total kilometers
    if start_date and end_date:
        odo_query = Q(truck=truck, date__gte=start_date.date(), date__lte=end_date.date())
    elif start_date:
        odo_query = Q(truck=truck, date__gte=start_date.date())
    elif end_date:
        odo_query = Q(truck=truck, date__lte=end_date.date())
    else:
        odo_query = Q(truck=truck)
    
    daily_odos = DailyOdoRegistry.objects.filter(odo_query)
    total_km = daily_odos.aggregate(total=Sum('daily_mileage'))['total'] or 0
    
    total_cost = fuel_cost + tire_cost
    cost_per_km = Decimal(str(total_cost / total_km)) if total_km > 0 else Decimal('0')
    
    return {
        'truck': truck,
        'fuel_cost': fuel_cost,
        'tire_cost': tire_cost,
        'total_cost': total_cost,
        'total_km': total_km,
        'cost_per_km': cost_per_km
    }


def calculate_fuel_efficiency(truck: Truck = None, driver: Driver = None, 
                               start_date: datetime = None, end_date: datetime = None) -> Dict[str, Any]:
    """
    Calculate fuel efficiency for a truck or driver.
    
    If both truck and driver are provided, calculates efficiency for that driver in that truck.
    """
    fuel_query = Q()
    if truck:
        fuel_query &= Q(truck=truck)
    if driver:
        fuel_query &= Q(driver=driver)
    if start_date:
        fuel_query &= Q(date__gte=start_date.date())
    if end_date:
        fuel_query &= Q(date__lte=end_date.date())
    
    fuel_logs = FuelLog.objects.filter(fuel_query).select_related('truck', 'driver')
    
    if not fuel_logs.exists():
        return {
            'truck': truck,
            'driver': driver,
            'total_fuel': Decimal('0'),
            'total_distance': 0,
            'efficiency': Decimal('0'),
            'trips': 0
        }
    
    total_fuel = sum(log.fuel_liters for log in fuel_logs)
    total_distance = sum(
        log.odometer - log.previous_odometer 
        for log in fuel_logs 
        if log.previous_odometer > 0
    )
    
    efficiency = Decimal(str(total_distance / total_fuel)) if total_fuel > 0 else Decimal('0')
    
    return {
        'truck': truck,
        'driver': driver,
        'total_fuel': total_fuel,
        'total_distance': total_distance,
        'efficiency': efficiency,
        'trips': fuel_logs.count()
    }


def calculate_driver_performance_score(driver: Driver, start_date: datetime = None, 
                                        end_date: datetime = None) -> Dict[str, Any]:
    """
    Calculate overall performance score for a driver.
    
    Scoring algorithm:
    - Efficiency (40%): How well they manage fuel
    - Trips (30%): Number of trips completed
    - Consistency (30%): Variance in efficiency (lower is better)
    """
    fuel_query = Q(driver=driver)
    if start_date:
        fuel_query &= Q(date__gte=start_date.date())
    if end_date:
        fuel_query &= Q(date__lte=end_date.date())
    
    fuel_logs = FuelLog.objects.filter(fuel_query)
    
    if not fuel_logs.exists():
        return {
            'driver': driver,
            'efficiency_score': 0,
            'trips_score': 0,
            'consistency_score': 0,
            'total_score': 0,
            'total_trips': 0,
            'avg_efficiency': Decimal('0')
        }
    
    # Efficiency score (normalize to 0-100, 5 km/l = 50, 10 km/l = 100)
    efficiency_data = calculate_fuel_efficiency(driver=driver, start_date=start_date, end_date=end_date)
    avg_efficiency = efficiency_data['efficiency']
    efficiency_score = min(100, (float(avg_efficiency) / 10) * 100) if avg_efficiency > 0 else 0
    
    # Trips score (normalize: 20 trips = 100)
    total_trips = fuel_logs.count()
    trips_score = min(100, (total_trips / 20) * 100)
    
    # Consistency score (calculate variance in efficiency)
    daily_efficiencies = []
    for log in fuel_logs:
        if log.previous_odometer > 0 and log.fuel_liters > 0:
            eff = (log.odometer - log.previous_odometer) / log.fuel_liters
            daily_efficiencies.append(eff)
    
    if len(daily_efficiencies) > 1:
        avg_eff = sum(daily_efficiencies) / len(daily_efficiencies)
        variance = sum((x - avg_eff) ** 2 for x in daily_efficiencies) / len(daily_efficiencies)
        std_dev = variance ** 0.5
        # Lower std_dev = higher consistency (0 = 100, 2 = 0)
        consistency_score = max(0, 100 - (std_dev * 50))
    else:
        consistency_score = 100 if daily_efficiencies else 0
    
    # Calculate weighted total score
    total_score = (efficiency_score * 0.4) + (trips_score * 0.3) + (consistency_score * 0.3)
    
    return {
        'driver': driver,
        'efficiency_score': efficiency_score,
        'trips_score': trips_score,
        'consistency_score': consistency_score,
        'total_score': total_score,
        'total_trips': total_trips,
        'avg_efficiency': avg_efficiency
    }


def get_fleet_average_efficiency(start_date: datetime = None, end_date: datetime = None) -> Decimal:
    """Get average efficiency across the entire fleet."""
    trucks = Truck.objects.filter(status='ACTIVE')
    
    if not trucks.exists():
        return Decimal('0')
    
    total_efficiency = Decimal('0')
    valid_trucks = 0
    
    for truck in trucks:
        eff_data = calculate_fuel_efficiency(truck=truck, start_date=start_date, end_date=end_date)
        if eff_data['efficiency'] > 0:
            total_efficiency += eff_data['efficiency']
            valid_trucks += 1
    
    return total_efficiency / valid_trucks if valid_trucks > 0 else Decimal('0')


def get_all_trucks_cost_per_km(start_date: datetime = None, end_date: datetime = None) -> List[Dict[str, Any]]:
    """Get cost per km for all trucks in the fleet."""
    trucks = Truck.objects.filter(status='ACTIVE')
    
    results = []
    for truck in trucks:
        cost_data = calculate_cost_per_km(truck, start_date, end_date)
        if cost_data['total_km'] > 0:
            results.append(cost_data)
    
    return sorted(results, key=lambda x: x['cost_per_km'])


def get_all_trucks_efficiency(start_date: datetime = None, end_date: datetime = None) -> List[Dict[str, Any]]:
    """Get fuel efficiency for all trucks in the fleet."""
    trucks = Truck.objects.filter(status='ACTIVE')
    fleet_avg = get_fleet_average_efficiency(start_date, end_date)
    
    results = []
    for truck in trucks:
        eff_data = calculate_fuel_efficiency(truck=truck, start_date=start_date, end_date=end_date)
        if eff_data['total_fuel'] > 0:
            results.append({
                'truck': truck,
                'efficiency': eff_data['efficiency'],
                'total_distance': eff_data['total_distance'],
                'total_fuel': eff_data['total_fuel'],
                'trips': eff_data['trips'],
                'vs_fleet_avg': eff_data['efficiency'] - fleet_avg
            })
    
    return sorted(results, key=lambda x: x['efficiency'], reverse=True)


def get_driver_rankings(start_date: datetime = None, end_date: datetime = None) -> List[Dict[str, Any]]:
    """Get ranked list of all drivers by performance."""
    drivers = Driver.objects.filter(status='ON_DUTY')
    
    rankings = []
    for driver in drivers:
        perf_data = calculate_driver_performance_score(driver, start_date, end_date)
        rankings.append(perf_data)
    
    return sorted(rankings, key=lambda x: x['total_score'], reverse=True)


def get_monthly_fuel_trend(start_date: datetime = None, end_date: datetime = None) -> List[Dict[str, Any]]:
    """Get monthly fuel consumption trend data for charts."""
    query = Q()
    if start_date:
        query &= Q(date__gte=start_date.date())
    if end_date:
        query &= Q(date__lte=end_date.date())
    
    fuel_logs = FuelLog.objects.filter(query).annotate(
        month=TruncMonth('date')
    ).values('month').annotate(
        total_liters=Sum('fuel_liters'),
        total_cost=Sum('fuel_cost'),
        trip_count=Count('id')
    ).order_by('month')
    
    return [
        {
            'month': item['month'].strftime('%Y-%m') if item['month'] else '',
            'total_liters': float(item['total_liters'] or 0),
            'total_cost': float(item['total_cost'] or 0),
            'trip_count': item['trip_count']
        }
        for item in fuel_logs
    ]


def get_operations_summary(date_from=None, date_to=None) -> Dict[str, Any]:
    """Get operations summary data."""
    coal_query = Q()
    mining_query = Q()
    
    if date_from:
        coal_query &= Q(date__gte=date_from)
        mining_query &= Q(date__gte=date_from)
    if date_to:
        coal_query &= Q(date__lte=date_to)
        mining_query &= Q(date__lte=date_to)
    
    coal_logs = CoalLog.objects.filter(coal_query)
    mining_logs = MiningLog.objects.filter(mining_query)
    
    # Coal summary
    coal_trips = coal_logs.count()
    coal_tonnage = coal_logs.aggregate(total=Sum('net_weight'))['total'] or Decimal('0')
    coal_diesel = coal_logs.aggregate(total=Sum('diesel_liters'))['total'] or Decimal('0')
    
    # Mining summary
    mining_trips = mining_logs.count()
    mining_tonnage = mining_logs.aggregate(total=Sum('net'))['total'] or Decimal('0')
    
    # By type
    coal_internal = coal_logs.filter(truck__mining_type='INTERNAL').count()
    coal_external = coal_logs.filter(truck__mining_type='EXTERNAL').count()
    mining_internal = mining_logs.filter(mining_type='INTERNAL').count()
    mining_external = mining_logs.filter(mining_type='EXTERNAL').count()
    
    return {
        'coal': {
            'trips': coal_trips,
            'tonnage': coal_tonnage,
            'diesel_liters': coal_diesel,
            'internal_trips': coal_internal,
            'external_trips': coal_external
        },
        'mining': {
            'trips': mining_trips,
            'tonnage': mining_tonnage,
            'internal_trips': mining_internal,
            'external_trips': mining_external
        },
        'total_trips': coal_trips + mining_trips,
        'total_tonnage': coal_tonnage + mining_tonnage
    }


def get_fleet_status_summary() -> Dict[str, Any]:
    """Get fleet status summary with document expiry information."""
    trucks = Truck.objects.all()
    
    # Status counts
    status_counts = {
        'ACTIVE': trucks.filter(status='ACTIVE').count(),
        'MAINTENANCE': trucks.filter(status='MAINTENANCE').count(),
        'INACTIVE': trucks.filter(status='INACTIVE').count()
    }
    
    # Document expiry warnings
    today = datetime.now().date()
    from fleet.models import Truck
    from fleet.utils.expiry_helpers import get_expiry_color_code
    
    expiring_docs = []
    for truck in trucks:
        for doc_type in ['fitness', 'insurance', 'pucc', 'tax', 'permit']:
            expiry_field = f'{doc_type}_expiry'
            expiry_date = getattr(truck, expiry_field, None)
            if expiry_date:
                days_until = (expiry_date - today).days
                if days_until <= 30:  # Within 30 days
                    expiring_docs.append({
                        'truck': truck,
                        'document': doc_type.upper(),
                        'expiry_date': expiry_date,
                        'days_until': days_until,
                        'urgency': 'CRITICAL' if days_until <= 7 else ('WARNING' if days_until <= 15 else 'INFO')
                    })
    
    # Sort by days until expiry
    expiring_docs.sort(key=lambda x: x['days_until'])
    
    return {
        'total_trucks': trucks.count(),
        'status_counts': status_counts,
        'expiring_documents': expiring_docs,
        'active_trucks': trucks.filter(status='ACTIVE').count()
    }
