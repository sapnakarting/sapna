from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.views import LogoutView as DjangoLogoutView
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse

from .forms import LoginForm, UserCreationForm, TruckForm, TruckSearchForm, DriverForm, FuelLogForm, DieselPriceForm
from .models import UserProfile, Truck, Driver, FuelLog, TireInventory, DieselPrice
from .utils.permissions import is_admin_required, is_fuel_agent_required


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


@is_fuel_agent_required
def get_today_diesel_price(request):
    """Get today's diesel price for form autocomplete"""
    today = timezone.now().date()
    today_price = DieselPrice.objects.filter(date=today).first()
    
    if today_price:
        return JsonResponse({'price': float(today_price.price)})
    else:
        return JsonResponse({'price': 0.0})

