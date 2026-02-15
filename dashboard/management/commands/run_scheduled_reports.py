from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.utils import timezone

from dashboard.models import ReportSchedule
from dashboard.utils.reporting import (
    generate_fleet_status_csv,
    generate_fleet_status_pdf,
    generate_fuel_consumption_csv,
    generate_fuel_consumption_pdf,
    generate_operations_summary_csv,
    generate_operations_summary_pdf,
    generate_tire_cost_csv,
    generate_tire_cost_pdf,
)


class Command(BaseCommand):
    help = 'Generate scheduled reports and update schedule run times.'

    def handle(self, *args, **options):
        now = timezone.now()
        schedules = ReportSchedule.objects.filter(is_active=True, next_run_at__lte=now)
        if not schedules.exists():
            self.stdout.write(self.style.SUCCESS('No scheduled reports due.'))
            return

        for schedule in schedules:
            try:
                self._run_schedule(schedule, now)
                self.stdout.write(self.style.SUCCESS(f"Generated report for {schedule.name}"))
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f"Failed to generate {schedule.name}: {exc}"))

    def _run_schedule(self, schedule, now):
        filters = schedule.filters or {}
        if schedule.report_type == ReportSchedule.ReportType.FUEL_CONSUMPTION:
            content, extension = self._build_fuel_report(schedule.output_format, filters)
        elif schedule.report_type == ReportSchedule.ReportType.TIRE_COST:
            content, extension = self._build_tire_report(schedule.output_format, filters)
        elif schedule.report_type == ReportSchedule.ReportType.OPERATIONS_SUMMARY:
            content, extension = self._build_operations_report(schedule.output_format, filters)
        else:
            content, extension = self._build_fleet_report(schedule.output_format, filters)

        filename = f"reports/{schedule.report_type.lower()}_{now.strftime('%Y%m%d_%H%M%S')}.{extension}"
        saved_path = default_storage.save(filename, ContentFile(content))

        schedule.last_run_at = now
        schedule.last_output_path = saved_path
        schedule.schedule_next_run(from_date=now)
        schedule.save(update_fields=['last_run_at', 'last_output_path', 'next_run_at', 'updated_at'])

    def _build_fuel_report(self, output_format, filters):
        if output_format == ReportSchedule.OutputFormat.CSV:
            return generate_fuel_consumption_csv(filters).encode('utf-8'), 'csv'
        return generate_fuel_consumption_pdf(filters), 'pdf'

    def _build_tire_report(self, output_format, filters):
        if output_format == ReportSchedule.OutputFormat.CSV:
            return generate_tire_cost_csv(filters).encode('utf-8'), 'csv'
        return generate_tire_cost_pdf(filters), 'pdf'

    def _build_operations_report(self, output_format, filters):
        if output_format == ReportSchedule.OutputFormat.CSV:
            return generate_operations_summary_csv(filters).encode('utf-8'), 'csv'
        return generate_operations_summary_pdf(filters), 'pdf'

    def _build_fleet_report(self, output_format, filters):
        if output_format == ReportSchedule.OutputFormat.CSV:
            return generate_fleet_status_csv(filters).encode('utf-8'), 'csv'
        return generate_fleet_status_pdf(filters), 'pdf'
