from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.views import LogoutView as DjangoLogoutView
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse

from django.db.models import Sum, Count
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods

from .forms import LoginForm, UserCreationForm, TruckForm, TruckSearchForm, DriverForm, FuelLogForm, DieselPriceForm, TireInventoryForm, TireActionForm, TireSearchForm, DailyOdoRegistryForm, DailyOdoRegistrySearchForm, BulkDailyOdoEntryForm, BulkDailyOdoEntryFormSet
from .models import UserProfile, Truck, Driver, FuelLog, TireInventory, DieselPrice, DailyOdoRegistry
from .utils.permissions import is_admin_required, is_fuel_agent_required, AdminRequiredMixin


class LoginView(View):
    template_name = 'fleet/login.html'

    def get(self, request):
        if request.user.is_authenticated:
            return self.get_redirect_url(request.user)
        form = LoginForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = LoginForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data.get('user')
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            return self.get_redirect_url(user)
        return render(request, self.template_name, {'form': form})

    def get_redirect_url(self, user):
        if hasattr(user, 'userprofile'):
            if user.userprofile.role == 'ADMIN':
                return redirect('dashboard:index')
            elif user.userprofile.role == 'FUEL_AGENT':
                return redirect('dashboard:index')
        return redirect('dashboard:index')


class LogoutView(DjangoLogoutView):
    http_method_names = ['post']

    def dispatch(self, request, *args, **kwargs):
        messages.success(request, 'You have been logged out successfully.')
        return super().dispatch(request, *args, **kwargs)


class UserListView(ListView):
    model = User
    template_name = 'fleet/user_list.html'
    context_object_name = 'users'
    paginate_by = 20

    @is_admin_required
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_queryset(self):
        queryset = User.objects.select_related('userprofile').all()
        role_filter = self.request.GET.get('role')
        if role_filter:
            queryset = queryset.filter(userprofile__role=role_filter)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['breadcrumbs'] = [
            {'name': 'Users', 'url': None}
        ]
        return context


class UserCreateView(CreateView):
    model = User
    form_class = UserCreationForm
    template_name = 'fleet/user_form.html'
    success_url = '/fleet/users/'

    @is_admin_required
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def form_valid(self, form):
        user = form.save()
        UserProfile.objects.create(
            user=user,
            role=form.cleaned_data['role'],
            phone=form.cleaned_data['phone']
        )
        messages.success(self.request, f'User "{user.username}" created successfully.')
        return super().form_valid(form)


class UserUpdateView(UpdateView):
    model = User
    form_class = UserCreationForm
    template_name = 'fleet/user_form.html'
    success_url = '/fleet/users/'

    @is_admin_required
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        user = self.get_object()
        if hasattr(user, 'userprofile'):
            initial['role'] = user.userprofile.role
            initial['phone'] = user.userprofile.phone
        return initial

    def form_valid(self, form):
        user = form.save(commit=False)
        # Only update password if provided
        if form.cleaned_data['password1']:
            user.set_password(form.cleaned_data['password1'])
        user.save()

        profile = user.userprofile
        profile.role = form.cleaned_data['role']
        profile.phone = form.cleaned_data['phone']
        profile.save()

        messages.success(self.request, f'User "{user.username}" updated successfully.')
        return super().form_valid(form)


class UserDeleteView(DeleteView):
    model = User
    template_name = 'fleet/user_delete.html'
    success_url = '/fleet/users/'
    context_object_name = 'user'

    @is_admin_required
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def delete(self, request, *args, **kwargs):
        user = self.get_object()
        messages.success(self.request, f'User "{user.username}" deleted successfully.')
        return super().delete(request, *args, **kwargs)


class TruckListView(LoginRequiredMixin, ListView):
    model = Truck
    template_name = 'fleet/truck_list.html'
    context_object_name = 'trucks'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Truck.objects.all().order_by('-created_at')
        # Apply search filter
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                plate_number__icontains=search
            ) | queryset.filter(
                transporter_name__icontains=search
            )
        # Apply fleet type filter
        fleet_type = self.request.GET.get('fleet_type', '')
        if fleet_type:
            queryset = queryset.filter(fleet_type=fleet_type)
        # Apply status filter
        status = self.request.GET.get('status', '')
        if status:
            queryset = queryset.filter(status=status)
        # Apply wheel config filter
        wheel_config = self.request.GET.get('wheel_config', '')
        if wheel_config:
            queryset = queryset.filter(wheel_config=wheel_config)
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = TruckSearchForm(self.request.GET)
        context['breadcrumbs'] = [
            {'name': 'Fleet', 'url': None},
            {'name': 'Trucks', 'url': None}
        ]
        return context


class TruckDetailView(LoginRequiredMixin, DetailView):
    model = Truck
    template_name = 'fleet/truck_detail.html'
    context_object_name = 'truck'
    pk_url_kwarg = 'pk'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        truck = self.object
        # Get recent fuel logs for this truck
        context['recent_fuel_logs'] = FuelLog.objects.filter(
            truck=truck
        ).order_by('-created_at')[:5]
        # Get current tires mounted on this truck
        context['current_tires'] = TireInventory.objects.filter(
            truck=truck, status='MOUNTED'
        )
        context['breadcrumbs'] = [
            {'name': 'Fleet', 'url': None},
            {'name': 'Trucks', 'url': reverse('fleet:truck-list')},
            {'name': truck.plate_number, 'url': None}
        ]
        return context


