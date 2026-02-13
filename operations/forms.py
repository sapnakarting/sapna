from django import forms
from django.utils import timezone

from fleet.models import Truck

from .models import CoalLog, MiningLog


class CoalLogForm(forms.ModelForm):
    class Meta:
        model = CoalLog
        fields = [
            'truck', 'date', 'pass_no', 'gross_weight', 'tare_weight',
            'diesel_liters', 'diesel_rate', 'origin_site', 'destination_site',
            'trip_remarks', 'diesel_remarks', 'diesel_adjustment',
            'air_adjustment', 'air_remarks', 'trip_adjustment'
        ]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'gross_weight': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'tare_weight': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'diesel_liters': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'diesel_rate': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'diesel_adjustment': forms.NumberInput(attrs={'step': '0.01'}),
            'air_adjustment': forms.NumberInput(attrs={'step': '0.01'}),
            'trip_adjustment': forms.NumberInput(attrs={'step': '0.01'}),
            'trip_remarks': forms.Textarea(attrs={'rows': 3}),
            'diesel_remarks': forms.Textarea(attrs={'rows': 3}),
            'air_remarks': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        for field_name, field in self.fields.items():
            if field_name not in ['trip_remarks', 'diesel_remarks', 'air_remarks']:
                field.widget.attrs.update({
                    'class': 'w-full px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-slate-500'
                })
            else:
                field.widget.attrs.update({
                    'class': 'w-full px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-slate-500'
                })
        
        # Set default date to today
        if not self.instance.pk:
            self.fields['date'].initial = timezone.now().date()

    def clean(self):
        cleaned_data = super().clean()
        gross_weight = cleaned_data.get('gross_weight')
        tare_weight = cleaned_data.get('tare_weight')
        
        if gross_weight and tare_weight and tare_weight > gross_weight:
            self.add_error('tare_weight', 'Tare weight cannot be greater than gross weight.')
        
        return cleaned_data

    def save(self, commit=True):
        coal_log = super().save(commit=False)
        
        if self.request and self.request.user.is_authenticated:
            coal_log.created_by = self.request.user
        
        # Calculate derived fields
        coal_log.net_weight = coal_log.calculate_net_weight()
        coal_log.diesel_cost = coal_log.calculate_diesel_cost()
        
        if commit:
            coal_log.save()
        
        return coal_log


class CoalLogSearchForm(forms.Form):
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-slate-500'
        })
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-slate-500'
        })
    )
    truck = forms.ModelChoiceField(
        queryset=Truck.objects.all(),
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-slate-500'
        })
    )
    pass_no = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Pass number...',
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-slate-500'
        })
    )
    origin_site = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Origin site...',
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-slate-500'
        })
    )


class MiningLogForm(forms.ModelForm):
    class Meta:
        model = MiningLog
        fields = [
            'type', 'date', 'time', 'chalan_no', 'customer_name',
            'truck', 'net', 'material', 'mining_type', 'chalan_document'
        ]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'time': forms.TimeInput(attrs={'type': 'time'}),
            'net': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        for field_name, field in self.fields.items():
            if field_name != 'chalan_document':
                field.widget.attrs.update({
                    'class': 'w-full px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-slate-500'
                })
            else:
                field.widget.attrs.update({
                    'class': 'w-full px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-slate-500'
                })
        
        # Set defaults
        if not self.instance.pk:
            self.fields['date'].initial = timezone.now().date()
            self.fields['time'].initial = timezone.now().time()

    def clean_chalan_no(self):
        chalan_no = self.cleaned_data['chalan_no'].upper().strip()
        
        # Check uniqueness if creating new
        if not self.instance.pk:
            if MiningLog.objects.filter(chalan_no=chalan_no).exists():
                raise forms.ValidationError("A mining log with this chalan number already exists.")
        else:
            if MiningLog.objects.filter(chalan_no=chalan_no).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError("A mining log with this chalan number already exists.")
        
        return chalan_no

    def save(self, commit=True):
        mining_log = super().save(commit=False)
        
        if self.request and self.request.user.is_authenticated:
            mining_log.created_by = self.request.user
        
        if commit:
            mining_log.save()
        
        return mining_log


class MiningLogSearchForm(forms.Form):
    LOG_TYPE_CHOICES = [
        ('', 'All'),
        ('DISPATCH', 'Dispatch'),
        ('PURCHASE', 'Purchase'),
    ]
    
    MINING_TYPE_CHOICES = [
        ('', 'All'),
        ('INTERNAL', 'Internal'),
        ('EXTERNAL', 'External'),
    ]
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-slate-500'
        })
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-slate-500'
        })
    )
    truck = forms.ModelChoiceField(
        queryset=Truck.objects.all(),
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-slate-500'
        })
    )
    type = forms.ChoiceField(
        choices=LOG_TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-slate-500'
        })
    )
    mining_type = forms.ChoiceField(
        choices=MINING_TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-slate-500'
        })
    )
    chalan_no = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Chalan number...',
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-slate-500'
        })
    )
    customer_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Customer name...',
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-slate-500'
        })
    )
