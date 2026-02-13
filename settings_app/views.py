from django.shortcuts import render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, UpdateView
from django.contrib import messages
from django.utils.decorators import method_decorator

from .models import SystemSettings
from .forms import SystemSettingsForm
from fleet.utils.permissions import is_admin_required


@method_decorator(is_admin_required, name='dispatch')
class SettingsView(LoginRequiredMixin, TemplateView):
    template_name = 'settings/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        settings = SystemSettings.objects.first()
        context['settings'] = settings
        context['form'] = SystemSettingsForm(instance=settings) if settings else SystemSettingsForm()
        context['breadcrumbs'] = [
            {'name': 'Settings', 'url': None}
        ]
        return context

    def post(self, request, *args, **kwargs):
        settings = SystemSettings.objects.first()
        if not settings:
            settings = SystemSettings()
            settings.pk = 1  # Ensure it's the singleton instance

        form = SystemSettingsForm(request.POST, instance=settings)
        
        if form.is_valid():
            form.save()
            messages.success(request, 'System settings updated successfully!')
            return redirect('settings_app:index')
        else:
            context = self.get_context_data(**kwargs)
            context['form'] = form
            return render(request, self.template_name, context)

