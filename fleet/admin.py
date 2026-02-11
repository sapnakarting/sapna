from django.contrib import admin

from .models import DailyOdoRegistry, Driver, FuelLog, TireInventory, Truck


@admin.register(Truck)
class TruckAdmin(admin.ModelAdmin):
    list_display = (
        "plate_number",
        "transporter_name",
        "wheel_config",
        "fleet_type",
        "mining_type",
        "status",
        "current_odometer",
    )
    list_filter = ("status", "fleet_type", "wheel_config", "mining_type")
    search_fields = ("plate_number", "transporter_name")


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ("name", "license_number", "phone", "status", "driver_type")
    list_filter = ("status", "driver_type")
    search_fields = ("name", "license_number", "phone")


@admin.register(FuelLog)
class FuelLogAdmin(admin.ModelAdmin):
    list_display = (
        "truck",
        "driver",
        "date",
        "entry_type",
        "fuel_liters",
        "diesel_price",
        "fuel_cost",
    )
    list_filter = ("entry_type", "date", "truck")
    search_fields = ("truck__plate_number", "driver__name")
    readonly_fields = ("fuel_cost", "attribution_date")


@admin.register(TireInventory)
class TireInventoryAdmin(admin.ModelAdmin):
    list_display = ("serial_number", "brand", "status", "truck", "position")
    list_filter = ("status", "truck")
    search_fields = ("serial_number", "truck__plate_number")


@admin.register(DailyOdoRegistry)
class DailyOdoRegistryAdmin(admin.ModelAdmin):
    list_display = (
        "truck",
        "date",
        "opening_odometer",
        "closing_odometer",
        "daily_mileage",
    )
    list_filter = ("date", "truck")
    search_fields = ("truck__plate_number",)
    readonly_fields = ("daily_mileage",)
