from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from io import BytesIO, StringIO
import csv

from django.db.models import Sum
from django.utils import timezone
from django.utils.dateparse import parse_date

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from fleet.models import Driver, FuelLog, TireInventory, Truck
from operations.models import CoalLog, MiningLog
from dashboard.models import ComplianceAlert

MAX_PDF_ROWS = 200


@dataclass
class ReportSection:
    title: str
    table: list[list[str]] | None = None
    note: str | None = None


def format_currency(value: Decimal | float | int | None) -> str:
    amount = Decimal(value or 0)
    return f"₹{amount:,.2f}"


def normalize_filters(filters: dict | None) -> dict:
    normalized = dict(filters or {})
    for key in ['date_from', 'date_to', 'start_date']:
        value = normalized.get(key)
        if isinstance(value, str):
            parsed = parse_date(value)
            if parsed:
                normalized[key] = parsed
    truck_value = normalized.get('truck')
    if truck_value and not isinstance(truck_value, Truck):
        try:
            normalized['truck'] = Truck.objects.get(pk=truck_value)
        except Truck.DoesNotExist:
            normalized['truck'] = None
    return normalized


def _apply_date_filters(queryset, date_from, date_to, field_name='date'):
    if date_from:
        queryset = queryset.filter(**{f"{field_name}__gte": date_from})
    if date_to:
        queryset = queryset.filter(**{f"{field_name}__lte": date_to})
    return queryset


def get_fuel_consumption_data(filters: dict | None) -> dict:
    filters = normalize_filters(filters)
    queryset = FuelLog.objects.select_related('truck', 'driver').order_by('-date', '-created_at')

    queryset = _apply_date_filters(queryset, filters.get('date_from'), filters.get('date_to'))

    truck = filters.get('truck')
    if truck:
        queryset = queryset.filter(truck=truck)

    entries = []
    total_liters = Decimal('0')
    total_cost = Decimal('0')
    total_distance = 0
    truck_summary = {}

    for log in queryset:
        distance = max((log.odometer or 0) - (log.previous_odometer or 0), 0)
        liters = log.fuel_liters or Decimal('0')
        cost = log.fuel_cost or Decimal('0')
        efficiency = Decimal(distance) / liters if liters else Decimal('0')

        entries.append({
            'date': log.date,
            'truck': log.truck,
            'driver': log.driver,
            'entry_type': log.entry_type,
            'liters': liters,
            'cost': cost,
            'distance': distance,
            'efficiency': efficiency,
        })

        total_liters += liters
        total_cost += cost
        total_distance += distance

        summary = truck_summary.setdefault(log.truck_id, {
            'truck': log.truck,
            'total_liters': Decimal('0'),
            'total_cost': Decimal('0'),
            'total_distance': 0,
            'entries': 0,
        })
        summary['total_liters'] += liters
        summary['total_cost'] += cost
        summary['total_distance'] += distance
        summary['entries'] += 1

    avg_efficiency = Decimal(total_distance) / total_liters if total_liters else Decimal('0')

    for summary in truck_summary.values():
        summary['avg_efficiency'] = (
            Decimal(summary['total_distance']) / summary['total_liters']
            if summary['total_liters'] else Decimal('0')
        )

    return {
        'entries': entries,
        'summary': {
            'total_liters': total_liters,
            'total_cost': total_cost,
            'total_distance': total_distance,
            'avg_efficiency': avg_efficiency,
        },
        'truck_summary': truck_summary,
    }


