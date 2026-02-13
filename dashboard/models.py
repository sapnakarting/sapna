from django.db import models
from django.contrib.auth.models import User


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
