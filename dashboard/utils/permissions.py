from django.contrib.auth.decorators import login_required
from functools import wraps


def is_admin_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if not hasattr(request.user, 'userprofile') or request.user.userprofile.role != 'ADMIN':
            from django.shortcuts import redirect
            return redirect('dashboard:index')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def is_fuel_agent_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if not hasattr(request.user, 'userprofile') or request.user.userprofile.role not in ['ADMIN', 'FUEL_AGENT']:
            from django.shortcuts import redirect
            return redirect('dashboard:index')
        return view_func(request, *args, **kwargs)
    return _wrapped_view
