from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.DashboardView.as_view(), name='index'),
    path('metrics/', views.MetricsView.as_view(), name='metrics'),
    path('chart-data/', views.ChartDataView.as_view(), name='chart-data'),
    path('activity-feed/', views.ActivityFeedView.as_view(), name='activity-feed'),
    path('compliance-alerts/', views.ComplianceAlertView.as_view(), name='compliance-alerts'),
    path('dismiss-alert/', views.DismissAlertView.as_view(), name='dismiss-alert'),
    path('reports/', views.ReportIndexView.as_view(), name='report-index'),
    path('reports/fuel-consumption/', views.FuelConsumptionReportView.as_view(), name='fuel-consumption-report'),
    path('reports/fuel-consumption/pdf/', views.FuelConsumptionReportPDFView.as_view(), name='fuel-consumption-export-pdf'),
    path('reports/fuel-consumption/csv/', views.FuelConsumptionReportCSVView.as_view(), name='fuel-consumption-export-csv'),
    path('reports/tire-cost/', views.TireCostReportView.as_view(), name='tire-cost-report'),
    path('reports/tire-cost/pdf/', views.TireCostReportPDFView.as_view(), name='tire-cost-export-pdf'),
    path('reports/tire-cost/csv/', views.TireCostReportCSVView.as_view(), name='tire-cost-export-csv'),
    path('reports/operations-summary/', views.OperationsSummaryReportView.as_view(), name='operations-summary-report'),
    path('reports/operations-summary/pdf/', views.OperationsSummaryReportPDFView.as_view(), name='operations-summary-export-pdf'),
    path('reports/operations-summary/csv/', views.OperationsSummaryReportCSVView.as_view(), name='operations-summary-export-csv'),
    path('reports/fleet-status/', views.FleetStatusReportView.as_view(), name='fleet-status-report'),
    path('reports/fleet-status/pdf/', views.FleetStatusReportPDFView.as_view(), name='fleet-status-export-pdf'),
    path('reports/fleet-status/csv/', views.FleetStatusReportCSVView.as_view(), name='fleet-status-export-csv'),
    path('reports/schedules/', views.ReportScheduleListView.as_view(), name='report-schedule-list'),
    path('reports/schedules/create/', views.ReportScheduleCreateView.as_view(), name='report-schedule-create'),
]
