from django.db import models
from datetime import timedelta

from django.contrib.auth.models import User
from django.utils import timezone


class ActivityLog(models.Model):
    ACTION_TYPES = [
        ('FUEL_ENTRY', 'Fuel Entry'),
        ('COAL_ENTRY', 'Coal Entry'),
        ('MINING_ENTRY', 'Mining Entry'),
        ('TIRE_MOUNTED', 'Tire Mounted'),
        ('TIRE_UNMOUNTED', 'Tire Unmounted'),
        ('TIRE_REPAIRED', 'Tire Repaired'),
        ('TIRE_SCRAPPED', 'Tire Scrapped'),
        ('TRUCK_CREATED', 'Truck Created'),
        ('TRUCK_UPDATED', 'Truck Updated'),
        ('TRUCK_DELETED', 'Truck Deleted'),
        ('DRIVER_CREATED', 'Driver Created'),
        ('DRIVER_UPDATED', 'Driver Updated'),
        ('ALERT_DISMISSED', 'Alert Dismissed'),
    ]

    action = models.CharField(max_length=50, choices=ACTION_TYPES)
    description = models.CharField(max_length=255)
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='activities')
    object_type = models.CharField(max_length=50, null=True, blank=True)
    object_id = models.IntegerField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.get_action_display()} - {self.actor}"


class ComplianceAlert(models.Model):
    ALERT_TYPES = [
        ('DOCUMENT_EXPIRY', 'Document Expiry'),
        ('FUEL_EFFICIENCY', 'Fuel Efficiency Anomaly'),
        ('TIRE_COST', 'Tire Cost Alert'),
    ]

    alert_type = models.CharField(max_length=50, choices=ALERT_TYPES)
    message = models.TextField()
    severity = models.CharField(max_length=20, choices=[('LOW', 'LOW'), ('MEDIUM', 'MEDIUM'), ('HIGH', 'HIGH')])
    is_dismissed = models.BooleanField(default=False)
    dismissed_at = models.DateTimeField(null=True, blank=True)
    dismissed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_severity_display()}: {self.message}"


class ReportSchedule(models.Model):
    class ReportType(models.TextChoices):
        FUEL_CONSUMPTION = 'FUEL_CONSUMPTION', 'Fuel Consumption'
        TIRE_COST = 'TIRE_COST', 'Tire Cost Analysis'
        OPERATIONS_SUMMARY = 'OPERATIONS_SUMMARY', 'Operations Summary'
        FLEET_STATUS = 'FLEET_STATUS', 'Fleet Status'

    class Frequency(models.TextChoices):
        DAILY = 'DAILY', 'Daily'
        WEEKLY = 'WEEKLY', 'Weekly'
        MONTHLY = 'MONTHLY', 'Monthly'

    class OutputFormat(models.TextChoices):
        PDF = 'PDF', 'PDF'
        CSV = 'CSV', 'CSV'

    name = models.CharField(max_length=255)
    report_type = models.CharField(max_length=30, choices=ReportType.choices)
    frequency = models.CharField(max_length=10, choices=Frequency.choices, default=Frequency.WEEKLY)
    output_format = models.CharField(max_length=10, choices=OutputFormat.choices, default=OutputFormat.PDF)
    start_date = models.DateField(null=True, blank=True)
    filters = models.JSONField(default=dict, blank=True)
    email_recipients = models.TextField(blank=True, help_text='Comma-separated email addresses')
    is_active = models.BooleanField(default=True)
    next_run_at = models.DateTimeField(null=True, blank=True)
    last_run_at = models.DateTimeField(null=True, blank=True)
    last_output_path = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def schedule_next_run(self, from_date=None):
        reference = from_date or self.next_run_at or timezone.now()
        if self.frequency == self.Frequency.DAILY:
            self.next_run_at = reference + timedelta(days=1)
        elif self.frequency == self.Frequency.WEEKLY:
            self.next_run_at = reference + timedelta(weeks=1)
        else:
            self.next_run_at = reference + timedelta(days=30)

    def save(self, *args, **kwargs):
        if not self.next_run_at:
            base = self.start_date or timezone.now().date()
            self.next_run_at = timezone.make_aware(timezone.datetime.combine(base, timezone.datetime.min.time()))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.get_report_type_display()})"
