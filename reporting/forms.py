"""
Forms for reporting and analytics system.
"""

from datetime import date
from decimal import Decimal
from django import forms
from django.db.models import QuerySet

from fleet.models import Truck, Driver


class ReportFilterForm(forms.Form):
    """Base form for filtering reports by date range and entities."""
    
    date_from = forms.DateField(
        label='From Date',
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-transparent'
        }),
        required=False
    )
    
    date_to = forms.DateField(
        label='To Date',
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-transparent'
        }),
        required=False
    )
    
    truck = forms.ModelChoiceField(
        queryset=Truck.objects.none(),
        label='Truck',
        widget=forms.Select(attrs={
            'class': 'w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-transparent'
        }),
        required=False,
        empty_label="All Trucks"
    )
    
    driver = forms.ModelChoiceField(
        queryset=Driver.objects.none(),
        label='Driver',
        widget=forms.Select(attrs={
            'class': 'w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-transparent'
        }),
        required=False,
        empty_label="All Drivers"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate queryset for truck and driver
        self.fields['truck'].queryset = Truck.objects.all().order_by('plate_number')
        self.fields['driver'].queryset = Driver.objects.all().order_by('name')
    
    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        
        if date_from and date_to and date_from > date_to:
            raise forms.ValidationError("From date cannot be later than To date.")
        
        return cleaned_data
    
    def get_filtered_queryset(self, queryset: QuerySet):
        """Apply filters to queryset based on form data."""
        date_from = self.cleaned_data.get('date_from')
        date_to = self.cleaned_data.get('date_to')
        truck = self.cleaned_data.get('truck')
        driver = self.cleaned_data.get('driver')
        
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
        if truck:
            queryset = queryset.filter(truck=truck)
        if driver:
            queryset = queryset.filter(driver=driver)
        
        return queryset


class GroupByForm(forms.Form):
    """Form for selecting groupBy options for reports."""
    
    GROUP_BY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]
    
    group_by = forms.ChoiceField(
        label='Group By',
        choices=GROUP_BY_CHOICES,
        initial='daily',
        widget=forms.Select(attrs={
            'class': 'w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-transparent'
        })
    )


class ExportFormatForm(forms.Form):
    """Form for selecting export format."""
    
    EXPORT_CHOICES = [
        ('pdf', 'PDF Report'),
        ('csv', 'CSV Data'),
    ]
    
    format = forms.ChoiceField(
        label='Export Format',
        choices=EXPORT_CHOICES,
        initial='pdf',
        widget=forms.Select(attrs={
            'class': 'w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-transparent'
        })
    )


class FuelConsumptionFilterForm(ReportFilterForm):
    """Specialized form for fuel consumption reports."""
    
    ENTRY_TYPE_CHOICES = [
        ('', 'All Entry Types'),
        ('FULL_TANK', 'Full Tank'),
        ('PER_TRIP', 'Per Trip'),
    ]
    
    entry_type = forms.ChoiceField(
        label='Entry Type',
        choices=ENTRY_TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-transparent'
        })
    )
    
    def get_filtered_queryset(self, queryset: QuerySet):
        """Apply filters to queryset including entry type."""
        queryset = super().get_filtered_queryset(queryset)
        
        entry_type = self.cleaned_data.get('entry_type')
        if entry_type:
            queryset = queryset.filter(entry_type=entry_type)
        
        return queryset


class TireCostFilterForm(forms.Form):
    """Form for tire cost reports."""
    
    STATUS_CHOICES = [
        ('', 'All Statuses'),
        ('NEW', 'New'),
        ('MOUNTED', 'Mounted'),
        ('SPARE', 'Spare'),
        ('REPAIR', 'Repair'),
        ('SCRAPPED', 'Scrapped'),
    ]
    
    BRAND_CHOICES = [
        ('', 'All Brands'),
    ]
    
    truck = forms.ModelChoiceField(
        queryset=Truck.objects.all().order_by('plate_number'),
        label='Truck',
        widget=forms.Select(attrs={
            'class': 'w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-transparent'
        }),
        required=False,
        empty_label="All Trucks"
    )
    
    status = forms.ChoiceField(
        label='Tire Status',
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-transparent'
        })
    )
    
    def get_filtered_queryset(self, queryset: QuerySet):
        """Apply filters to tire queryset."""
        truck = self.cleaned_data.get('truck')
        status = self.cleaned_data.get('status')
        
        if truck:
            queryset = queryset.filter(truck=truck)
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset


class DriverPerformanceFilterForm(ReportFilterForm):
    """Form for driver performance reports."""
    
    PERFORMANCE_CHOICES = [
        ('all', 'All Drivers'),
        ('top_performers', 'Top Performers'),
        ('needs_improvement', 'Needs Improvement'),
    ]
    
    driver_filter = forms.ChoiceField(
        label='Driver Filter',
        choices=PERFORMANCE_CHOICES,
        initial='all',
        widget=forms.Select(attrs={
            'class': 'w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-transparent'
        })
    )
    
    MIN_TRIPS = 1
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove truck filter for driver reports
        self.fields.pop('truck', None)


