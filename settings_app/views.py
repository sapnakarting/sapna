from django.shortcuts import render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, UpdateView
from django.contrib import messages

from .models import SystemSettings


class SettingsView(LoginRequiredMixin, TemplateView):
    template_name = 'settings/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        settings = SystemSettings.objects.first()
        context['settings'] = settings
        context['breadcrumbs'] = [
            {'name': 'Settings', 'url': None}
        ]
        return context

