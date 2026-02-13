from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from fleet.models import Truck, Alert
from django.contrib.contenttypes.models import ContentType


class Command(BaseCommand):
    help = 'Check for document expiry alerts and create alerts for expiring documents'

    def handle(self, *args, **options):
        today = timezone.now().date()
        
        # Define expiry thresholds (days before expiry)
        thresholds = {
            'critical': 7,      # 7 days or less - Critical
            'warning': 30,      # 30 days or less - Warning
            'info': 60          # 60 days or less - Info
        }
        
        trucks = Truck.objects.all()
        alerts_created = 0
        
        for truck in trucks:
            # Check each document type
            document_fields = [
                ('fitness', truck.fitness_expiry, 'Fitness Certificate'),
                ('insurance', truck.insurance_expiry, 'Insurance'),
                ('pucc', truck.pucc_expiry, 'PUCC Certificate'),
                ('tax', truck.tax_expiry, 'Tax Certificate'),
                ('permit', truck.permit_expiry, 'Permit')
            ]
            
            for field_name, expiry_date, document_name in document_fields:
                if expiry_date:
                    days_until_expiry = (expiry_date - today).days
                    
                    # Only create alerts for documents that haven't expired yet
                    if days_until_expiry > 0:
                        alert_level = None
                        
                        if days_until_expiry <= thresholds['critical']:
                            alert_level = Alert.AlertLevel.CRITICAL
                        elif days_until_expiry <= thresholds['warning']:
                            alert_level = Alert.AlertLevel.WARNING
                        elif days_until_expiry <= thresholds['info']:
                            alert_level = Alert.AlertLevel.INFO
                        
                        if alert_level:
                            # Check if alert already exists for this document
                            existing_alert = Alert.objects.filter(
                                truck=truck,
                                alert_type=Alert.AlertType.DOCUMENT_EXPIRY,
                                status=Alert.AlertStatus.PENDING,
                                metadata__document_type=field_name
                            ).first()
                            
                            if not existing_alert:
                                Alert.objects.create(
                                    title=f"{document_name} Expiry Alert for {truck.plate_number}",
                                    alert_type=Alert.AlertType.DOCUMENT_EXPIRY,
                                    alert_level=alert_level,
                                    description=f"The {document_name} for truck {truck.plate_number} will expire on {expiry_date}. Only {days_until_expiry} days remaining.",
                                    truck=truck,
                                    related_content_type=ContentType.objects.get_for_model(truck).model,
                                    related_object_id=truck.id,
                                    metadata={
                                        'document_type': field_name,
                                        'expiry_date': str(expiry_date),
                                        'days_remaining': days_until_expiry,
                                        'truck_plate': truck.plate_number
                                    }
                                )
                                alerts_created += 1
                                self.stdout.write(self.style.SUCCESS(f"Created {alert_level} alert for {truck.plate_number} - {document_name} expires in {days_until_expiry} days"))
        
        self.stdout.write(self.style.SUCCESS(f"Document expiry check completed. {alerts_created} new alerts created."))