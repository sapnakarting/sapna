from decimal import Decimal

from django.conf import settings
from django.db import models

from .utils.expiry_helpers import get_expiry_color_code
from .utils.fuel_attribution import calculate_attribution_date
from .utils.tire_mileage import calculate_current_mileage as calculate_tire_mileage


class UserProfile(models.Model):
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Admin'
        FUEL_AGENT = 'FUEL_AGENT', 'Fuel Agent'

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='userprofile'
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.FUEL_AGENT)
    phone = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_admin(self):
        return self.role == self.Role.ADMIN

    def is_fuel_agent(self):
        return self.role == self.Role.FUEL_AGENT

    def __str__(self):
        return f"{self.user.username} - {self.role}"


class Truck(models.Model):
    class WheelConfig(models.TextChoices):
        TEN_WHEEL = "10_WHEEL", "10 Wheel"
        FOURTEEN_WHEEL = "14_WHEEL", "14 Wheel"
        SIXTEEN_WHEEL = "16_WHEEL", "16 Wheel"

    class FleetType(models.TextChoices):
        COAL = "COAL", "Coal"
        MINING = "MINING", "Mining"

    class MiningType(models.TextChoices):
        INTERNAL = "INTERNAL", "Internal"
        EXTERNAL = "EXTERNAL", "External"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        INACTIVE = "INACTIVE", "Inactive"
        MAINTENANCE = "MAINTENANCE", "Maintenance"

    plate_number = models.CharField(max_length=50, unique=True)
    transporter_name = models.CharField(max_length=255)
    wheel_config = models.CharField(max_length=10, choices=WheelConfig.choices)
    fleet_type = models.CharField(max_length=10, choices=FleetType.choices)
    mining_type = models.CharField(
        max_length=10, choices=MiningType.choices, blank=True, null=True
    )
    current_odometer = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=15, choices=Status.choices)
    remarks = models.TextField(blank=True)
    status_history = models.JSONField(default=list)
    fitness_expiry = models.DateField(null=True, blank=True)
    insurance_expiry = models.DateField(null=True, blank=True)
    pucc_expiry = models.DateField(null=True, blank=True)
    tax_expiry = models.DateField(null=True, blank=True)
    permit_expiry = models.DateField(null=True, blank=True)
    documents = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_expiry_color_code(self, expiry_date=None):
        if expiry_date is not None:
            return get_expiry_color_code(expiry_date)
        return {
            "fitness": get_expiry_color_code(self.fitness_expiry),
            "insurance": get_expiry_color_code(self.insurance_expiry),
            "pucc": get_expiry_color_code(self.pucc_expiry),
            "tax": get_expiry_color_code(self.tax_expiry),
            "permit": get_expiry_color_code(self.permit_expiry),
        }

    def __str__(self):
        return self.plate_number


class Driver(models.Model):
    class Status(models.TextChoices):
        ON_DUTY = "ON_DUTY", "On Duty"
        OFF_DUTY = "OFF_DUTY", "Off Duty"

    class DriverType(models.TextChoices):
        PERMANENT = "PERMANENT", "Permanent"
        TEMPORARY = "TEMPORARY", "Temporary"

    name = models.CharField(max_length=255)
    license_number = models.CharField(max_length=100, unique=True)
    phone = models.CharField(max_length=20)
    status = models.CharField(max_length=10, choices=Status.choices)
    driver_type = models.CharField(max_length=10, choices=DriverType.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class FuelLog(models.Model):
    class EntryType(models.TextChoices):
        FULL_TANK = "FULL_TANK", "Full Tank"
        PER_TRIP = "PER_TRIP", "Per Trip"

    truck = models.ForeignKey(Truck, on_delete=models.CASCADE, related_name="fuel_logs")
    driver = models.ForeignKey(Driver, on_delete=models.PROTECT)
    date = models.DateField()
    attribution_date = models.DateField(null=True, blank=True)
    entry_type = models.CharField(max_length=10, choices=EntryType.choices)
    odometer = models.PositiveIntegerField()
    previous_odometer = models.PositiveIntegerField(default=0)
    fuel_liters = models.DecimalField(max_digits=10, decimal_places=2)
    diesel_price = models.DecimalField(max_digits=10, decimal_places=2)
    fuel_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    verification_photos = models.JSONField(default=list)
    fueling_agent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    synced = models.BooleanField(default=True)
    synced_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def calculate_fuel_cost(self):
        return (self.fuel_liters or Decimal("0")) * (self.diesel_price or Decimal("0"))

    def save(self, *args, **kwargs):
        if self.date and self.entry_type:
            self.attribution_date = calculate_attribution_date(self.date, self.entry_type)
        self.fuel_cost = self.calculate_fuel_cost()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.truck} - {self.date}"


class TireInventory(models.Model):
    class Status(models.TextChoices):
        NEW = "NEW", "New"
        MOUNTED = "MOUNTED", "Mounted"
        SPARE = "SPARE", "Spare"
        REPAIR = "REPAIR", "Repair"
        SCRAPPED = "SCRAPPED", "Scrapped"

    serial_number = models.CharField(max_length=100, unique=True)
    brand = models.CharField(max_length=100)
    status = models.CharField(max_length=10, choices=Status.choices)
    truck = models.ForeignKey(
        Truck, on_delete=models.SET_NULL, null=True, blank=True, related_name="tires"
    )
    position = models.CharField(max_length=100)
    purchase_cost = models.DecimalField(max_digits=12, decimal_places=2)
    mounting_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    repair_costs = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    historical_mileage = models.PositiveIntegerField(default=0)
    mounted_at_odometer = models.PositiveIntegerField(null=True, blank=True)
    history = models.JSONField(default=list)
    scrap_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def calculate_current_mileage(self):
        current_truck_odo = self.truck.current_odometer if self.truck else None
        if current_truck_odo is None:
            return self.historical_mileage or 0
        return calculate_tire_mileage(self, current_truck_odo)

    def calculate_total_cost(self):
        return (self.purchase_cost or Decimal("0")) + (self.mounting_cost or Decimal("0")) + (
            self.repair_costs or Decimal("0")
        )

    def calculate_cost_per_km(self):
        mileage = self.calculate_current_mileage()
        if mileage <= 0:
            return Decimal("0.00")
        return self.calculate_total_cost() / Decimal(mileage)

    def __str__(self):
        return self.serial_number


class DailyOdoRegistry(models.Model):
    truck = models.ForeignKey(Truck, on_delete=models.CASCADE, related_name="daily_odos")
    date = models.DateField()
    opening_odometer = models.PositiveIntegerField()
    closing_odometer = models.PositiveIntegerField()
    daily_mileage = models.PositiveIntegerField(default=0)
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("truck", "date")

    def save(self, *args, **kwargs):
        if self.opening_odometer is not None and self.closing_odometer is not None:
            self.daily_mileage = max(self.closing_odometer - self.opening_odometer, 0)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.truck} - {self.date}"


class DieselPrice(models.Model):
    """Diesel price tracking by date"""
    date = models.DateField(unique=True)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"₹{self.price}/L on {self.date}"