class TruckCreateView(LoginRequiredMixin, CreateView):
    model = Truck
    form_class = TruckForm
    template_name = 'fleet/truck_form.html'
    success_url = reverse_lazy('truck-list')

    def form_valid(self, form):
        truck = form.save(commit=False)
        truck.created_by = self.request.user
        truck.save()
        truck.status_history.append({
            'status': truck.status,
            'remarks': f'Truck created with status {truck.status}',
            'date': timezone.now().isoformat()
        })
        truck.save()
        messages.success(self.request, f'Truck {truck.plate_number} created successfully!')
        return super().form_valid(form)


class TruckUpdateView(LoginRequiredMixin, UpdateView):
    model = Truck
    form_class = TruckForm
    template_name = 'fleet/truck_form.html'
    success_url = reverse_lazy('truck-list')

    def form_valid(self, form):
        truck = form.save(commit=False)
        old_status = Truck.objects.get(pk=self.object.pk).status
        if old_status != truck.status:
            truck.status_history.append({
                'status': truck.status,
                'remarks': f'Status changed from {old_status} to {truck.status}',
                'date': timezone.now().isoformat()
            })
        truck.save()
        messages.success(self.request, f'Truck {truck.plate_number} updated successfully!')
        return super().form_valid(form)


class TruckDeleteView(LoginRequiredMixin, DeleteView):
    model = Truck
    template_name = 'fleet/truck_delete.html'
    success_url = reverse_lazy('truck-list')

    def delete(self, request, *args, **kwargs):
        truck = self.get_object()
        plate_number = truck.plate_number
        messages.success(self.request, f'Truck {plate_number} deleted successfully!')
        return super().delete(request, *args, **kwargs)


class TruckSearchView(LoginRequiredMixin, ListView):
    model = Truck
    template_name = 'fleet/truck_list_partial.html'
    context_object_name = 'trucks'

    def get_queryset(self):
        queryset = Truck.objects.all().order_by('-created_at')
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                plate_number__icontains=search
            ) | queryset.filter(
                transporter_name__icontains=search
            )
        fleet_type = self.request.GET.get('fleet_type', '')
        if fleet_type:
            queryset = queryset.filter(fleet_type=fleet_type)
        status = self.request.GET.get('status', '')
        if status:
            queryset = queryset.filter(status=status)
        wheel_config = self.request.GET.get('wheel_config', '')
        if wheel_config:
            queryset = queryset.filter(wheel_config=wheel_config)
        return queryset


