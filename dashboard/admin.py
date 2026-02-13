from django.contrib import admin

from .models import ActivityLog, ComplianceAlert


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ['action', 'actor', 'timestamp', 'object_type']
    list_filter = ['action', 'timestamp']
    search_fields = ['description', 'actor__username']
    readonly_fields = ['timestamp']


@admin.register(ComplianceAlert)
class ComplianceAlertAdmin(admin.ModelAdmin):
    list_display = ['alert_type', 'severity', 'is_dismissed', 'created_at']
    list_filter = ['alert_type', 'severity', 'is_dismissed']
    search_fields = ['message']
    readonly_fields = ['created_at']