def get_tire_cost_data(filters: dict | None) -> dict:
    filters = normalize_filters(filters)
    queryset = TireInventory.objects.select_related('truck').order_by('-created_at')

    status = filters.get('status')
    if status:
        queryset = queryset.filter(status=status)

    truck = filters.get('truck')
    if truck:
        queryset = queryset.filter(truck=truck)

    queryset = _apply_date_filters(queryset, filters.get('date_from'), filters.get('date_to'), 'created_at__date')

    tires = []
    total_cost = Decimal('0')
    total_mileage = 0

    status_counts = {status: 0 for status, _ in TireInventory.Status.choices}

    for tire in queryset:
        current_mileage = tire.calculate_current_mileage()
        total_cost_value = tire.calculate_total_cost()
        cost_per_km = tire.calculate_cost_per_km()

        tires.append({
            'tire': tire,
            'current_mileage': current_mileage,
            'total_cost': total_cost_value,
            'cost_per_km': cost_per_km,
        })

        total_cost += total_cost_value
        total_mileage += current_mileage
        status_counts[tire.status] = status_counts.get(tire.status, 0) + 1

    avg_cost_per_km = total_cost / Decimal(total_mileage) if total_mileage else Decimal('0')

    return {
        'tires': tires,
        'summary': {
            'total_tires': queryset.count(),
            'total_cost': total_cost,
            'total_mileage': total_mileage,
            'avg_cost_per_km': avg_cost_per_km,
        },
        'status_counts': status_counts,
    }


def get_operations_summary_data(filters: dict | None) -> dict:
    filters = normalize_filters(filters)
    coal_logs = CoalLog.objects.select_related('truck').order_by('-date', '-created_at')
    mining_logs = MiningLog.objects.select_related('truck').order_by('-date', '-time')

    coal_logs = _apply_date_filters(coal_logs, filters.get('date_from'), filters.get('date_to'))
    mining_logs = _apply_date_filters(mining_logs, filters.get('date_from'), filters.get('date_to'))

    truck = filters.get('truck')
    if truck:
        coal_logs = coal_logs.filter(truck=truck)
        mining_logs = mining_logs.filter(truck=truck)

    coal_summary = {
        'total_trips': coal_logs.count(),
        'total_net_weight': coal_logs.aggregate(Sum('net_weight'))['net_weight__sum'] or Decimal('0'),
        'total_diesel_liters': coal_logs.aggregate(Sum('diesel_liters'))['diesel_liters__sum'] or Decimal('0'),
        'total_diesel_cost': coal_logs.aggregate(Sum('diesel_cost'))['diesel_cost__sum'] or Decimal('0'),
    }

    mining_summary = {
        'total_entries': mining_logs.count(),
        'total_tonnage': mining_logs.aggregate(Sum('net'))['net__sum'] or Decimal('0'),
        'dispatch_count': mining_logs.filter(type='DISPATCH').count(),
        'purchase_count': mining_logs.filter(type='PURCHASE').count(),
    }

    return {
        'coal_logs': list(coal_logs),
        'mining_logs': list(mining_logs),
        'coal_summary': coal_summary,
        'mining_summary': mining_summary,
    }


def get_fleet_status_data(filters: dict | None) -> dict:
    filters = normalize_filters(filters)
    trucks = Truck.objects.all().order_by('plate_number')

    status = filters.get('status')
    if status:
        trucks = trucks.filter(status=status)

    fleet_type = filters.get('fleet_type')
    if fleet_type:
        trucks = trucks.filter(fleet_type=fleet_type)

    mining_type = filters.get('mining_type')
    if mining_type:
        trucks = trucks.filter(mining_type=mining_type)

    summary = {
        'total_trucks': trucks.count(),
        'active_trucks': trucks.filter(status='ACTIVE').count(),
        'inactive_trucks': trucks.filter(status='INACTIVE').count(),
        'maintenance_trucks': trucks.filter(status='MAINTENANCE').count(),
    }

    driver_summary = {
        'total_drivers': Driver.objects.count(),
        'on_duty': Driver.objects.filter(status='ON_DUTY').count(),
        'off_duty': Driver.objects.filter(status='OFF_DUTY').count(),
    }

    tire_summary = {
        'total_tires': TireInventory.objects.count(),
        'mounted_tires': TireInventory.objects.filter(status='MOUNTED').count(),
        'spare_tires': TireInventory.objects.filter(status='SPARE').count(),
        'repair_tires': TireInventory.objects.filter(status='REPAIR').count(),
        'scrapped_tires': TireInventory.objects.filter(status='SCRAPPED').count(),
    }

    upcoming_docs = []
    today = timezone.now().date()
    for truck in trucks:
        for label, date_value in [
            ('Fitness', truck.fitness_expiry),
            ('Insurance', truck.insurance_expiry),
            ('PUCC', truck.pucc_expiry),
            ('Tax', truck.tax_expiry),
            ('Permit', truck.permit_expiry),
        ]:
            if date_value:
                days_until = (date_value - today).days
                if 0 <= days_until <= 30:
                    upcoming_docs.append({
                        'truck': truck,
                        'document': label,
                        'expiry_date': date_value,
                        'days_until': days_until,
                    })

    upcoming_docs.sort(key=lambda item: item['expiry_date'])

    return {
        'trucks': list(trucks),
        'summary': summary,
        'driver_summary': driver_summary,
        'tire_summary': tire_summary,
        'pending_alerts': ComplianceAlert.objects.filter(is_dismissed=False).count(),
        'upcoming_docs': upcoming_docs,
    }