class DriverListView(LoginRequiredMixin, ListView):
    model = Driver
    template_name = 'fleet/driver_list.html'
    context_object_name = 'drivers'
    paginate_by = 20

    def get_queryset(self):
        queryset = Driver.objects.all().order_by('-created_at')
        status = self.request.GET.get('status', '')
        if status:
            queryset = queryset.filter(status=status)
        driver_type = self.request.GET.get('driver_type', '')
        if driver_type:
            queryset = queryset.filter(driver_type=driver_type)
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                name__icontains=search
            ) | queryset.filter(
                license_number__icontains=search
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['breadcrumbs'] = [
            {'name': 'Fleet', 'url': None},
            {'name': 'Drivers', 'url': None}
        ]
        return context


class DriverDetailView(LoginRequiredMixin, DetailView):
    model = Driver
    template_name = 'fleet/driver_detail.html'
    context_object_name = 'driver'
    pk_url_kwarg = 'pk'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        driver = self.object
        context['recent_fuel_logs'] = FuelLog.objects.filter(
            driver=driver
        ).order_by('-created_at')[:5]
        context['breadcrumbs'] = [
            {'name': 'Fleet', 'url': None},
            {'name': 'Drivers', 'url': reverse('fleet:driver-list')},
            {'name': driver.name, 'url': None}
        ]
        return context


class DriverCreateView(LoginRequiredMixin, CreateView):
    model = Driver
    form_class = DriverForm
    template_name = 'fleet/driver_form.html'
    success_url = reverse_lazy('driver-list')

    def form_valid(self, form):
        driver = form.save(commit=False)
        driver.created_by = self.request.user
        driver.save()
        messages.success(self.request, f'Driver {driver.name} created successfully!')
        return super().form_valid(form)


class DriverUpdateView(LoginRequiredMixin, UpdateView):
    model = Driver
    form_class = DriverForm
    template_name = 'fleet/driver_form.html'
    success_url = reverse_lazy('driver-list')

    def form_valid(self, form):
        driver = form.save()
        messages.success(self.request, f'Driver {driver.name} updated successfully!')
        return super().form_valid(form)


class DriverDeleteView(LoginRequiredMixin, DeleteView):
    model = Driver
    template_name = 'fleet/driver_delete.html'
    success_url = reverse_lazy('driver-list')

    def delete(self, request, *args, **kwargs):
        driver = self.get_object()
        name = driver.name
        messages.success(self.request, f'Driver {name} deleted successfully!')
        return super().delete(request, *args, **kwargs)


# Fuel Log Views

class FuelLogListView(LoginRequiredMixin, ListView):
    model = FuelLog
    template_name = 'fleet/fuel_log_list.html'
    context_object_name = 'fuel_logs'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = FuelLog.objects.all().select_related('truck', 'driver').order_by('-created_at')
        # Apply filters
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
        truck_id = self.request.GET.get('truck')
        if truck_id:
            queryset = queryset.filter(truck_id=truck_id)
        entry_type = self.request.GET.get('entry_type')
        if entry_type:
            queryset = queryset.filter(entry_type=entry_type)
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['date_from'] = self.request.GET.get('date_from')
        context['date_to'] = self.request.GET.get('date_to')
        context['truck_filter'] = self.request.GET.get('truck')
        context['entry_type_filter'] = self.request.GET.get('entry_type')
        context['pending_sync_count'] = FuelLog.objects.filter(synced=False).count()
        context['breadcrumbs'] = [
            {'name': 'Fleet', 'url': None},
            {'name': 'Fuel Logs', 'url': None}
        ]
        return context


class FuelLogCreateView(LoginRequiredMixin, CreateView):
    model = FuelLog
    form_class = FuelLogForm
    template_name = 'fleet/fuel_log_form.html'
    success_url = reverse_lazy('fuel-log-list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        truck_id = self.request.GET.get('truck')
        if truck_id:
            truck = Truck.objects.get(pk=truck_id)
            kwargs['initial'] = {
                'previous_odometer': truck.current_odometer,
                'truck': truck,
            }
        return kwargs
    
    def form_valid(self, form):
        fuel_log = form.save()
        messages.success(self.request, f'Fuel log entry created for {fuel_log.truck.plate_number}!')
        return super().form_valid(form)


class FuelLogDetailView(LoginRequiredMixin, DetailView):
    model = FuelLog
    template_name = 'fleet/fuel_log_detail.html'
    context_object_name = 'fuel_log'
    pk_url_kwarg = 'pk'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        fuel_log = self.object
        context['breadcrumbs'] = [
            {'name': 'Fleet', 'url': None},
            {'name': 'Fuel Logs', 'url': reverse('fleet:fuel-log-list')},
            {'name': f'Entry {fuel_log.id}', 'url': None}
        ]
        return context


class FuelLogUpdateView(LoginRequiredMixin, UpdateView):
    model = FuelLog
    form_class = FuelLogForm
    template_name = 'fleet/fuel_log_form.html'
    success_url = reverse_lazy('fuel-log-list')
    
    def form_valid(self, form):
        fuel_log = form.save()
        messages.success(self.request, f'Fuel log updated for {fuel_log.truck.plate_number}!')
        return super().form_valid(form)


class FuelLogDeleteView(LoginRequiredMixin, DeleteView):
    model = FuelLog
    template_name = 'fleet/fuel_log_delete.html'
    success_url = reverse_lazy('fuel-log-list')
    
    def delete(self, request, *args, **kwargs):
        fuel_log = self.get_object()
        messages.success(self.request, f'Fuel log deleted for {fuel_log.truck.plate_number}!')
        return super().delete(request, *args, **kwargs)


@is_fuel_agent_required
def sync_now(request):
    """Sync all pending fuel entries now"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)
    
    pending_logs = FuelLog.objects.filter(synced=False)
    count = pending_logs.count()
    
    if count == 0:
        return JsonResponse({'success': True, 'count': 0, 'message': 'No pending entries to sync'})
    
    # Sync all pending logs
    for log in pending_logs:
        log.synced = True
        log.synced_at = timezone.now()
        log.save()
    
    messages.success(request, f'{count} fuel entries synced successfully!')
    
    return JsonResponse({
        'success': True,
        'count': count,
        'pending_count': FuelLog.objects.filter(synced=False).count()
    })


@is_admin_required
def update_diesel_price(request):
    """Update diesel price for a date"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)
    
    form = DieselPriceForm(request.POST)
    if not form.is_valid():
        return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    
    price = form.cleaned_data['price']
    date = form.cleaned_data['date']
    
    # Update or create diesel price
    diesel_price, created = DieselPrice.objects.update_or_create(
        date=date,
        defaults={'price': price}
    )
    
    # If updating today's price, delete old prices
    if not created and timezone.now().date() != date:
        DieselPrice.objects.filter(date__gt=date).delete()
    
    return JsonResponse({
        'success': True,
        'price': float(price),
        'message': f'Diesel price for {date} updated to ₹{price}'
    })


# Tire Inventory Views

class TireInventoryListView(LoginRequiredMixin, ListView):
    model = TireInventory
    template_name = 'fleet/tire_list.html'
    context_object_name = 'tires'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = TireInventory.objects.all().select_related('truck').order_by('-created_at')
        
        # Apply search filter
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                serial_number__icontains=search
            ) | queryset.filter(
                brand__icontains=search
            ) | queryset.filter(
                truck__plate_number__icontains=search
            )
        
        # Apply status filter
        status_filter = self.request.GET.get('status', '')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Apply truck filter
        truck_filter = self.request.GET.get('truck', '')
        if truck_filter:
            queryset = queryset.filter(truck_id=truck_filter)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Calculate quick stats
        context['total_tires'] = TireInventory.objects.count()
        context['mounted_count'] = TireInventory.objects.filter(status='MOUNTED').count()
        context['spare_count'] = TireInventory.objects.filter(status='SPARE').count()
        context['repair_count'] = TireInventory.objects.filter(status='REPAIR').count()
        context['scrapped_count'] = TireInventory.objects.filter(status='SCRAPPED').count()

        # Calculate average cost per km
        total_cost = TireInventory.objects.aggregate(
            total=Sum('purchase_cost') + Sum('mounting_cost') + Sum('repair_costs')
        )['total'] or 0

        total_mileage = 0
        for tire in TireInventory.objects.all():
            total_mileage += tire.calculate_current_mileage()

        if total_mileage > 0:
            context['avg_cost_per_km'] = total_cost / total_mileage
        else:
            context['avg_cost_per_km'] = 0

        context['search_form'] = TireSearchForm(self.request.GET)
        context['breadcrumbs'] = [
            {'name': 'Fleet', 'url': None},
            {'name': 'Tire Inventory', 'url': None}
        ]

        return context


class TireInventoryDetailView(LoginRequiredMixin, DetailView):
    model = TireInventory
    template_name = 'fleet/tire_detail.html'
    context_object_name = 'tire'
    pk_url_kwarg = 'pk'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tire = self.object

        # Calculate metrics
        context['total_cost'] = tire.calculate_total_cost()
        context['cost_per_km'] = tire.calculate_cost_per_km()
        context['current_mileage'] = tire.calculate_current_mileage()

        # Get truck information if mounted
        if tire.truck:
            context['truck_info'] = {
                'plate_number': tire.truck.plate_number,
                'transporter': tire.truck.transporter_name,
                'wheel_config': tire.truck.wheel_config,
                'current_odometer': tire.truck.current_odometer
            }

        # Sort history chronologically
        context['history'] = sorted(tire.history, key=lambda x: x.get('date', ''))

        context['breadcrumbs'] = [
            {'name': 'Fleet', 'url': None},
            {'name': 'Tire Inventory', 'url': reverse('fleet:tire-list')},
            {'name': tire.serial_number, 'url': None}
        ]

        return context


class TireInventoryCreateView(LoginRequiredMixin, CreateView):
    model = TireInventory
    form_class = TireInventoryForm
    template_name = 'fleet/tire_form.html'
    success_url = reverse_lazy('tire-list')
    
    def get_initial(self):
        initial = super().get_initial()
        initial['status'] = 'NEW'
        return initial
    
    def form_valid(self, form):
        tire = form.save(commit=False)
        tire.status = 'NEW'
        
        # Add initial history entry
        tire.history = [{
            'status': 'NEW',
            'date': timezone.now().isoformat(),
            'reason': 'Tire created'
        }]
        
        tire.save()
        messages.success(self.request, f'Tire {tire.serial_number} created successfully!')
        return super().form_valid(form)


class TireInventoryUpdateView(LoginRequiredMixin, UpdateView):
    model = TireInventory
    form_class = TireInventoryForm
    template_name = 'fleet/tire_form.html'
    success_url = reverse_lazy('tire-list')
    
    def form_valid(self, form):
        tire = form.save(commit=False)
        old_status = TireInventory.objects.get(pk=self.object.pk).status
        
        # Track status changes in history
        if old_status != tire.status:
            event = {
                'status': tire.status,
                'date': timezone.now().isoformat(),
                'reason': f'Status changed from {old_status} to {tire.status}'
            }
            
            if tire.status == 'MOUNTED':
                event['odometer'] = tire.mounted_at_odometer
                event['reason'] = f'Mounted at position {tire.position} on {tire.truck.plate_number}'
            elif tire.status == 'REPAIR':
                event['reason'] = f'Repair done. Cost: ₹{tire.repair_costs}'
            elif tire.status == 'SCRAPPED':
                event['reason'] = f'Scrapped. Reason: {tire.scrap_reason}'
            
            tire.history.append(event)
        
        tire.save()
        messages.success(self.request, f'Tire {tire.serial_number} updated successfully!')
        return super().form_valid(form)


class TireInventoryDeleteView(LoginRequiredMixin, DeleteView):
    model = TireInventory
    template_name = 'fleet/tire_delete.html'
    success_url = reverse_lazy('tire-list')
    context_object_name = 'tire'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tire = self.object
        
        # Calculate metrics for deletion confirmation
        context['total_cost'] = tire.calculate_total_cost()
        context['cost_per_km'] = tire.calculate_cost_per_km()
        context['current_mileage'] = tire.calculate_current_mileage()
        context['history_count'] = len(tire.history)
        
        return context
    
    def delete(self, request, *args, **kwargs):
        tire = self.get_object()
        serial_number = tire.serial_number
        messages.success(self.request, f'Tire {serial_number} deleted successfully!')
        return super().delete(request, *args, **kwargs)


class TireTruckView(LoginRequiredMixin, DetailView):
    model = Truck
    template_name = 'fleet/tire_truck_visual.html'
    context_object_name = 'truck'
    pk_url_kwarg = 'pk'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        truck = self.object
        
        # Get all tires for this truck
        context['tires'] = TireInventory.objects.filter(truck=truck)
        
        # Define wheel positions based on configuration
        wheel_positions = []
        if truck.wheel_config == '10_WHEEL':
            wheel_positions = [
                'FL', 'FR',
                'R1 Left Outside', 'R1 Left Inside', 'R1 Right Inside', 'R1 Right Outside',
                'R2 Left Outside', 'R2 Left Inside', 'R2 Right Inside', 'R2 Right Outside'
            ]
        elif truck.wheel_config == '14_WHEEL':
            wheel_positions = [
                'FL', 'FR',
                'R1 Left Outside', 'R1 Left Inside', 'R1 Right Inside', 'R1 Right Outside',
                'R2 Left Outside', 'R2 Left Inside', 'R2 Right Inside', 'R2 Right Outside',
                'R3 Left Outside', 'R3 Left Inside', 'R3 Right Inside', 'R3 Right Outside'
            ]
        elif truck.wheel_config == '16_WHEEL':
            wheel_positions = [
                'FL', 'FR',
                'R1 Left Outside', 'R1 Left Inside', 'R1 Right Inside', 'R1 Right Outside',
                'R2 Left Outside', 'R2 Left Inside', 'R2 Right Inside', 'R2 Right Outside',
                'R3 Left Outside', 'R3 Left Inside', 'R3 Right Inside', 'R3 Right Outside',
                'R4 Left Outside', 'R4 Left Inside', 'R4 Right Inside', 'R4 Right Outside'
            ]
        
        context['wheel_positions'] = wheel_positions
        
        # Create position map for easy lookup
        position_map = {}
        for tire in context['tires']:
            position_map[tire.position] = {
                'tire': tire,
                'status': tire.status,
                'serial': tire.serial_number
            }
        
        context['position_map'] = position_map
        
        # Status color legend
        context['status_colors'] = {
            'MOUNTED': 'bg-green-500',
            'SPARE': 'bg-amber-500',
            'REPAIR': 'bg-red-500',
            'SCRAPPED': 'bg-gray-500',
            'NEW': 'bg-blue-500'
        }
        
        return context


class TireSearchView(LoginRequiredMixin, ListView):
    model = TireInventory
    template_name = 'fleet/tire_list_partial.html'
    context_object_name = 'tires'
    
    def get_queryset(self):
        queryset = TireInventory.objects.all().select_related('truck').order_by('-created_at')
        
        # Apply search filter
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                serial_number__icontains=search
            ) | queryset.filter(
                brand__icontains=search
            ) | queryset.filter(
                truck__plate_number__icontains=search
            )
        
        # Apply status filter
        status_filter = self.request.GET.get('status', '')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Apply truck filter
        truck_filter = self.request.GET.get('truck', '')
        if truck_filter:
            queryset = queryset.filter(truck_id=truck_filter)
        
        return queryset


