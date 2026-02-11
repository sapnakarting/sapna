from django.contrib import admin

from .models import CoalLog, MiningLog


@admin.register(CoalLog)
class CoalLogAdmin(admin.ModelAdmin):
    list_display = ("truck", "date", "origin_site", "destination_site", "net_weight")
    list_filter = ("date",)
    search_fields = ("pass_no", "truck__plate_number")
    readonly_fields = ("net_weight", "diesel_cost")


@admin.register(MiningLog)
class MiningLogAdmin(admin.ModelAdmin):
    list_display = ("truck", "date", "material", "net", "type", "mining_type")
    list_filter = ("date", "material", "type", "mining_type")
    search_fields = ("chalan_no", "customer_name", "truck__plate_number")
