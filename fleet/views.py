from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.views import LogoutView as DjangoLogoutView
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from .forms import LoginForm, UserCreationForm
from .models import UserProfile
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

