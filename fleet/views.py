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

from .forms import LoginForm, UserCreationForm, TruckForm, TruckSearchForm
from .models import UserProfile, Truck, FuelLog, TireInventory
from .utils.permissions import is_admin_required


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

