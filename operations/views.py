import json
import os
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.files.storage import default_storage
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from dashboard.models import ActivityLog
from fleet.models import Truck

from .forms import CoalLogForm, CoalLogSearchForm, MiningLogForm, MiningLogSearchForm
from .models import CoalLog, MiningLog


# ============== COAL LOG VIEWS ==============

class CoalLogListView(LoginRequiredMixin, ListView):
    model = CoalLog
    template_name = 'operations/coal_log_list.html'
    context_object_name = 'coal_logs'
    paginate_by = 20

    def get_queryset(self):
        queryset = CoalLog.objects.all().select_related('truck').order_by('-date', '-created_at')
        
        # Apply filters
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        truck_id = self.request.GET.get('truck')
        pass_no = self.request.GET.get('pass_no')
        origin_site = self.request.GET.get('origin_site')
        
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
        if truck_id:
            queryset = queryset.filter(truck_id=truck_id)
        if pass_no:
            queryset = queryset.filter(pass_no__icontains=pass_no)
        if origin_site:
            queryset = queryset.filter(origin_site__icontains=origin_site)
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = CoalLogSearchForm(self.request.GET)
        context['date_from'] = self.request.GET.get('date_from')
        context['date_to'] = self.request.GET.get('date_to')
        
        # Calculate summary stats
        queryset = self.get_queryset()
        context['total_trips'] = queryset.count()
        context['total_net_weight'] = queryset.aggregate(Sum('net_weight'))['net_weight__sum'] or 0
        context['total_diesel_liters'] = queryset.aggregate(Sum('diesel_liters'))['diesel_liters__sum'] or 0
        context['total_diesel_cost'] = queryset.aggregate(Sum('diesel_cost'))['diesel_cost__sum'] or 0
        
        return context


class CoalLogDetailView(LoginRequiredMixin, DetailView):
    model = CoalLog
    template_name = 'operations/coal_log_detail.html'
    context_object_name = 'coal_log'
    pk_url_kwarg = 'pk'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        coal_log = self.object
        
        # Calculate additional metrics
        context['total_adjustments'] = coal_log.calculate_total_adjustments()
        context['documents'] = coal_log.documents or []
        
        return context


