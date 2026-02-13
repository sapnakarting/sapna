from django import forms
from .models import SystemSettings


class SystemSettingsForm(forms.ModelForm):
    class Meta:
        model = SystemSettings
        fields = [
            'compliance_alert_email',
            'global_fuel_efficiency_benchmark',
            'per_trip_diesel_benchmark',
            'per_tonnage_diesel_benchmark',
            'fleet_efficiency_threshold_min',
            'fleet_efficiency_threshold_max',
            'fuel_efficiency_check_frequency'
        ]
        widgets = {
            'compliance_alert_email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-slate-500 focus:border-transparent',
                'placeholder': 'Email address for compliance notifications'
            }),
            'global_fuel_efficiency_benchmark': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-slate-500 focus:border-transparent',
                'step': '0.01',
                'placeholder': 'Target km per liter for entire fleet'
            }),
            'per_trip_diesel_benchmark': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-slate-500 focus:border-transparent',
                'step': '0.01',
                'placeholder': 'Expected diesel consumption per trip'
            }),
            'per_tonnage_diesel_benchmark': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-slate-500 focus:border-transparent',
                'step': '0.01',
                'placeholder': 'Expected diesel per ton of material'
            }),
            'fleet_efficiency_threshold_min': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-slate-500 focus:border-transparent',
                'step': '0.01',
                'placeholder': 'Alert if efficiency falls below this value'
            }),
            'fleet_efficiency_threshold_max': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-slate-500 focus:border-transparent',
                'step': '0.01',
                'placeholder': 'Alert if efficiency exceeds this value'
            }),
            'fuel_efficiency_check_frequency': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-slate-500 focus:border-transparent'
            })
        }

    def clean_global_fuel_efficiency_benchmark(self):
        value = self.cleaned_data['global_fuel_efficiency_benchmark']
        if value <= 0:
            raise forms.ValidationError("Benchmark must be greater than 0.")
        return value

    def clean_per_trip_diesel_benchmark(self):
        value = self.cleaned_data['per_trip_diesel_benchmark']
        if value <= 0:
            raise forms.ValidationError("Benchmark must be greater than 0.")
        return value

    def clean_per_tonnage_diesel_benchmark(self):
        value = self.cleaned_data['per_tonnage_diesel_benchmark']
        if value <= 0:
            raise forms.ValidationError("Benchmark must be greater than 0.")
        return value

    def clean_fleet_efficiency_threshold_min(self):
        min_threshold = self.cleaned_data['fleet_efficiency_threshold_min']
        max_threshold = self.cleaned_data.get('fleet_efficiency_threshold_max')
        
        if min_threshold <= 0:
            raise forms.ValidationError("Minimum threshold must be greater than 0.")
        
        if max_threshold and min_threshold >= max_threshold:
            raise forms.ValidationError("Minimum threshold must be less than maximum threshold.")
        
        return min_threshold

    def clean_fleet_efficiency_threshold_max(self):
        max_threshold = self.cleaned_data['fleet_efficiency_threshold_max']
        min_threshold = self.cleaned_data.get('fleet_efficiency_threshold_min')
        
        if max_threshold <= 0:
            raise forms.ValidationError("Maximum threshold must be greater than 0.")
        
        if min_threshold and max_threshold <= min_threshold:
            raise forms.ValidationError("Maximum threshold must be greater than minimum threshold.")
        
        return max_threshold