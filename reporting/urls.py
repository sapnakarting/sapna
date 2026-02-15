from django.urls import path
from . import views

app_name = 'reporting'

urlpatterns = [
    # Dashboard & Hub
    path('', views.ReportDashboardView.as_view(), name='dashboard'),
    path('analytics/', views.AnalyticsDashboardView.as_view(), name='analytics_dashboard'),
    
    # Fuel Reports
    path('fuel/', views.FuelConsumptionReportView.as_view(), name='fuel_report'),
    path('fuel/export/csv/', views.FuelConsumptionCSVExportView.as_view(), name='fuel_export_csv'),
    path('fuel/export/pdf/', views.FuelConsumptionPDFExportView.as_view(), name='fuel_export_pdf'),
    
    # Tire Reports
    path('tire/', views.TireCostReportView.as_view(), name='tire_report'),
    path('tire/export/csv/', views.TireCostCSVExportView.as_view(), name='tire_export_csv'),
    path('tire/export/pdf/', views.TireCostPDFExportView.as_view(), name='tire_export_pdf'),
    
    # Operations Reports
    path('operations/', views.OperationsSummaryReportView.as_view(), name='operations_report'),
    path('operations/export/csv/', views.OperationsCSVExportView.as_view(), name='operations_export_csv'),
    path('operations/export/pdf/', views.OperationsPDFExportView.as_view(), name='operations_export_pdf'),
    
    # Fleet Status Reports
    path('fleet-status/', views.FleetStatusReportView.as_view(), name='fleet_status_report'),
    path('fleet-status/export/csv/', views.FleetStatusCSVExportView.as_view(), name='fleet_status_export_csv'),
    path('fleet-status/export/pdf/', views.FleetStatusPDFExportView.as_view(), name='fleet_status_export_pdf'),
    
    # Driver Performance Reports
    path('driver-performance/', views.DriverPerformanceReportView.as_view(), name='driver_performance_report'),
    path('driver-performance/export/csv/', views.DriverPerformanceCSVExportView.as_view(), name='driver_performance_export_csv'),
    path('driver-performance/export/pdf/', views.DriverPerformancePDFExportView.as_view(), name='driver_performance_export_pdf'),
    
    # Cost Per KM Analysis
    path('cost-per-km/', views.CostPerKmAnalysisView.as_view(), name='cost_per_km'),
    path('cost-per-km/export/csv/', views.CostPerKmCSVExportView.as_view(), name='cost_per_km_export_csv'),
    path('cost-per-km/export/pdf/', views.CostPerKmPDFExportView.as_view(), name='cost_per_km_export_pdf'),
    
    # Fleet Efficiency Comparison
    path('efficiency/', views.FleetEfficiencyComparisonView.as_view(), name='fleet_efficiency'),
    path('efficiency/export/csv/', views.FleetEfficiencyCSVExportView.as_view(), name='fleet_efficiency_export_csv'),
    path('efficiency/export/pdf/', views.FleetEfficiencyPDFExportView.as_view(), name='fleet_efficiency_export_pdf'),
    
    # Driver Analytics
    path('driver-analytics/', views.DriverPerformanceAnalyticsView.as_view(), name='driver_analytics'),
    
    # Predictive Maintenance
    path('predictive-maintenance/', views.PredictiveMaintenanceView.as_view(), name='predictive_maintenance'),
    path('predictive-maintenance/export/csv/', views.PredictiveMaintenanceCSVExportView.as_view(), name='predictive_maintenance_export_csv'),
    path('predictive-maintenance/export/pdf/', views.PredictiveMaintenancePDFExportView.as_view(), name='predictive_maintenance_export_pdf'),
    
    # API Endpoints for Charts
    path('api/cost-per-km-data/', views.CostPerKmChartAPIView.as_view(), name='api_cost_per_km'),
    path('api/efficiency-data/', views.EfficiencyChartAPIView.as_view(), name='api_efficiency'),
    path('api/fuel-trend-data/', views.FuelTrendChartAPIView.as_view(), name='api_fuel_trend'),
    path('api/driver-performance-data/', views.DriverPerformanceChartAPIView.as_view(), name='api_driver_performance'),
]
