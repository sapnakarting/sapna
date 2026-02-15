from datetime import datetime
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
import os


def health_check(request):
    """Basic health check endpoint."""
    return JsonResponse({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': os.getenv('GIT_COMMIT', 'unknown'),
    })


def health_check_detailed(request):
    """Detailed health check with component status."""
    status = {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': os.getenv('GIT_COMMIT', 'unknown'),
        'environment': 'production' if not settings.DEBUG else 'development',
        'components': {}
    }
    
    # Database check
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        status['components']['database'] = {'status': 'healthy'}
    except Exception as e:
        status['components']['database'] = {'status': 'unhealthy', 'error': str(e)}
        status['status'] = 'degraded'
    
    # Check if Sentry is configured
    status['components']['sentry'] = {
        'status': 'configured' if os.getenv('SENTRY_DSN') else 'not_configured'
    }
    
    # Check media storage
    try:
        if settings.MEDIA_ROOT:
            os.listdir(settings.MEDIA_ROOT)
            status['components']['media_storage'] = {'status': 'accessible'}
    except Exception as e:
        status['components']['media_storage'] = {'status': 'unhealthy', 'error': str(e)}
    
    http_status = 200 if status['status'] == 'healthy' else 503
    return JsonResponse(status, status=http_status)


def readiness_check(request):
    """Kubernetes-style readiness check."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return JsonResponse({
            'ready': True,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return JsonResponse({
            'ready': False,
            'error': str(e)
        }, status=503)


urlpatterns = [
    path('', RedirectView.as_view(url='/dashboard/', permanent=False)),
    path('admin/', admin.site.urls),
    path('fleet/', include('fleet.urls')),
    path('operations/', include('operations.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('reporting/', include('reporting.urls')),
    path('settings/', include('settings_app.urls')),
    # Health check endpoints
    path('health/', health_check, name='health-check'),
    path('health/detailed/', health_check_detailed, name='health-check-detailed'),
    path('ready/', readiness_check, name='readiness-check'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