class TireActionView(LoginRequiredMixin, View):
    def get(self, request, pk):
        tire = get_object_or_404(TireInventory, pk=pk)
        action = request.GET.get('action', '')
        trucks = Truck.objects.all()
        
        context = {
            'tire': tire,
            'action': action,
            'trucks': trucks
        }
        
        return render(request, 'fleet/tire_action_modal.html', context)
    
    def post(self, request, pk):
        tire = get_object_or_404(TireInventory, pk=pk)
        form = TireActionForm(request.POST)
        
        if not form.is_valid():
            return JsonResponse({
                'success': False,
                'errors': form.errors
            }, status=400)
        
        action = form.cleaned_data['action']
        old_status = tire.status
        
        # Process different actions
        if action == 'MOUNT':
            tire.status = 'MOUNTED'
            tire.truck = form.cleaned_data['truck']
            tire.position = form.cleaned_data['position']
            tire.mounted_at_odometer = form.cleaned_data['truck_odometer']
            
            # Update truck odometer
            if tire.truck:
                tire.truck.current_odometer = form.cleaned_data['truck_odometer']
                tire.truck.save()
            
            # Add history entry
            tire.history.append({
                'status': 'MOUNTED',
                'date': timezone.now().isoformat(),
                'odometer': form.cleaned_data['truck_odometer'],
                'reason': f'Mounted at position {form.cleaned_data["position"]} on {tire.truck.plate_number}'
            })
            
        elif action == 'UNMOUNT':
            tire.status = 'SPARE'
            old_truck = tire.truck
            old_position = tire.position
            tire.truck = None
            tire.position = ''
            tire.mounted_at_odometer = None
            
            # Add history entry
            tire.history.append({
                'status': 'SPARE',
                'date': timezone.now().isoformat(),
                'reason': f'Unmounted from position {old_position} on {old_truck.plate_number}'
            })
            
        elif action == 'REPAIR':
            tire.status = 'REPAIR'
            repair_cost = form.cleaned_data.get('repair_cost', 0)
            tire.repair_costs = (tire.repair_costs or 0) + repair_cost
            
            # Add history entry
            tire.history.append({
                'status': 'REPAIR',
                'date': timezone.now().isoformat(),
                'reason': f'Repair done. Cost: ₹{repair_cost}',
                'cost': repair_cost
            })
            
        elif action == 'SCRAP':
            tire.status = 'SCRAPPED'
            tire.scrap_reason = form.cleaned_data['scrap_reason']
            
            # Add history entry
            tire.history.append({
                'status': 'SCRAPPED',
                'date': timezone.now().isoformat(),
                'reason': f'Scrapped. Reason: {form.cleaned_data["scrap_reason"]}'
            })
        
        tire.save()
        
        # Calculate updated metrics
        total_cost = tire.calculate_total_cost()
        cost_per_km = tire.calculate_cost_per_km()
        current_mileage = tire.calculate_current_mileage()
        
        return JsonResponse({
            'success': True,
            'tire_id': tire.pk,
            'serial_number': tire.serial_number,
            'status': tire.status,
            'total_cost': float(total_cost),
            'cost_per_km': float(cost_per_km),
            'current_mileage': current_mileage,
            'message': f'Tire {action.lower()}ed successfully'
        })


