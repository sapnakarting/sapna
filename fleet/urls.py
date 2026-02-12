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
]
