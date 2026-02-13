from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, UpdateView
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.db.models import Count

from .models import Alert
from .forms import AlertUpdateForm
from .utils.permissions import is_admin_required


class AlertListView(LoginRequiredMixin, ListView):
    model = Alert
    template_name = 'fleet/alert_list.html'
    context_object_name = 'alerts'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Alert.objects.all().order_by('-alert_level', '-created_at')
        
        # Apply filters
        alert_type = self.request.GET.get('alert_type', '')
        status = self.request.GET.get('status', '')
        level = self.request.GET.get('level', '')
        truck = self.request.GET.get('truck', '')
        
        if alert_type:
            queryset = queryset.filter(alert_type=alert_type)
        if status:
            queryset = queryset.filter(status=status)
        if level:
            queryset = queryset.filter(alert_level=level)
        if truck:
            queryset = queryset.filter(truck__plate_number__icontains=truck)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add filter options
        context['alert_types'] = Alert.AlertType.choices
        context['alert_statuses'] = Alert.AlertStatus.choices
        context['alert_levels'] = Alert.AlertLevel.choices
        
        # Add statistics
        context['stats'] = {
            'total': Alert.objects.count(),
            'pending': Alert.objects.filter(status=Alert.AlertStatus.PENDING).count(),
            'critical': Alert.objects.filter(alert_level=Alert.AlertLevel.CRITICAL, status=Alert.AlertStatus.PENDING).count(),
            'warning': Alert.objects.filter(alert_level=Alert.AlertLevel.WARNING, status=Alert.AlertStatus.PENDING).count(),
            'info': Alert.objects.filter(alert_level=Alert.AlertLevel.INFO, status=Alert.AlertStatus.PENDING).count(),
        }
        
        context['breadcrumbs'] = [
            {'name': 'Compliance', 'url': None},
            {'name': 'Alerts', 'url': None}
        ]
        
        return context


class AlertDetailView(LoginRequiredMixin, DetailView):
    model = Alert
    template_name = 'fleet/alert_detail.html'
    context_object_name = 'alert'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context['breadcrumbs'] = [
            {'name': 'Compliance', 'url': reverse_lazy('fleet:alert-list')},
            {'name': 'Alerts', 'url': reverse_lazy('fleet:alert-list')},
            {'name': f'Alert #{self.object.id}', 'url': None}
        ]
        
        return context


class AlertUpdateView(LoginRequiredMixin, UpdateView):
    model = Alert
    form_class = AlertUpdateForm
    template_name = 'fleet/alert_form.html'
    success_url = reverse_lazy('fleet:alert-list')
    
    @is_admin_required
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def form_valid(self, form):
        alert = form.save(commit=False)
        
        # Handle status changes
        if form.cleaned_data['status'] in [Alert.AlertStatus.RESOLVED, Alert.AlertStatus.DISMISSED]:
            alert.resolved_at = timezone.now()
            alert.resolved_by = self.request.user
            alert.resolution_notes = form.cleaned_data.get('resolution_notes', '')
        else:
            alert.resolved_at = None
            alert.resolved_by = None
            alert.resolution_notes = ''
        
        alert.save()
        messages.success(self.request, f'Alert "{alert.title}" updated successfully.')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context['breadcrumbs'] = [
            {'name': 'Compliance', 'url': reverse_lazy('fleet:alert-list')},
            {'name': 'Alerts', 'url': reverse_lazy('fleet:alert-list')},
            {'name': f'Update Alert #{self.object.id}', 'url': None}
        ]
        
        return context


@login_required
@is_admin_required
def resolve_alert(request, pk):
    """Quick resolve action for alerts"""
    alert = get_object_or_404(Alert, pk=pk)
    
    if request.method == 'POST':
        resolution_notes = request.POST.get('resolution_notes', '')
        
        alert.status = Alert.AlertStatus.RESOLVED
        alert.resolved_at = timezone.now()
        alert.resolved_by = request.user
        alert.resolution_notes = resolution_notes
        alert.save()
        
        messages.success(request, f'Alert "{alert.title}" marked as resolved.')
        return JsonResponse({'success': True, 'message': 'Alert resolved successfully'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request'}, status=400)


@login_required
@is_admin_required
def dismiss_alert(request, pk):
    """Quick dismiss action for alerts"""
    alert = get_object_or_404(Alert, pk=pk)
    
    if request.method == 'POST':
        dismissal_notes = request.POST.get('dismissal_notes', '')
        
        alert.status = Alert.AlertStatus.DISMISSED
        alert.resolved_at = timezone.now()
        alert.resolved_by = request.user
        alert.resolution_notes = dismissal_notes
        alert.save()
        
        messages.success(request, f'Alert "{alert.title}" marked as dismissed.')
        return JsonResponse({'success': True, 'message': 'Alert dismissed successfully'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request'}, status=400)


@login_required
@is_admin_required
def bulk_resolve_alerts(request):
    """Bulk resolve multiple alerts"""
    if request.method == 'POST':
        alert_ids = request.POST.getlist('alert_ids[]')
        resolution_notes = request.POST.get('resolution_notes', '')
        
        if alert_ids:
            alerts = Alert.objects.filter(id__in=alert_ids, status=Alert.AlertStatus.PENDING)
            count = alerts.count()
            
            alerts.update(
                status=Alert.AlertStatus.RESOLVED,
                resolved_at=timezone.now(),
                resolved_by=request.user,
                resolution_notes=resolution_notes
            )
            
            messages.success(request, f'Successfully resolved {count} alerts.')
            return JsonResponse({'success': True, 'count': count})
        
        return JsonResponse({'success': False, 'message': 'No alerts selected'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request'}, status=400)


@login_required
def get_alert_stats(request):
    """Get alert statistics for dashboard"""
    stats = {
        'total': Alert.objects.count(),
        'pending': Alert.objects.filter(status=Alert.AlertStatus.PENDING).count(),
        'critical': Alert.objects.filter(alert_level=Alert.AlertLevel.CRITICAL, status=Alert.AlertStatus.PENDING).count(),
        'warning': Alert.objects.filter(alert_level=Alert.AlertLevel.WARNING, status=Alert.AlertStatus.PENDING).count(),
        'info': Alert.objects.filter(alert_level=Alert.AlertLevel.INFO, status=Alert.AlertStatus.PENDING).count(),
        'resolved': Alert.objects.filter(status=Alert.AlertStatus.RESOLVED).count(),
        'dismissed': Alert.objects.filter(status=Alert.AlertStatus.DISMISSED).count(),
    }
    
    return JsonResponse(stats)