@is_fuel_agent_required
def get_today_diesel_price(request):
    """Get today's diesel price for form autocomplete"""
    today = timezone.now().date()
    today_price = DieselPrice.objects.filter(date=today).first()
    
    if today_price:
        return JsonResponse({'price': float(today_price.price)})
    else:
        return JsonResponse({'price': 0.0})


# Daily Odometer Registry Views

class DailyOdoRegistryListView(LoginRequiredMixin, ListView):
    model = DailyOdoRegistry
    template_name = 'fleet/daily_odo_list.html'
    context_object_name = 'entries'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = DailyOdoRegistry.objects.all().select_related('truck').order_by('-date', 'truck')
        
        # Apply filters
        truck_id = self.request.GET.get('truck')
        if truck_id:
            queryset = queryset.filter(truck_id=truck_id)
        
        date_from = self.request.GET.get('date_from')
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        
        date_to = self.request.GET.get('date_to')
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
        
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(remarks__icontains=search)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = DailyOdoRegistrySearchForm(self.request.GET)
        
        # Calculate stats
        today = timezone.now().date()
        active_trucks = Truck.objects.filter(status='ACTIVE').count()
        today_entries = DailyOdoRegistry.objects.filter(date=today).count()
        
        context['stats'] = {
            'active_trucks': active_trucks,
            'today_entries': today_entries,
            'completion_pct': (today_entries / active_trucks * 100) if active_trucks > 0 else 0
        }
        
        # Get trucks without entries today
        trucks_with_entries = DailyOdoRegistry.objects.filter(date=today).values_list('truck_id', flat=True)
        context['missing_trucks'] = Truck.objects.filter(status='ACTIVE').exclude(id__in=trucks_with_entries)
        
        context['breadcrumbs'] = [
            {'name': 'Fleet', 'url': None},
            {'name': 'Daily Odometer', 'url': None}
        ]
        
        return context


