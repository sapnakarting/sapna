# Dashboard Views & Metrics Implementation Summary

## Overview
This implementation creates the dashboard views, models, and utility functions for SAPNA CARTING's analytics and monitoring system.

## Files Created/Modified

### 1. Dashboard Models (`dashboard/models.py`)
Created two models for activity tracking and compliance alerts:

**ActivityLog:**
- Tracks all system activities (fuel entries, coal entries, mining entries, tire actions, truck/driver CRUD operations, alert dismissals)
- Fields: action, description, actor (User), object_type, object_id, metadata (JSON), timestamp
- Ordered by timestamp (newest first)

**ComplianceAlert:**
- Tracks compliance alerts (document expiry, fuel efficiency anomalies, tire cost alerts)
- Fields: alert_type, message, severity (LOW/MEDIUM/HIGH), is_dismissed, dismissed_at, dismissed_by (User), metadata (JSON), created_at
- Ordered by created_at (newest first)

### 2. Dashboard Views (`dashboard/views.py`)
Created five views for dashboard functionality:

**DashboardView:**
- Main dashboard landing page
- Calculates fleet metrics: total/active trucks, total/active drivers
- Calculates fuel metrics (last 30 days): total fuel liters, total fuel cost
- Calculates tire metrics: total/mounted/scrapped tires, total tire cost
- Calculates operations metrics (last 30 days): total coal and mining tons
- Shows compliance alerts: pending and high priority counts
- Shows recent activity feed (last 10 items)

**MetricsView:**
- API endpoint returning JSON data for charts
- Supports date range filtering via `period` query parameter (default: 30 days)
- Calculates fuel efficiency by truck:
  - Total fuel liters per truck
  - Total fuel cost per truck
  - Average fuel efficiency (km/liter)
- Calculates tire costs:
  - Total cost (purchase + mounting + repair)
  - Cost per km
- Returns operations statistics:
  - Coal: total trips, total tonnage, total diesel, total diesel cost
  - Mining: total trips, total tonnage

**ActivityFeedView:**
- Returns recent activities for HTMX partial template updates
- Shows last 10 activities by default

**ComplianceAlertView:**
- Returns JSON alert data for document expiries and fuel efficiency anomalies
- Checks document expiries (fitness, insurance, PUCC, tax, permit) within 7 days
- Uses get_expiry_color_code() from fleet.utils.expiry_helpers
- Checks fuel efficiency anomalies using SystemSettings.global_fuel_efficiency_benchmark
- Returns total alert count and detailed alert information

**DismissAlertView:**
- Handles alert dismissal via POST request
- Marks alerts as dismissed with timestamp and user
- Logs the dismissal activity in ActivityLog
- Returns JSON success/error responses

### 3. Dashboard Utils (`dashboard/utils/metrics.py`)
Created utility functions for metrics calculations:

**calculate_fuel_efficiency(fuel_logs):**
- Returns fuel efficiency metrics including:
  - Average km per liter
  - Total fuel consumed
  - Total fuel cost
  - Average cost per liter
- Handles empty queryset gracefully

**calculate_tire_metrics(tires):**
- Returns tire metrics including:
  - Total tire count
  - Total cost
  - Average cost per km
  - Average cost per tire
- Handles empty queryset gracefully

### 4. Dashboard Utils (`dashboard/utils/permissions.py`)
Created permission decorator:

**is_admin_required:**
- Decorator to restrict views to admin users only
- Redirects to dashboard if user is not an admin
- Wraps login_required decorator

### 5. Admin Configuration (`dashboard/admin.py`)
Registered dashboard models in admin interface:
- ActivityLogAdmin with filters for action and timestamp
- ComplianceAlertAdmin with filters for alert_type, severity, and is_dismissed

## Key Features

### Metrics Calculations
- **Fleet Metrics**: Active vs total counts for trucks and drivers
- **Fuel Metrics**: Total consumption and cost over configurable periods
- **Tire Metrics**: Inventory counts, costs, and per-km calculations
- **Operations Metrics**: Coal and mining tonnage, trip counts, diesel usage

### Compliance Monitoring
- **Document Expiry Alerts**: Automatic detection of expiring documents (within 7 days)
- **Fuel Efficiency Alerts**: Detects trucks below benchmark efficiency
- **Alert Dismissal**: Users can dismiss alerts with activity logging

### Activity Tracking
- Comprehensive activity log for all major system events
- Support for tracking object references (object_type, object_id)
- Flexible metadata storage via JSONField

### HTMX Integration
- Partial template support for activity feed updates
- JSON API endpoints for real-time data

## Technical Notes

1. **Fuel Efficiency Calculation**: Uses odometer delta (odometer - previous_odometer) for accurate efficiency calculation
2. **Graceful Error Handling**: ComplianceAlertView catches exceptions to prevent errors if SystemSettings is not configured
3. **Null-Safe Formatting**: All currency fields use conditional formatting to handle None values
4. **Pagination**: Activity feed limits to 10 items by default
5. **Date Range Support**: MetricsView supports configurable periods via query parameter

## Dependencies
- fleet.models: Truck, Driver, FuelLog, TireInventory
- operations.models: CoalLog, MiningLog
- settings_app.models: SystemSettings (for benchmarks)
- fleet.utils.expiry_helpers: get_expiry_color_code
- Django: TemplateView, LoginRequiredMixin, Sum aggregation

## Future Enhancements
- Add support for tire cost alerts
- Add pagination support for activity feed
- Add filtering options for activity feed
- Add date range picker for metrics
- Add alert notification preferences
- Add dashboard personalization
