from django.contrib import admin

from .models import ActivityLog, ComplianceAlert, ReportSchedule


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


@admin.register(ReportSchedule)
class ReportScheduleAdmin(admin.ModelAdmin):
    list_display = ['name', 'report_type', 'frequency', 'output_format', 'is_active', 'next_run_at', 'last_run_at']
    list_filter = ['report_type', 'frequency', 'output_format', 'is_active']
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at', 'last_run_at']
