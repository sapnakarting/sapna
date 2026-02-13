from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from fleet.models import Alert
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Send email notifications for pending alerts to administrators'

    def handle(self, *args, **options):
        # Get all pending alerts that haven't been sent via email yet
        pending_alerts = Alert.objects.filter(
            status=Alert.AlertStatus.PENDING,
            email_sent=False
        ).order_by('-alert_level', 'created_at')  # Prioritize critical alerts
        
        if not pending_alerts.exists():
            self.stdout.write(self.style.SUCCESS('No pending alerts to send.'))
            return
        
        # Get all admin users
        admin_emails = []
        admin_users = User.objects.filter(userprofile__role='ADMIN')
        
        for user in admin_users:
            if user.email:
                admin_emails.append(user.email)
        
        if not admin_emails:
            self.stdout.write(self.style.WARNING('No admin email addresses found. Cannot send notifications.'))
            return
        
        # Group alerts by type for better email organization
        alerts_by_type = {}
        for alert in pending_alerts:
            alert_type = alert.get_alert_type_display()
            if alert_type not in alerts_by_type:
                alerts_by_type[alert_type] = []
            alerts_by_type[alert_type].append(alert)
        
        # Send email for each alert type
        emails_sent = 0
        for alert_type, alerts in alerts_by_type.items():
            subject = f"[SAPNA CARTING] {len(alerts)} {alert_type} Alerts Require Attention"
            
            # Build email content
            message_lines = []
            message_lines.append(f"Dear Administrator,")
            message_lines.append("")
            message_lines.append(f"There are {len(alerts)} {alert_type} alerts that require your attention:")
            message_lines.append("")
            
            for i, alert in enumerate(alerts, 1):
                message_lines.append(f"{i}. {alert.title}")
                message_lines.append(f"   Level: {alert.get_alert_level_display()}")
                message_lines.append(f"   Truck: {alert.truck.plate_number if alert.truck else 'N/A'}")
                message_lines.append(f"   Description: {alert.description}")
                message_lines.append("")
            
            message_lines.append("")
            message_lines.append("Please log in to the SAPNA CARTING system to view and manage these alerts:")
            message_lines.append(f"https://{settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'your-domain.com'}/fleet/alerts/")
            message_lines.append("")
            message_lines.append("Thank you,")
            message_lines.append("SAPNA CARTING Alert System")
            
            message = "\n".join(message_lines)
            
            try:
                # Send email
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=admin_emails,
                    fail_silently=False,
                )
                
                # Mark alerts as sent
                for alert in alerts:
                    alert.email_sent = True
                    alert.email_sent_at = timezone.now()
                    alert.save()
                
                emails_sent += 1
                self.stdout.write(self.style.SUCCESS(f"Sent {alert_type} alert notification to {len(admin_emails)} administrators"))
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to send {alert_type} alert notification: {str(e)}"))
        
        self.stdout.write(self.style.SUCCESS(f"Alert notification process completed. {emails_sent} emails sent for {pending_alerts.count()} alerts."))