class CoalLogCreateView(LoginRequiredMixin, CreateView):
    model = CoalLog
    form_class = CoalLogForm
    template_name = 'operations/coal_log_form.html'
    success_url = reverse_lazy('coal-log-list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        coal_log = form.save()
        
        # Handle file uploads
        documents = []
        for file_key in ['document_1', 'document_2', 'document_3']:
            file = self.request.FILES.get(file_key)
            if file:
                file_path = default_storage.save(
                    f'coal_documents/{coal_log.id}/{file_key}_{file.name}',
                    file
                )
                documents.append({
                    'name': file.name,
                    'path': file_path,
                    'uploaded_at': timezone.now().isoformat()
                })
        
        if documents:
            coal_log.documents = documents
            coal_log.save()
        
        # Log activity
        ActivityLog.objects.create(
            action='COAL_ENTRY',
            description=f'Coal entry created: {coal_log.truck.plate_number} - {coal_log.pass_no}',
            actor=self.request.user,
            object_type='CoalLog',
            object_id=coal_log.id,
            metadata={
                'truck_id': coal_log.truck.id,
                'pass_no': coal_log.pass_no,
                'net_weight': float(coal_log.net_weight)
            }
        )
        
        messages.success(
            self.request,
            f'Coal entry created successfully! Net weight: {coal_log.net_weight} tons'
        )
        return super().form_valid(form)


class CoalLogUpdateView(LoginRequiredMixin, UpdateView):
    model = CoalLog
    form_class = CoalLogForm
    template_name = 'operations/coal_log_form.html'
    success_url = reverse_lazy('coal-log-list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        coal_log = form.save()
        
        # Handle additional file uploads
        documents = coal_log.documents or []
        for file_key in ['document_1', 'document_2', 'document_3']:
            file = self.request.FILES.get(file_key)
            if file:
                file_path = default_storage.save(
                    f'coal_documents/{coal_log.id}/{file_key}_{file.name}',
                    file
                )
                documents.append({
                    'name': file.name,
                    'path': file_path,
                    'uploaded_at': timezone.now().isoformat()
                })
        
        if documents:
            coal_log.documents = documents
            coal_log.save()
        
        # Log activity
        ActivityLog.objects.create(
            action='COAL_ENTRY',
            description=f'Coal entry updated: {coal_log.truck.plate_number} - {coal_log.pass_no}',
            actor=self.request.user,
            object_type='CoalLog',
            object_id=coal_log.id
        )
        
        messages.success(self.request, f'Coal entry updated successfully!')
        return super().form_valid(form)


class CoalLogDeleteView(LoginRequiredMixin, DeleteView):
    model = CoalLog
    template_name = 'operations/coal_log_delete.html'
    success_url = reverse_lazy('coal-log-list')
    context_object_name = 'coal_log'

    def delete(self, request, *args, **kwargs):
        coal_log = self.get_object()
        
        # Log activity before deletion
        ActivityLog.objects.create(
            action='COAL_ENTRY',
            description=f'Coal entry deleted: {coal_log.truck.plate_number} - {coal_log.pass_no}',
            actor=request.user,
            object_type='CoalLog',
            object_id=coal_log.id
        )
        
        messages.success(request, f'Coal entry deleted successfully!')
        return super().delete(request, *args, **kwargs)


# ============== MINING LOG VIEWS ==============

class MiningLogListView(LoginRequiredMixin, ListView):
    model = MiningLog
    template_name = 'operations/mining_log_list.html'
    context_object_name = 'mining_logs'
    paginate_by = 20

    def get_queryset(self):
        queryset = MiningLog.objects.all().select_related('truck').order_by('-date', '-time')
        
        # Apply filters
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        truck_id = self.request.GET.get('truck')
        log_type = self.request.GET.get('type')
        mining_type = self.request.GET.get('mining_type')
        chalan_no = self.request.GET.get('chalan_no')
        customer_name = self.request.GET.get('customer_name')
        
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
        if truck_id:
            queryset = queryset.filter(truck_id=truck_id)
        if log_type:
            queryset = queryset.filter(type=log_type)
        if mining_type:
            queryset = queryset.filter(mining_type=mining_type)
        if chalan_no:
            queryset = queryset.filter(chalan_no__icontains=chalan_no)
        if customer_name:
            queryset = queryset.filter(customer_name__icontains=customer_name)
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = MiningLogSearchForm(self.request.GET)
        context['date_from'] = self.request.GET.get('date_from')
        context['date_to'] = self.request.GET.get('date_to')
        
        # Calculate summary stats
        queryset = self.get_queryset()
        context['total_entries'] = queryset.count()
        context['total_tonnage'] = queryset.aggregate(Sum('net'))['net__sum'] or 0
        context['dispatch_count'] = queryset.filter(type='DISPATCH').count()
        context['purchase_count'] = queryset.filter(type='PURCHASE').count()
        
        return context


class MiningLogDetailView(LoginRequiredMixin, DetailView):
    model = MiningLog
    template_name = 'operations/mining_log_detail.html'
    context_object_name = 'mining_log'
    pk_url_kwarg = 'pk'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        mining_log = self.object
        
        context['documents'] = mining_log.documents or []
        context['has_chalan_document'] = bool(mining_log.chalan_document)
        
        return context


class MiningLogCreateView(LoginRequiredMixin, CreateView):
    model = MiningLog
    form_class = MiningLogForm
    template_name = 'operations/mining_log_form.html'
    success_url = reverse_lazy('mining-log-list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        mining_log = form.save()
        
        # Handle additional file uploads
        documents = []
        for file_key in ['document_1', 'document_2']:
            file = self.request.FILES.get(file_key)
            if file:
                file_path = default_storage.save(
                    f'mining_documents/{mining_log.id}/{file_key}_{file.name}',
                    file
                )
                documents.append({
                    'name': file.name,
                    'path': file_path,
                    'uploaded_at': timezone.now().isoformat()
                })
        
        if documents:
            mining_log.documents = documents
            mining_log.save()
        
        # Log activity
        ActivityLog.objects.create(
            action='MINING_ENTRY',
            description=f'Mining entry created: {mining_log.chalan_no} - {mining_log.customer_name}',
            actor=self.request.user,
            object_type='MiningLog',
            object_id=mining_log.id,
            metadata={
                'truck_id': mining_log.truck.id,
                'chalan_no': mining_log.chalan_no,
                'type': mining_log.type,
                'net': float(mining_log.net)
            }
        )
        
        messages.success(
            self.request,
            f'Mining entry created successfully! Chalan: {mining_log.chalan_no}'
        )
        return super().form_valid(form)


class MiningLogUpdateView(LoginRequiredMixin, UpdateView):
    model = MiningLog
    form_class = MiningLogForm
    template_name = 'operations/mining_log_form.html'
    success_url = reverse_lazy('mining-log-list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        mining_log = form.save()
        
        # Handle additional file uploads
        documents = mining_log.documents or []
        for file_key in ['document_1', 'document_2']:
            file = self.request.FILES.get(file_key)
            if file:
                file_path = default_storage.save(
                    f'mining_documents/{mining_log.id}/{file_key}_{file.name}',
                    file
                )
                documents.append({
                    'name': file.name,
                    'path': file_path,
                    'uploaded_at': timezone.now().isoformat()
                })
        
        if documents:
            mining_log.documents = documents
            mining_log.save()
        
        # Log activity
        ActivityLog.objects.create(
            action='MINING_ENTRY',
            description=f'Mining entry updated: {mining_log.chalan_no} - {mining_log.customer_name}',
            actor=self.request.user,
            object_type='MiningLog',
            object_id=mining_log.id
        )
        
        messages.success(self.request, f'Mining entry updated successfully!')
        return super().form_valid(form)


class MiningLogDeleteView(LoginRequiredMixin, DeleteView):
    model = MiningLog
    template_name = 'operations/mining_log_delete.html'
    success_url = reverse_lazy('mining-log-list')
    context_object_name = 'mining_log'

    def delete(self, request, *args, **kwargs):
        mining_log = self.get_object()
        
        # Log activity before deletion
        ActivityLog.objects.create(
            action='MINING_ENTRY',
            description=f'Mining entry deleted: {mining_log.chalan_no} - {mining_log.customer_name}',
            actor=request.user,
            object_type='MiningLog',
            object_id=mining_log.id
        )
        
        messages.success(request, f'Mining entry deleted successfully!')
        return super().delete(request, *args, **kwargs)


# ============== API VIEWS ==============

@login_required
def get_coal_summary(request):
    """API endpoint for coal operations summary"""
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    queryset = CoalLog.objects.all()
    
    if date_from:
        queryset = queryset.filter(date__gte=date_from)
    if date_to:
        queryset = queryset.filter(date__lte=date_to)
    
    summary = {
        'total_trips': queryset.count(),
        'total_net_weight': float(queryset.aggregate(Sum('net_weight'))['net_weight__sum'] or 0),
        'total_diesel_liters': float(queryset.aggregate(Sum('diesel_liters'))['diesel_liters__sum'] or 0),
        'total_diesel_cost': float(queryset.aggregate(Sum('diesel_cost'))['diesel_cost__sum'] or 0),
    }
    
    return JsonResponse(summary)


@login_required
def get_mining_summary(request):
    """API endpoint for mining operations summary"""
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    queryset = MiningLog.objects.all()
    
    if date_from:
        queryset = queryset.filter(date__gte=date_from)
    if date_to:
        queryset = queryset.filter(date__lte=date_to)
    
    summary = {
        'total_entries': queryset.count(),
        'total_tonnage': float(queryset.aggregate(Sum('net'))['net__sum'] or 0),
        'dispatch_count': queryset.filter(type='DISPATCH').count(),
        'purchase_count': queryset.filter(type='PURCHASE').count(),
        'internal_count': queryset.filter(mining_type='INTERNAL').count(),
        'external_count': queryset.filter(mining_type='EXTERNAL').count(),
    }
    
    return JsonResponse(summary)


@login_required
def calculate_net_weight(request):
    """AJAX endpoint to calculate net weight from gross and tare"""
    try:
        gross = Decimal(request.POST.get('gross_weight', 0))
        tare = Decimal(request.POST.get('tare_weight', 0))
        net = max(gross - tare, Decimal('0'))
        return JsonResponse({
            'success': True,
            'net_weight': float(net),
            'gross_weight': float(gross),
            'tare_weight': float(tare)
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
def calculate_diesel_cost(request):
    """AJAX endpoint to calculate diesel cost"""
    try:
        liters = Decimal(request.POST.get('diesel_liters', 0))
        rate = Decimal(request.POST.get('diesel_rate', 0))
        cost = liters * rate
        return JsonResponse({
            'success': True,
            'diesel_cost': float(cost),
            'diesel_liters': float(liters),
            'diesel_rate': float(rate)
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


# ============== HTMX PARTIAL VIEWS ==============

class CoalLogSearchView(LoginRequiredMixin, ListView):
    model = CoalLog
    template_name = 'operations/coal_log_list_partial.html'
    context_object_name = 'coal_logs'

    def get_queryset(self):
        queryset = CoalLog.objects.all().select_related('truck').order_by('-date', '-created_at')
        
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        truck_id = self.request.GET.get('truck')
        pass_no = self.request.GET.get('pass_no')
        origin_site = self.request.GET.get('origin_site')
        
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
        if truck_id:
            queryset = queryset.filter(truck_id=truck_id)
        if pass_no:
            queryset = queryset.filter(pass_no__icontains=pass_no)
        if origin_site:
            queryset = queryset.filter(origin_site__icontains=origin_site)
        
        return queryset


class MiningLogSearchView(LoginRequiredMixin, ListView):
    model = MiningLog
    template_name = 'operations/mining_log_list_partial.html'
    context_object_name = 'mining_logs'

    def get_queryset(self):
        queryset = MiningLog.objects.all().select_related('truck').order_by('-date', '-time')
        
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        truck_id = self.request.GET.get('truck')
        log_type = self.request.GET.get('type')
        mining_type = self.request.GET.get('mining_type')
        chalan_no = self.request.GET.get('chalan_no')
        customer_name = self.request.GET.get('customer_name')
        
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
        if truck_id:
            queryset = queryset.filter(truck_id=truck_id)
        if log_type:
            queryset = queryset.filter(type=log_type)
        if mining_type:
            queryset = queryset.filter(mining_type=mining_type)
        if chalan_no:
            queryset = queryset.filter(chalan_no__icontains=chalan_no)
        if customer_name:
            queryset = queryset.filter(customer_name__icontains=customer_name)
        
        return queryset
