from django.contrib.auth.decorators import login_required
from functools import wraps
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin


def is_admin_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if not hasattr(request.user, 'userprofile') or request.user.userprofile.role != 'ADMIN':
            from django.shortcuts import redirect
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin for class-based views that require admin access"""
    def test_func(self):
        return hasattr(self.request.user, 'userprofile') and self.request.user.userprofile.role == 'ADMIN'
    
    def handle_no_permission(self):
        from django.shortcuts import redirect
        return redirect('dashboard')


def is_fuel_agent_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if not hasattr(request.user, 'userprofile') or request.user.userprofile.role not in ['ADMIN', 'FUEL_AGENT']:
            from django.shortcuts import redirect
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def any_role_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if not hasattr(request.user, 'userprofile') or request.user.userprofile.role not in ['ADMIN', 'FUEL_AGENT']:
            from django.shortcuts import redirect
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view
