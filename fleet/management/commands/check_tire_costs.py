from django.core.management.base import BaseCommand
from django.utils import timezone
from fleet.models import TireInventory, Alert, Truck
from django.contrib.contenttypes.models import ContentType
from decimal import Decimal


class Command(BaseCommand):
    help = 'Check for high tire costs and create alerts for tires with excessive cost per km'

    def handle(self, *args, **options):
        # Threshold for high tire cost per km (in INR per km)
        cost_thresholds = {
            '10_WHEEL': Decimal('15.00'),    # 15 INR per km
            '14_WHEEL': Decimal('18.00'),    # 18 INR per km
            '16_WHEEL': Decimal('20.00'),    # 20 INR per km
        }
        
        alerts_created = 0
        
        # Get all mounted tires
        mounted_tires = TireInventory.objects.filter(
            status=TireInventory.Status.MOUNTED
        ).select_related('truck')
        
        for tire in mounted_tires:
            if not tire.truck:
                continue
            
            # Calculate current cost per km
            cost_per_km = tire.calculate_cost_per_km()
            
            # Get threshold for this truck type
            wheel_config = tire.truck.wheel_config
            threshold = cost_thresholds.get(wheel_config, Decimal('18.00'))  # Default threshold
            
            # Check if cost per km exceeds threshold
            if cost_per_km > threshold:
                # Calculate how much above threshold
                percentage_above = ((cost_per_km - threshold) / threshold) * 100
                
                # Determine alert level based on severity
                if percentage_above > 50:  # More than 50% above threshold
                    alert_level = Alert.AlertLevel.CRITICAL
                elif percentage_above > 25:  # 25-50% above threshold
                    alert_level = Alert.AlertLevel.WARNING
                else:  # Less than 25% above threshold
                    alert_level = Alert.AlertLevel.INFO
                
                # Check if alert already exists
                existing_alert = Alert.objects.filter(
                    truck=tire.truck,
                    alert_type=Alert.AlertType.TIRE_COST,
                    status=Alert.AlertStatus.PENDING,
                    metadata__tire_serial=tire.serial_number
                ).first()
                
                if not existing_alert:
                    Alert.objects.create(
                        title=f"High Tire Cost for {tire.truck.plate_number} - {tire.serial_number}",
                        alert_type=Alert.AlertType.TIRE_COST,
                        alert_level=alert_level,
                        description=f"Tire {tire.serial_number} on truck {tire.truck.plate_number} has high cost per km (₹{cost_per_km:.2f}/km), which is {percentage_above:.1f}% above the threshold of ₹{threshold}/km.",
                        truck=tire.truck,
                        related_content_type=ContentType.objects.get_for_model(tire).model,
                        related_object_id=tire.id,
                        metadata={
                            'tire_serial': tire.serial_number,
                            'cost_per_km': str(cost_per_km),
                            'threshold_per_km': str(threshold),
                            'percentage_above_threshold': percentage_above,
                            'total_cost': str(tire.calculate_total_cost()),
                            'current_mileage': tire.calculate_current_mileage(),
                            'truck_plate': tire.truck.plate_number,
                            'wheel_config': wheel_config,
                            'position': tire.position
                        }
                    )
                    alerts_created += 1
                    self.stdout.write(self.style.SUCCESS(f"Created {alert_level} tire cost alert for {tire.truck.plate_number} - {tire.serial_number} (₹{cost_per_km:.2f}/km)"))
        
        self.stdout.write(self.style.SUCCESS(f"Tire cost check completed. {alerts_created} new alerts created."))