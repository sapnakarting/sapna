from django.urls import path
from . import views

app_name = 'fleet'

urlpatterns = [
    # Authentication
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),

    # User Management (Admin only)
    path('users/', views.UserListView.as_view(), name='user-list'),
    path('users/create/', views.UserCreateView.as_view(), name='user-create'),
    path('users/<int:pk>/edit/', views.UserUpdateView.as_view(), name='user-update'),
    path('users/<int:pk>/delete/', views.UserDeleteView.as_view(), name='user-delete'),

    # Truck Management
    path('trucks/', views.TruckListView.as_view(), name='truck-list'),
    path('trucks/<int:pk>/', views.TruckDetailView.as_view(), name='truck-detail'),
    path('trucks/create/', views.TruckCreateView.as_view(), name='truck-create'),
    path('trucks/<int:pk>/edit/', views.TruckUpdateView.as_view(), name='truck-update'),
    path('trucks/<int:pk>/delete/', views.TruckDeleteView.as_view(), name='truck-delete'),
    path('trucks/search/', views.TruckSearchView.as_view(), name='truck-search'),

    # Driver Management
    path('drivers/', views.DriverListView.as_view(), name='driver-list'),
    path('drivers/<int:pk>/', views.DriverDetailView.as_view(), name='driver-detail'),
    path('drivers/create/', views.DriverCreateView.as_view(), name='driver-create'),
    path('drivers/<int:pk>/edit/', views.DriverUpdateView.as_view(), name='driver-update'),
    path('drivers/<int:pk>/delete/', views.DriverDeleteView.as_view(), name='driver-delete'),

    # Fuel Operations
    path('fuel-logs/', views.FuelLogListView.as_view(), name='fuel-log-list'),
    path('fuel-logs/create/', views.FuelLogCreateView.as_view(), name='fuel-log-create'),
    path('fuel-logs/<int:pk>/', views.FuelLogDetailView.as_view(), name='fuel-log-detail'),
    path('fuel-logs/<int:pk>/edit/', views.FuelLogUpdateView.as_view(), name='fuel-log-update'),
    path('fuel-logs/<int:pk>/delete/', views.FuelLogDeleteView.as_view(), name='fuel-log-delete'),
    
    # Fuel Sync and Utilities
    path('fuel-logs/sync/', views.sync_now, name='fuel-sync-now'),
    path('fuel-logs/diesel-price/', views.get_today_diesel_price, name='fuel-diesel-price'),
    path('fuel-logs/update-diesel-price/', views.update_diesel_price, name='fuel-update-diesel-price'),

    # Tire Inventory Management
    path('tires/', views.TireInventoryListView.as_view(), name='tire-list'),
    path('tires/<int:pk>/', views.TireInventoryDetailView.as_view(), name='tire-detail'),
    path('tires/create/', views.TireInventoryCreateView.as_view(), name='tire-create'),
    path('tires/<int:pk>/edit/', views.TireInventoryUpdateView.as_view(), name='tire-update'),
    path('tires/<int:pk>/delete/', views.TireInventoryDeleteView.as_view(), name='tire-delete'),
    path('tires/truck/<int:pk>/', views.TireTruckView.as_view(), name='tire-truck'),
    path('tires/search/', views.TireSearchView.as_view(), name='tire-search'),
    path('tires/<int:pk>/action/', views.TireActionView.as_view(), name='tire-action'),
]