def build_pdf_report(title: str, sections: list[ReportSection]) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )
    styles = getSampleStyleSheet()
    story = [
        Paragraph(title, styles['Title']),
        Paragraph(f"Generated on {timezone.now().strftime('%d %b %Y %H:%M')}", styles['Normal']),
        Spacer(1, 12),
    ]

    table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f2937')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ])

    for section in sections:
        story.append(Paragraph(section.title, styles['Heading2']))
        if section.note:
            story.append(Paragraph(section.note, styles['BodyText']))
        if section.table:
            table = Table(section.table, repeatRows=1)
            table.setStyle(table_style)
            story.append(table)
        story.append(Spacer(1, 12))

    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf


def generate_fuel_consumption_pdf(filters: dict | None) -> bytes:
    data = get_fuel_consumption_data(filters)
    summary = data['summary']

    summary_table = [[
        'Total Liters',
        'Total Cost',
        'Total Distance',
        'Avg Efficiency (km/l)',
    ], [
        f"{summary['total_liters']:.2f}",
        format_currency(summary['total_cost']),
        f"{summary['total_distance']} km",
        f"{summary['avg_efficiency']:.2f}",
    ]]

    entries = data['entries'][:MAX_PDF_ROWS]
    detail_table = [[
        'Date', 'Truck', 'Driver', 'Entry Type', 'Liters', 'Cost', 'Distance', 'Efficiency'
    ]]
    for entry in entries:
        detail_table.append([
            entry['date'].strftime('%d %b %Y'),
            entry['truck'].plate_number,
            entry['driver'].name,
            entry['entry_type'].replace('_', ' ').title(),
            f"{entry['liters']:.2f}",
            format_currency(entry['cost']),
            f"{entry['distance']} km",
            f"{entry['efficiency']:.2f}",
        ])

    sections = [
        ReportSection(title='Fuel Consumption Summary', table=summary_table),
        ReportSection(
            title='Fuel Log Details',
            table=detail_table,
            note='Showing latest entries.' if len(data['entries']) > MAX_PDF_ROWS else None,
        ),
    ]

    return build_pdf_report('Fuel Consumption Report', sections)


def generate_tire_cost_pdf(filters: dict | None) -> bytes:
    data = get_tire_cost_data(filters)
    summary = data['summary']

    summary_table = [[
        'Total Tires', 'Total Cost', 'Total Mileage', 'Avg Cost/Km'
    ], [
        str(summary['total_tires']),
        format_currency(summary['total_cost']),
        f"{summary['total_mileage']} km",
        format_currency(summary['avg_cost_per_km']),
    ]]

    detail_table = [[
        'Serial', 'Brand', 'Status', 'Truck', 'Mileage', 'Total Cost', 'Cost/Km'
    ]]

    for entry in data['tires'][:MAX_PDF_ROWS]:
        tire = entry['tire']
        detail_table.append([
            tire.serial_number,
            tire.brand,
            tire.status.title(),
            tire.truck.plate_number if tire.truck else '—',
            f"{entry['current_mileage']} km",
            format_currency(entry['total_cost']),
            format_currency(entry['cost_per_km']),
        ])

    return build_pdf_report('Tire Cost Analysis Report', [
        ReportSection(title='Tire Cost Summary', table=summary_table),
        ReportSection(
            title='Tire Cost Breakdown',
            table=detail_table,
            note='Showing latest entries.' if len(data['tires']) > MAX_PDF_ROWS else None,
        ),
    ])


