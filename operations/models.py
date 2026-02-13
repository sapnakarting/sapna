from decimal import Decimal

from django.conf import settings
from django.db import models

from fleet.models import Truck


class CoalLog(models.Model):
    truck = models.ForeignKey(Truck, on_delete=models.CASCADE, related_name="coal_logs")
    date = models.DateField()
    pass_no = models.CharField(max_length=100)
    gross_weight = models.DecimalField(max_digits=12, decimal_places=2)
    tare_weight = models.DecimalField(max_digits=12, decimal_places=2)
    net_weight = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    diesel_liters = models.DecimalField(max_digits=10, decimal_places=2)
    diesel_rate = models.DecimalField(max_digits=10, decimal_places=2)
    diesel_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    origin_site = models.CharField(max_length=255)
    destination_site = models.CharField(max_length=255)
    trip_remarks = models.TextField(blank=True)
    diesel_remarks = models.TextField(blank=True)
    diesel_adjustment = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    air_adjustment = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    air_remarks = models.TextField(blank=True)
    trip_adjustment = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    documents = models.JSONField(default=list, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def calculate_net_weight(self):
        return (self.gross_weight or Decimal("0")) - (self.tare_weight or Decimal("0"))

    def calculate_diesel_cost(self):
        return (self.diesel_liters or Decimal("0")) * (self.diesel_rate or Decimal("0"))

    def calculate_total_adjustments(self):
        return (self.diesel_adjustment or Decimal("0")) + (self.air_adjustment or Decimal("0")) + (self.trip_adjustment or Decimal("0"))

    def save(self, *args, **kwargs):
        self.net_weight = self.calculate_net_weight()
        self.diesel_cost = self.calculate_diesel_cost()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.truck} - {self.date} - {self.pass_no}"


class MiningLog(models.Model):
    class LogType(models.TextChoices):
        DISPATCH = "DISPATCH", "Dispatch"
        PURCHASE = "PURCHASE", "Purchase"

    class MiningType(models.TextChoices):
        INTERNAL = "INTERNAL", "Internal"
        EXTERNAL = "EXTERNAL", "External"

    type = models.CharField(max_length=10, choices=LogType.choices)
    date = models.DateField()
    time = models.TimeField()
    chalan_no = models.CharField(max_length=100, unique=True)
    customer_name = models.CharField(max_length=255)
    truck = models.ForeignKey(Truck, on_delete=models.CASCADE, related_name="mining_logs")
    net = models.DecimalField(max_digits=12, decimal_places=2)
    material = models.CharField(max_length=100)
    mining_type = models.CharField(max_length=10, choices=MiningType.choices)
    chalan_document = models.FileField(upload_to="mining_chalans/", blank=True, null=True)
    ocr_processed = models.BooleanField(default=False)
    ocr_data = models.JSONField(blank=True, null=True)
    documents = models.JSONField(default=list, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-time', '-created_at']

    def __str__(self):
        return f"{self.chalan_no} - {self.customer_name}"

    def get_document_count(self):
        return len(self.documents) if self.documents else 0
