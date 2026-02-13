from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.DashboardView.as_view(), name='index'),
    path('metrics/', views.MetricsView.as_view(), name='metrics'),
    path('activity-feed/', views.ActivityFeedView.as_view(), name='activity-feed'),
    path('compliance-alerts/', views.ComplianceAlertView.as_view(), name='compliance-alerts'),
    path('dismiss-alert/', views.DismissAlertView.as_view(), name='dismiss-alert'),
]
