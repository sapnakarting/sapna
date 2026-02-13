from django.urls import path

from . import views

app_name = 'operations'

urlpatterns = [
    # Coal Log URLs
    path('coal/', views.CoalLogListView.as_view(), name='coal-log-list'),
    path('coal/<int:pk>/', views.CoalLogDetailView.as_view(), name='coal-log-detail'),
    path('coal/create/', views.CoalLogCreateView.as_view(), name='coal-log-create'),
    path('coal/<int:pk>/edit/', views.CoalLogUpdateView.as_view(), name='coal-log-update'),
    path('coal/<int:pk>/delete/', views.CoalLogDeleteView.as_view(), name='coal-log-delete'),
    path('coal/search/', views.CoalLogSearchView.as_view(), name='coal-log-search'),
    
    # Mining Log URLs
    path('mining/', views.MiningLogListView.as_view(), name='mining-log-list'),
    path('mining/<int:pk>/', views.MiningLogDetailView.as_view(), name='mining-log-detail'),
    path('mining/create/', views.MiningLogCreateView.as_view(), name='mining-log-create'),
    path('mining/<int:pk>/edit/', views.MiningLogUpdateView.as_view(), name='mining-log-update'),
    path('mining/<int:pk>/delete/', views.MiningLogDeleteView.as_view(), name='mining-log-delete'),
    path('mining/search/', views.MiningLogSearchView.as_view(), name='mining-log-search'),
    
    # API Endpoints
    path('api/coal/summary/', views.get_coal_summary, name='coal-summary-api'),
    path('api/mining/summary/', views.get_mining_summary, name='mining-summary-api'),
    path('api/calculate-net-weight/', views.calculate_net_weight, name='calculate-net-weight'),
    path('api/calculate-diesel-cost/', views.calculate_diesel_cost, name='calculate-diesel-cost'),
]
