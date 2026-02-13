from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from fleet.models import Truck, FuelLog, Alert
from django.contrib.contenttypes.models import ContentType
from decimal import Decimal


class Command(BaseCommand):
    help = 'Check for fuel efficiency alerts based on recent fuel consumption patterns'

    def handle(self, *args, **options):
        # Get date range for analysis (last 30 days)
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
        
        # Threshold for poor fuel efficiency (km per liter)
        # These thresholds can be adjusted based on truck type
        efficiency_thresholds = {
            '10_WHEEL': 2.5,    # 2.5 km/liter
            '14_WHEEL': 2.2,    # 2.2 km/liter  
            '16_WHEEL': 2.0,    # 2.0 km/liter
        }
        
        alerts_created = 0
        
        for truck in Truck.objects.all():
            # Get fuel logs for this truck in the date range
            fuel_logs = FuelLog.objects.filter(
                truck=truck,
                date__range=[start_date, end_date]
            ).order_by('date')
            
            if fuel_logs.count() < 2:
                continue  # Not enough data to calculate efficiency
            
            # Calculate total distance and total fuel
            total_distance = 0
            total_fuel = Decimal('0.00')
            
            for i in range(1, len(fuel_logs)):
                prev_log = fuel_logs[i-1]
                curr_log = fuel_logs[i]
                
                if prev_log.odometer and curr_log.odometer:
                    distance = curr_log.odometer - prev_log.odometer
                    if distance > 0:
                        total_distance += distance
                        total_fuel += curr_log.fuel_liters
            
            # Calculate fuel efficiency if we have data
            if total_distance > 0 and total_fuel > Decimal('0.00'):
                efficiency = float(total_distance) / float(total_fuel)  # km per liter
                
                # Get threshold for this truck type
                wheel_config = truck.wheel_config
                threshold = efficiency_thresholds.get(wheel_config, 2.0)  # Default threshold
                
                # Check if efficiency is below threshold
                if efficiency < threshold:
                    # Calculate how much below threshold
                    percentage_below = ((threshold - efficiency) / threshold) * 100
                    
                    # Determine alert level based on severity
                    if percentage_below > 30:  # More than 30% below threshold
                        alert_level = Alert.AlertLevel.CRITICAL
                    elif percentage_below > 15:  # 15-30% below threshold
                        alert_level = Alert.AlertLevel.WARNING
                    else:  # Less than 15% below threshold
                        alert_level = Alert.AlertLevel.INFO
                    
                    # Check if alert already exists
                    existing_alert = Alert.objects.filter(
                        truck=truck,
                        alert_type=Alert.AlertType.FUEL_EFFICIENCY,
                        status=Alert.AlertStatus.PENDING,
                        metadata__analysis_period=f"{start_date} to {end_date}"
                    ).first()
                    
                    if not existing_alert:
                        Alert.objects.create(
                            title=f"Poor Fuel Efficiency for {truck.plate_number}",
                            alert_type=Alert.AlertType.FUEL_EFFICIENCY,
                            alert_level=alert_level,
                            description=f"Truck {truck.plate_number} has poor fuel efficiency ({efficiency:.2f} km/liter) over the last 30 days, which is {percentage_below:.1f}% below the expected threshold of {threshold} km/liter.",
                            truck=truck,
                            related_content_type=ContentType.objects.get_for_model(truck).model,
                            related_object_id=truck.id,
                            metadata={
                                'efficiency_km_per_liter': efficiency,
                                'threshold_km_per_liter': threshold,
                                'percentage_below_threshold': percentage_below,
                                'total_distance_km': total_distance,
                                'total_fuel_liters': str(total_fuel),
                                'analysis_period': f"{start_date} to {end_date}",
                                'truck_plate': truck.plate_number,
                                'wheel_config': wheel_config
                            }
                        )
                        alerts_created += 1
                        self.stdout.write(self.style.SUCCESS(f"Created {alert_level} fuel efficiency alert for {truck.plate_number} - {efficiency:.2f} km/liter"))
        
        self.stdout.write(self.style.SUCCESS(f"Fuel efficiency check completed. {alerts_created} new alerts created."))