class FleetStatusFilterForm(forms.Form):
    """Form for fleet status reports."""
    
    STATUS_CHOICES = [
        ('', 'All Statuses'),
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
        ('MAINTENANCE', 'Maintenance'),
    ]
    
    FLEET_TYPE_CHOICES = [
        ('', 'All Types'),
        ('COAL', 'Coal'),
        ('MINING', 'Mining'),
    ]
    
    MINING_TYPE_CHOICES = [
        ('', 'All Types'),
        ('INTERNAL', 'Internal'),
        ('EXTERNAL', 'External'),
    ]
    
    DOCUMENT_STATUS_CHOICES = [
        ('all', 'All Trucks'),
        ('expiring_soon', 'Expiring Soon (≤30 days)'),
        ('expired', 'Expired'),
        ('current', 'Current Documents'),
    ]
    
    status = forms.ChoiceField(
        label='Fleet Status',
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-transparent'
        })
    )
    
    fleet_type = forms.ChoiceField(
        label='Fleet Type',
        choices=FLEET_TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-transparent'
        })
    )
    
    mining_type = forms.ChoiceField(
        label='Mining Type',
        choices=MINING_TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-transparent'
        })
    )
    
    document_status = forms.ChoiceField(
        label='Document Status',
        choices=DOCUMENT_STATUS_CHOICES,
        initial='all',
        widget=forms.Select(attrs={
            'class': 'w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-transparent'
        })
    )
    
    def get_filtered_queryset(self, queryset: QuerySet):
        """Apply filters to fleet status queryset."""
        status = self.cleaned_data.get('status')
        fleet_type = self.cleaned_data.get('fleet_type')
        mining_type = self.cleaned_data.get('mining_type')
        document_status = self.cleaned_data.get('document_status')
        
        if status:
            queryset = queryset.filter(status=status)
        if fleet_type:
            queryset = queryset.filter(fleet_type=fleet_type)
        if mining_type:
            queryset = queryset.filter(mining_type=mining_type)
        
        # Apply document status filter
        if document_status and document_status != 'all':
            today = date.today()
            if document_status == 'expiring_soon':
                queryset = queryset.filter(
                    Q(fitness_expiry__lte=today + timedelta(days=30)) |
                    Q(insurance_expiry__lte=today + timedelta(days=30)) |
                    Q(pucc_expiry__lte=today + timedelta(days=30)) |
                    Q(tax_expiry__lte=today + timedelta(days=30)) |
                    Q(permit_expiry__lte=today + timedelta(days=30))
                )
            elif document_status == 'expired':
                queryset = queryset.filter(
                    Q(fitness_expiry__lt=today) |
                    Q(insurance_expiry__lt=today) |
                    Q(pucc_expiry__lt=today) |
                    Q(tax_expiry__lt=today) |
                    Q(permit_expiry__lt=today)
                )
            elif document_status == 'current':
                queryset = queryset.exclude(
                    Q(fitness_expiry__lt=today) |
                    Q(insurance_expiry__lt=today) |
                    Q(pucc_expiry__lt=today) |
                    Q(tax_expiry__lt=today) |
                    Q(permit_expiry__lt=today)
                )
        
        return queryset


class CostAnalysisFilterForm(forms.Form):
    """Form for cost analysis reports."""
    
    date_from = forms.DateField(
        label='From Date',
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-transparent'
        }),
        required=False
    )
    
    date_to = forms.DateField(
        label='To Date',
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-transparent'
        }),
        required=False
    )
    
    fleet_type = forms.ChoiceField(
        label='Fleet Type',
        choices=[
            ('', 'All Types'),
            ('COAL', 'Coal'),
            ('MINING', 'Mining'),
        ],
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-transparent'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        
        if date_from and date_to and date_from > date_to:
            raise forms.ValidationError("From date cannot be later than To date.")
        
        return cleaned_data


class EfficiencyFilterForm(forms.Form):
    """Form for efficiency comparison reports."""
    
    date_from = forms.DateField(
        label='From Date',
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-transparent'
        }),
        required=False
    )
    
    date_to = forms.DateField(
        label='To Date',
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-transparent'
        }),
        required=False
    )
    
    SORT_BY_CHOICES = [
        ('efficiency_desc', 'Efficiency (High to Low)'),
        ('efficiency_asc', 'Efficiency (Low to High)'),
        ('plate_asc', 'Truck Number (A-Z)'),
        ('plate_desc', 'Truck Number (Z-A)'),
    ]
    
    sort_by = forms.ChoiceField(
        label='Sort By',
        choices=SORT_BY_CHOICES,
        initial='efficiency_desc',
        widget=forms.Select(attrs={
            'class': 'w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-transparent'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        
        if date_from and date_to and date_from > date_to:
            raise forms.ValidationError("From date cannot be later than To date.")
        
        return cleaned_data