def generate_operations_summary_pdf(filters: dict | None) -> bytes:
    data = get_operations_summary_data(filters)
    coal_summary = data['coal_summary']
    mining_summary = data['mining_summary']

    coal_summary_table = [[
        'Total Trips', 'Total Net Weight', 'Diesel Liters', 'Diesel Cost'
    ], [
        str(coal_summary['total_trips']),
        f"{coal_summary['total_net_weight']:.2f}",
        f"{coal_summary['total_diesel_liters']:.2f}",
        format_currency(coal_summary['total_diesel_cost']),
    ]]

    coal_table = [[
        'Date', 'Truck', 'Pass No', 'Net Weight', 'Diesel Liters', 'Diesel Cost'
    ]]
    for log in data['coal_logs'][:MAX_PDF_ROWS]:
        coal_table.append([
            log.date.strftime('%d %b %Y'),
            log.truck.plate_number,
            log.pass_no,
            f"{log.net_weight:.2f}",
            f"{log.diesel_liters:.2f}",
            format_currency(log.diesel_cost),
        ])

    mining_summary_table = [[
        'Total Entries', 'Total Tonnage', 'Dispatch Count', 'Purchase Count'
    ], [
        str(mining_summary['total_entries']),
        f"{mining_summary['total_tonnage']:.2f}",
        str(mining_summary['dispatch_count']),
        str(mining_summary['purchase_count']),
    ]]

    mining_table = [[
        'Date', 'Truck', 'Chalan', 'Customer', 'Type', 'Net Tonnage'
    ]]
    for log in data['mining_logs'][:MAX_PDF_ROWS]:
        mining_table.append([
            log.date.strftime('%d %b %Y'),
            log.truck.plate_number,
            log.chalan_no,
            log.customer_name,
            log.type.title(),
            f"{log.net:.2f}",
        ])

    return build_pdf_report('Operations Summary Report', [
        ReportSection(title='Coal Operations Summary', table=coal_summary_table),
        ReportSection(
            title='Coal Log Details',
            table=coal_table,
            note='Showing latest entries.' if len(data['coal_logs']) > MAX_PDF_ROWS else None,
        ),
        ReportSection(title='Mining Operations Summary', table=mining_summary_table),
        ReportSection(
            title='Mining Log Details',
            table=mining_table,
            note='Showing latest entries.' if len(data['mining_logs']) > MAX_PDF_ROWS else None,
        ),
    ])