class DailyOdoRegistryDetailView(LoginRequiredMixin, DetailView):
    model = DailyOdoRegistry
    template_name = 'fleet/daily_odo_detail.html'
    context_object_name = 'entry'
    pk_url_kwarg = 'pk'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        entry = self.object
        
        # Get previous and next entries for the same truck
        context['previous_entry'] = DailyOdoRegistry.objects.filter(
            truck=entry.truck, date__lt=entry.date
        ).order_by('-date').first()
        
        context['next_entry'] = DailyOdoRegistry.objects.filter(
            truck=entry.truck, date__gt=entry.date
        ).order_by('date').first()
        
        # Get truck's odometer history
        context['odometer_history'] = DailyOdoRegistry.objects.filter(
            truck=entry.truck
        ).order_by('date')[:10]
        
        context['breadcrumbs'] = [
            {'name': 'Fleet', 'url': None},
            {'name': 'Daily Odometer', 'url': reverse('fleet:daily-odo-list')},
            {'name': f'Entry {entry.id}', 'url': None}
        ]
        
        return context


class DailyOdoRegistryCreateView(AdminRequiredMixin, CreateView):
    model = DailyOdoRegistry
    form_class = DailyOdoRegistryForm
    template_name = 'fleet/daily_odo_form.html'
    success_url = reverse_lazy('fleet:daily-odo-list')
    
    def get_initial(self):
        initial = super().get_initial()
        truck_id = self.request.GET.get('truck')
        if truck_id:
            try:
                truck = Truck.objects.get(pk=truck_id)
                initial['truck'] = truck
                initial['opening_odometer'] = truck.current_odometer
            except Truck.DoesNotExist:
                pass
        return initial
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Daily odometer entry created for {form.instance.truck.plate_number}!')
        return response


