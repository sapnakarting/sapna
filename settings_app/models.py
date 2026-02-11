from django.db import models


class SystemSettings(models.Model):
    class CheckFrequency(models.TextChoices):
        DAILY = "DAILY", "Daily"
        WEEKLY = "WEEKLY", "Weekly"
        MONTHLY = "MONTHLY", "Monthly"

    compliance_alert_email = models.EmailField()
    global_fuel_efficiency_benchmark = models.DecimalField(
        max_digits=10, decimal_places=2, help_text="km/liter"
    )
    per_trip_diesel_benchmark = models.DecimalField(max_digits=10, decimal_places=2)
    per_tonnage_diesel_benchmark = models.DecimalField(max_digits=10, decimal_places=2)
    fleet_efficiency_threshold_min = models.DecimalField(max_digits=10, decimal_places=2)
    fleet_efficiency_threshold_max = models.DecimalField(max_digits=10, decimal_places=2)
    fuel_efficiency_check_frequency = models.CharField(
        max_length=10, choices=CheckFrequency.choices
    )
    last_efficiency_check = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.pk:
            self.pk = 1
        super().save(*args, **kwargs)

    def __str__(self):
        return "System Settings"
