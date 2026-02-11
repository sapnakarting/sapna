from django.contrib import admin

from .models import SystemSettings


@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        if SystemSettings.objects.exists():
            return False
        return super().has_add_permission(request)