class DailyOdoRegistryUpdateView(AdminRequiredMixin, UpdateView):
    model = DailyOdoRegistry
    form_class = DailyOdoRegistryForm
    template_name = 'fleet/daily_odo_form.html'
    
    def get_success_url(self):
        return reverse('fleet:daily-odo-detail', kwargs={'pk': self.object.pk})
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs
    
    def form_valid(self, form):
        # Check if closing odometer is being changed
        old_closing = DailyOdoRegistry.objects.get(pk=self.object.pk).closing_odometer
        new_closing = form.instance.closing_odometer
        
        if old_closing != new_closing:
            messages.warning(self.request, f'Truck odometer will be updated to {new_closing} km.')
        
        response = super().form_valid(form)
        messages.success(self.request, f'Daily odometer entry updated for {form.instance.truck.plate_number}!')
        return response


class DailyOdoRegistryDeleteView(AdminRequiredMixin, DeleteView):
    model = DailyOdoRegistry
    template_name = 'fleet/daily_odo_delete.html'
    success_url = reverse_lazy('fleet:daily-odo-list')
    context_object_name = 'entry'
    
    def delete(self, request, *args, **kwargs):
        entry = self.get_object()
        messages.warning(request, f'Truck odometer will not be automatically adjusted. You may need to update it manually.')
        messages.success(request, f'Daily odometer entry deleted for {entry.truck.plate_number}!')
        return super().delete(request, *args, **kwargs)


class BulkDailyOdoEntryView(AdminRequiredMixin, View):
    template_name = 'fleet/daily_odo_bulk_form.html'
    
    def get(self, request):
        # Get all active trucks
        active_trucks = Truck.objects.filter(status='ACTIVE').order_by('plate_number')
        
        # Create formset with one form per truck
        BulkFormSet = formset_factory(
            BulkDailyOdoEntryForm, 
            formset=BulkDailyOdoEntryFormSet,
            extra=0
        )
        
        forms = []
        for truck in active_trucks:
            form = BulkDailyOdoEntryForm(truck=truck)
            forms.append(form)
        
        formset = BulkFormSet(initial=[form.initial for form in forms])
        
        context = {
            'formset': formset,
            'trucks': active_trucks,
            'date': timezone.now().date()
        }
        
        return render(request, self.template_name, context)
    
    def post(self, request):
        date_str = request.POST.get('date')
        if not date_str:
            messages.error(request, 'Date is required.')
            return redirect('fleet:daily-odo-bulk-create')
        
        try:
            date = timezone.datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, 'Invalid date format.')
            return redirect('fleet:daily-odo-bulk-create')
        
        # Get all active trucks
        active_trucks = Truck.objects.filter(status='ACTIVE').order_by('plate_number')
        
        # Create formset with one form per truck
        BulkFormSet = formset_factory(
            BulkDailyOdoEntryForm, 
            formset=BulkDailyOdoEntryFormSet,
            extra=0
        )
        
        formset = BulkFormSet(request.POST, date=date)
        
        if formset.is_valid():
            created_count = 0
            skipped_count = 0
            
            for form in formset:
                if form.cleaned_data.get('skip', False):
                    skipped_count += 1
                    continue
                
                truck_id = form.cleaned_data.get('truck_id')
                closing_odometer = form.cleaned_data.get('closing_odometer')
                remarks = form.cleaned_data.get('remarks', '')
                
                if closing_odometer is not None:
                    # Check if entry already exists
                    existing = DailyOdoRegistry.objects.filter(truck_id=truck_id, date=date).first()
                    
                    if existing:
                        # Update existing entry
                        existing.closing_odometer = closing_odometer
                        existing.remarks = remarks
                        existing.save()
                    else:
                        # Create new entry
                        truck = Truck.objects.get(pk=truck_id)
                        entry = DailyOdoRegistry.objects.create(
                            truck=truck,
                            date=date,
                            opening_odometer=truck.current_odometer,
                            closing_odometer=closing_odometer,
                            remarks=remarks
                        )
                    
                    created_count += 1
            
            messages.success(request, f'Successfully processed {created_count} entries for {date}. {skipped_count} trucks were skipped.')
            return redirect('fleet:daily-odo-list')
        else:
            # Re-render form with errors
            context = {
                'formset': formset,
                'trucks': active_trucks,
                'date': date
            }
            return render(request, self.template_name, context)


class DailyOdoReportView(LoginRequiredMixin, ListView):
    model = DailyOdoRegistry
    template_name = 'fleet/daily_odo_report.html'
    context_object_name = 'entries'
    paginate_by = 50
    
    def get_queryset(self):
        queryset = DailyOdoRegistry.objects.all().select_related('truck').order_by('-date', 'truck')
        
        # Apply filters
        truck_id = self.request.GET.get('truck')
        if truck_id:
            queryset = queryset.filter(truck_id=truck_id)
        
        date_from = self.request.GET.get('date_from')
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        
        date_to = self.request.GET.get('date_to')
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = DailyOdoRegistrySearchForm(self.request.GET)
        
        # Calculate totals
        total_mileage = sum(entry.daily_mileage for entry in context['entries'])
        context['total_mileage'] = total_mileage
        
        # Group by truck for summary
        truck_summary = {}
        for entry in context['entries']:
            truck_id = entry.truck_id
            if truck_id not in truck_summary:
                truck_summary[truck_id] = {
                    'truck': entry.truck,
                    'total_mileage': 0,
                    'entry_count': 0
                }
            truck_summary[truck_id]['total_mileage'] += entry.daily_mileage
            truck_summary[truck_id]['entry_count'] += 1
        
        context['truck_summary'] = truck_summary
        
        context['breadcrumbs'] = [
            {'name': 'Fleet', 'url': None},
            {'name': 'Daily Odometer', 'url': reverse('fleet:daily-odo-list')},
            {'name': 'Report', 'url': None}
        ]
        
        return context


