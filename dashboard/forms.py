from django import forms

from fleet.models import TireInventory, Truck

from .models import ReportSchedule


class BaseReportFilterForm(forms.Form):
    date_from = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    date_to = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'w-full px-4 py-2 border border-gray-300 rounded-xl'})


class FuelReportFilterForm(BaseReportFilterForm):
    truck = forms.ModelChoiceField(queryset=Truck.objects.all(), required=False)


class TireCostReportFilterForm(BaseReportFilterForm):
    truck = forms.ModelChoiceField(queryset=Truck.objects.all(), required=False)
    status = forms.ChoiceField(required=False, choices=[('', 'All')] + list(TireInventory.Status.choices))


class OperationsSummaryFilterForm(BaseReportFilterForm):
    truck = forms.ModelChoiceField(queryset=Truck.objects.all(), required=False)


class FleetStatusFilterForm(forms.Form):
    status = forms.ChoiceField(required=False, choices=[('', 'All')] + list(Truck.Status.choices))
    fleet_type = forms.ChoiceField(required=False, choices=[('', 'All')] + list(Truck.FleetType.choices))
    mining_type = forms.ChoiceField(required=False, choices=[('', 'All')] + list(Truck.MiningType.choices))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'w-full px-4 py-2 border border-gray-300 rounded-xl'})


class ReportScheduleForm(forms.ModelForm):
    class Meta:
        model = ReportSchedule
        fields = [
            'name',
            'report_type',
            'frequency',
            'output_format',
            'start_date',
            'filters',
            'email_recipients',
            'is_active',
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'filters': forms.Textarea(attrs={'rows': 3, 'placeholder': '{"date_from": "2024-01-01"}'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if field.widget.input_type == 'checkbox':
                field.widget.attrs.update({'class': 'h-4 w-4 text-slate-900 border-gray-300 rounded'})
            else:
                field.widget.attrs.update({'class': 'w-full px-4 py-2 border border-gray-300 rounded-xl'})