def generate_fleet_status_pdf(filters: dict | None) -> bytes:
    data = get_fleet_status_data(filters)

    summary_table = [[
        'Total Trucks', 'Active', 'Inactive', 'Maintenance', 'Pending Alerts'
    ], [
        str(data['summary']['total_trucks']),
        str(data['summary']['active_trucks']),
        str(data['summary']['inactive_trucks']),
        str(data['summary']['maintenance_trucks']),
        str(data['pending_alerts']),
    ]]

    driver_table = [[
        'Total Drivers', 'On Duty', 'Off Duty'
    ], [
        str(data['driver_summary']['total_drivers']),
        str(data['driver_summary']['on_duty']),
        str(data['driver_summary']['off_duty']),
    ]]

    tire_table = [[
        'Total Tires', 'Mounted', 'Spare', 'Repair', 'Scrapped'
    ], [
        str(data['tire_summary']['total_tires']),
        str(data['tire_summary']['mounted_tires']),
        str(data['tire_summary']['spare_tires']),
        str(data['tire_summary']['repair_tires']),
        str(data['tire_summary']['scrapped_tires']),
    ]]

    truck_table = [[
        'Truck', 'Status', 'Fleet Type', 'Transporter', 'Current ODO'
    ]]
    for truck in data['trucks'][:MAX_PDF_ROWS]:
        truck_table.append([
            truck.plate_number,
            truck.status.title(),
            truck.fleet_type.title(),
            truck.transporter_name,
            f"{truck.current_odometer} km",
        ])

    doc_table = [[
        'Truck', 'Document', 'Expiry Date', 'Days Until'
    ]]
    for item in data['upcoming_docs'][:MAX_PDF_ROWS]:
        doc_table.append([
            item['truck'].plate_number,
            item['document'],
            item['expiry_date'].strftime('%d %b %Y'),
            str(item['days_until']),
        ])

    return build_pdf_report('Fleet Status Report', [
        ReportSection(title='Fleet Overview', table=summary_table),
        ReportSection(title='Driver Coverage', table=driver_table),
        ReportSection(title='Tire Inventory Summary', table=tire_table),
        ReportSection(
            title='Truck Status Details',
            table=truck_table,
            note='Showing current fleet status.' if len(data['trucks']) > MAX_PDF_ROWS else None,
        ),
        ReportSection(
            title='Upcoming Document Expirations (Next 30 Days)',
            table=doc_table,
            note='No documents expiring in the next 30 days.' if len(data['upcoming_docs']) == 0 else None,
        ),
    ])


def generate_fuel_consumption_csv(filters: dict | None) -> str:
    data = get_fuel_consumption_data(filters)
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(['Date', 'Truck', 'Driver', 'Entry Type', 'Liters', 'Cost', 'Distance', 'Efficiency'])
    for entry in data['entries']:
        writer.writerow([
            entry['date'],
            entry['truck'].plate_number,
            entry['driver'].name,
            entry['entry_type'],
            f"{entry['liters']:.2f}",
            f"{entry['cost']:.2f}",
            entry['distance'],
            f"{entry['efficiency']:.2f}",
        ])
    return buffer.getvalue()


def generate_tire_cost_csv(filters: dict | None) -> str:
    data = get_tire_cost_data(filters)
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(['Serial', 'Brand', 'Status', 'Truck', 'Mileage', 'Total Cost', 'Cost per Km'])
    for entry in data['tires']:
        tire = entry['tire']
        writer.writerow([
            tire.serial_number,
            tire.brand,
            tire.status,
            tire.truck.plate_number if tire.truck else '',
            entry['current_mileage'],
            f"{entry['total_cost']:.2f}",
            f"{entry['cost_per_km']:.2f}",
        ])
    return buffer.getvalue()


def generate_operations_summary_csv(filters: dict | None) -> str:
    data = get_operations_summary_data(filters)
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        'Category', 'Date', 'Truck', 'Reference', 'Customer/Origin', 'Type', 'Net Weight', 'Diesel Liters', 'Diesel Cost'
    ])

    for log in data['coal_logs']:
        writer.writerow([
            'Coal',
            log.date,
            log.truck.plate_number,
            log.pass_no,
            log.origin_site,
            'Trip',
            f"{log.net_weight:.2f}",
            f"{log.diesel_liters:.2f}",
            f"{log.diesel_cost:.2f}",
        ])

    for log in data['mining_logs']:
        writer.writerow([
            'Mining',
            log.date,
            log.truck.plate_number,
            log.chalan_no,
            log.customer_name,
            log.type,
            f"{log.net:.2f}",
            '',
            '',
        ])

    return buffer.getvalue()


def generate_fleet_status_csv(filters: dict | None) -> str:
    data = get_fleet_status_data(filters)
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(['Truck', 'Status', 'Fleet Type', 'Mining Type', 'Transporter', 'Current Odometer'])
    for truck in data['trucks']:
        writer.writerow([
            truck.plate_number,
            truck.status,
            truck.fleet_type,
            truck.mining_type or '',
            truck.transporter_name,
            truck.current_odometer,
        ])
    return buffer.getvalue()