class DailyOdoExportCSV(LoginRequiredMixin, View):
    def get(self, request):
        # Get filtered queryset using same filters as report
        queryset = DailyOdoRegistry.objects.all().select_related('truck').order_by('-date', 'truck')
        
        truck_id = request.GET.get('truck')
        if truck_id:
            queryset = queryset.filter(truck_id=truck_id)
        
        date_from = request.GET.get('date_from')
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        
        date_to = request.GET.get('date_to')
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
        
        # Create CSV response
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="daily_odometer_report_{timezone.now().date()}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Date', 'Truck', 'Opening ODO', 'Closing ODO', 'Daily Mileage', 'Remarks'])
        
        for entry in queryset:
            writer.writerow([
                entry.date,
                entry.truck.plate_number,
                entry.opening_odometer,
                entry.closing_odometer,
                entry.daily_mileage,
                entry.remarks
            ])
        
        return response


class FleetMileageSummaryView(LoginRequiredMixin, TemplateView):
    template_name = 'fleet/fleet_mileage_summary.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get date range from request
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        
        # Filter queryset
        queryset = DailyOdoRegistry.objects.all().select_related('truck')
        
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
        
        # Calculate mileage per truck
        truck_mileage = {}
        for entry in queryset:
            truck_id = entry.truck_id
            if truck_id not in truck_mileage:
                truck_mileage[truck_id] = {
                    'truck': entry.truck,
                    'total_mileage': 0,
                    'entry_count': 0
                }
            truck_mileage[truck_id]['total_mileage'] += entry.daily_mileage
            truck_mileage[truck_id]['entry_count'] += 1
        
        # Sort by mileage (descending)
        sorted_mileage = sorted(truck_mileage.values(), key=lambda x: x['total_mileage'], reverse=True)
        
        context['truck_mileage'] = sorted_mileage
        context['date_from'] = date_from
        context['date_to'] = date_to
        
        # Calculate grand total
        context['grand_total'] = sum(item['total_mileage'] for item in sorted_mileage)
        
        context['breadcrumbs'] = [
            {'name': 'Fleet', 'url': None},
            {'name': 'Daily Odometer', 'url': reverse('fleet:daily-odo-list')},
            {'name': 'Mileage Summary', 'url': None}
        ]
        
        return context


class OdometerDiscrepancyReportView(AdminRequiredMixin, TemplateView):
    template_name = 'fleet/odometer_discrepancy_report.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get date range from request
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        truck_id = self.request.GET.get('truck')
        
        # Filter fuel logs and daily odometer entries
        fuel_logs = FuelLog.objects.all()
        daily_odos = DailyOdoRegistry.objects.all()
        
        if date_from:
            fuel_logs = fuel_logs.filter(date__gte=date_from)
            daily_odos = daily_odos.filter(date__gte=date_from)
        
        if date_to:
            fuel_logs = fuel_logs.filter(date__lte=date_to)
            daily_odos = daily_odos.filter(date__lte=date_to)
        
        if truck_id:
            fuel_logs = fuel_logs.filter(truck_id=truck_id)
            daily_odos = daily_odos.filter(truck_id=truck_id)
        
        # Find discrepancies
        discrepancies = []
        
        for daily_odo in daily_odos:
            # Find fuel log on same date
            fuel_log = fuel_logs.filter(truck=daily_odo.truck, date=daily_odo.date).first()
            
            if fuel_log:
                difference = abs(fuel_log.odometer - daily_odo.closing_odometer)
                if difference > 10:  # More than 10km difference
                    discrepancies.append({
                        'date': daily_odo.date,
                        'truck': daily_odo.truck,
                        'daily_odo_closing': daily_odo.closing_odometer,
                        'fuel_log_odometer': fuel_log.odometer,
                        'difference': difference,
                        'daily_odo_id': daily_odo.id,
                        'fuel_log_id': fuel_log.id
                    })
        
        # Sort by difference (descending)
        discrepancies.sort(key=lambda x: x['difference'], reverse=True)
        
        context['discrepancies'] = discrepancies
        context['date_from'] = date_from
        context['date_to'] = date_to
        context['truck_filter'] = truck_id
        context['trucks'] = Truck.objects.all()
        
        context['breadcrumbs'] = [
            {'name': 'Fleet', 'url': None},
            {'name': 'Daily Odometer', 'url': reverse('fleet:daily-odo-list')},
            {'name': 'Discrepancy Report', 'url': None}
        ]
        
        return context


@login_required
def get_truck_current_odometer(request, truck_id):
    """Get truck's current odometer for AJAX calls"""
    try:
        truck = Truck.objects.get(pk=truck_id)
        return JsonResponse({'current_odometer': truck.current_odometer})
    except Truck.DoesNotExist:
        return JsonResponse({'error': 'Truck not found'}, status=404)

