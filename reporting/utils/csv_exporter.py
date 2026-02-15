"""
CSV Exporter utility module.
Generates CSV exports for various report types.
"""

import csv
from io import StringIO
from datetime import datetime
from typing import List, Dict, Any
from decimal import Decimal

from django.http import HttpResponse


def generate_csv_response(filename: str, headers: List[str], rows: List[List]) -> HttpResponse:
    """Generate a CSV HTTP response with given data."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    writer = csv.writer(response)
    writer.writerow(headers)
    writer.writerows(rows)
    
    return response


def export_fuel_consumption(fuel_logs, date_from=None, date_to=None):
    """Export fuel consumption data to CSV."""
    headers = ['Date', 'Truck', 'Driver', 'Entry Type', 'Odometer', 'Previous Odometer', 
               'Distance (km)', 'Fuel (Liters)', 'Price/Liter', 'Total Cost']
    
    rows = []
    for log in fuel_logs:
        distance = log.odometer - log.previous_odometer if log.previous_odometer > 0 else 0
        rows.append([
            log.date.strftime('%Y-%m-%d'),
            log.truck.plate_number,
            log.driver.name,
            log.get_entry_type_display(),
            log.odometer,
            log.previous_odometer,
            distance,
            float(log.fuel_liters),
            float(log.diesel_price),
            float(log.fuel_cost)
        ])
    
    filename = f"fuel_consumption_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return generate_csv_response(filename, headers, rows)


def export_tire_costs(tires):
    """Export tire cost data to CSV."""
    headers = ['Serial Number', 'Brand', 'Status', 'Truck', 'Position', 
               'Purchase Cost', 'Mounting Cost', 'Repair Costs', 'Total Cost',
               'Current Mileage', 'Cost per KM']
    
    rows = []
    for tire in tires:
        rows.append([
            tire.serial_number,
            tire.brand,
            tire.get_status_display(),
            tire.truck.plate_number if tire.truck else 'Not Mounted',
            tire.position,
            float(tire.purchase_cost),
            float(tire.mounting_cost),
            float(tire.repair_costs),
            float(tire.calculate_total_cost()),
            tire.calculate_current_mileage(),
            float(tire.calculate_cost_per_km())
        ])
    
    filename = f"tire_costs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return generate_csv_response(filename, headers, rows)


def export_operations(coal_logs, mining_logs, date_from=None, date_to=None):
    """Export operations data to CSV."""
    headers = ['Type', 'Date', 'Truck', 'Pass/Chalan No', 'Net Weight (MT)', 
               'Origin/Site', 'Destination/Customer', 'Material']
    
    rows = []
    
    # Add coal logs
    for log in coal_logs:
        rows.append([
            'Coal',
            log.date.strftime('%Y-%m-%d'),
            log.truck.plate_number,
            log.pass_no,
            float(log.net_weight),
            log.origin_site,
            log.destination_site,
            'Coal'
        ])
    
    # Add mining logs
    for log in mining_logs:
        rows.append([
            'Mining',
            log.date.strftime('%Y-%m-%d'),
            log.truck.plate_number,
            log.chalan_no,
            float(log.net),
            log.customer_name,
            '',
            log.material
        ])
    
    filename = f"operations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return generate_csv_response(filename, headers, rows)


def export_fleet_status(trucks):
    """Export fleet status data to CSV."""
    headers = ['Plate Number', 'Transporter', 'Wheel Config', 'Fleet Type', 
               'Mining Type', 'Status', 'Current Odometer', 'Fitness Expiry', 
               'Insurance Expiry', 'PUCC Expiry', 'Tax Expiry', 'Permit Expiry']
    
    rows = []
    for truck in trucks:
        rows.append([
            truck.plate_number,
            truck.transporter_name,
            truck.get_wheel_config_display(),
            truck.get_fleet_type_display(),
            truck.get_mining_type_display() if truck.mining_type else '',
            truck.get_status_display(),
            truck.current_odometer,
            truck.fitness_expiry.strftime('%Y-%m-%d') if truck.fitness_expiry else '',
            truck.insurance_expiry.strftime('%Y-%m-%d') if truck.insurance_expiry else '',
            truck.pucc_expiry.strftime('%Y-%m-%d') if truck.pucc_expiry else '',
            truck.tax_expiry.strftime('%Y-%m-%d') if truck.tax_expiry else '',
            truck.permit_expiry.strftime('%Y-%m-%d') if truck.permit_expiry else ''
        ])
    
    filename = f"fleet_status_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return generate_csv_response(filename, headers, rows)


def export_driver_performance(drivers, fuel_logs, date_from=None, date_to=None):
    """Export driver performance data to CSV."""
    headers = ['Driver Name', 'License Number', 'Phone', 'Status', 
               'Total Trips', 'Total Liters', 'Total Cost', 
               'Total Distance (km)', 'Avg Efficiency (km/l)']
    
    rows = []
    for driver in drivers:
        driver_logs = fuel_logs.filter(driver=driver)
        if driver_logs.exists():
            total_liters = sum(log.fuel_liters for log in driver_logs)
            total_cost = sum(log.fuel_cost for log in driver_logs)
            trips = driver_logs.count()
            total_distance = sum(
                log.odometer - log.previous_odometer 
                for log in driver_logs 
                if log.previous_odometer > 0
            )
            avg_efficiency = total_distance / total_liters if total_liters > 0 else 0
            
            rows.append([
                driver.name,
                driver.license_number,
                driver.phone,
                driver.get_status_display(),
                trips,
                float(total_liters),
                float(total_cost),
                total_distance,
                round(avg_efficiency, 2)
            ])
    
    filename = f"driver_performance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return generate_csv_response(filename, headers, rows)


def export_cost_per_km(truck_metrics):
    """Export cost per km analysis data to CSV."""
    headers = ['Truck', 'Fleet Type', 'Total KM', 'Fuel Cost', 
               'Tire Cost', 'Total Cost', 'Cost per KM']
    
    rows = []
    for metric in truck_metrics:
        rows.append([
            metric['truck'].plate_number,
            metric['truck'].get_fleet_type_display(),
            metric['total_km'],
            float(metric['fuel_cost']),
            float(metric['tire_cost']),
            float(metric['total_cost']),
            float(metric['cost_per_km'])
        ])
    
    filename = f"cost_per_km_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return generate_csv_response(filename, headers, rows)


def export_fleet_efficiency(efficiency_data):
    """Export fleet efficiency comparison data to CSV."""
    headers = ['Truck', 'Efficiency (km/l)', 'Total Distance (km)', 
               'Total Fuel (liters)', 'Trips', 'vs Fleet Average']
    
    rows = []
    for data in efficiency_data:
        rows.append([
            data['truck'].plate_number,
            float(data['efficiency']),
            data['total_distance'],
            float(data['total_fuel']),
            data['trips'],
            float(data.get('vs_fleet_avg', 0))
        ])
    
    filename = f"fleet_efficiency_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return generate_csv_response(filename, headers, rows)


def export_predictive_maintenance(maintenance_alerts):
    """Export predictive maintenance data to CSV."""
    headers = ['Truck', 'Priority', 'Alert Type', 'Description', 
               'Days Until', 'Recommendation', 'Estimated Cost']
    
    rows = []
    for alert in maintenance_alerts:
        rows.append([
            alert['truck'].plate_number,
            alert['priority'],
            alert['alert_type'],
            alert['description'],
            alert.get('days_until', ''),
            alert.get('recommendation', ''),
            alert.get('estimated_cost', '')
        ])
    
    filename = f"predictive_maintenance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return generate_csv_response(filename, headers, rows)