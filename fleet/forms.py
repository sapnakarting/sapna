from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import UserCreationForm as DjangoUserCreationForm
from django.contrib.auth.models import User
from django.utils import timezone
from django.forms import formset_factory, BaseFormSet

from .models import Truck, Driver, FuelLog, TireInventory, Alert, DailyOdoRegistry


class LoginForm(forms.Form):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-slate-500 focus:border-transparent',
            'placeholder': 'Username',
            'autofocus': True
        }),
        label='Username'
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-slate-500 focus:border-transparent',
            'placeholder': 'Password'
        }),
        label='Password'
    )

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')

        if username and password:
            user = authenticate(username=username, password=password)
            if user is None:
                raise forms.ValidationError('Invalid username or password.')
            if not user.is_active:
                raise forms.ValidationError('This account is inactive.')

            # Check if user has a profile
            if not hasattr(user, 'userprofile'):
                raise forms.ValidationError('User profile not found. Please contact administrator.')

            cleaned_data['user'] = user

        return cleaned_data


class UserCreationForm(DjangoUserCreationForm):
    role = forms.ChoiceField(
        choices=[('ADMIN', 'Admin'), ('FUEL_AGENT', 'Fuel Agent')],
        initial='FUEL_AGENT',
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-slate-500 focus:border-transparent'
        })
    )
    phone = forms.CharField(
        required=False,
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-slate-500 focus:border-transparent',
            'placeholder': 'Phone number (optional)'
        })
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-slate-500 focus:border-transparent'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-slate-500 focus:border-transparent'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-slate-500 focus:border-transparent'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-slate-500 focus:border-transparent'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-slate-500 focus:border-transparent'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-slate-500 focus:border-transparent'
        })
        # For editing, make passwords optional
        if self.instance and self.instance.pk:
            self.fields['password1'].required = False
            self.fields['password2'].required = False
            self.fields['password1'].help_text = "Leave blank to keep the current password"


class TruckForm(forms.ModelForm):
    class Meta:
        model = Truck
        fields = [
            'plate_number', 'transporter_name', 'wheel_config',
            'fleet_type', 'mining_type', 'current_odometer',
            'status', 'remarks',
            'fitness_expiry', 'insurance_expiry', 'pucc_expiry',
            'tax_expiry', 'permit_expiry'
        ]
        widgets = {
            'fitness_expiry': forms.DateInput(attrs={'type': 'date'}),
            'insurance_expiry': forms.DateInput(attrs={'type': 'date'}),
            'pucc_expiry': forms.DateInput(attrs={'type': 'date'}),
            'tax_expiry': forms.DateInput(attrs={'type': 'date'}),
            'permit_expiry': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'w-full px-4 py-2 border border-gray-300 rounded-xl'})

    def clean_plate_number(self):
        plate = self.cleaned_data['plate_number']
        plate = plate.upper().strip()
        # Check uniqueness if editing existing truck
        if self.instance.pk:
            if Truck.objects.filter(plate_number=plate).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError("A truck with this plate number already exists.")
        else:
            if Truck.objects.filter(plate_number=plate).exists():
                raise forms.ValidationError("A truck with this plate number already exists.")
        return plate

    def save(self, commit=True):
        truck = super().save(commit=False)
        truck.plate_number = truck.plate_number.upper().strip()
        if commit:
            truck.save()
        return truck


class TruckSearchForm(forms.Form):
    search = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'placeholder': 'Plate number or transporter name...',
        'class': 'w-full px-4 py-2 border border-gray-300 rounded-xl'
    }))

    fleet_type = forms.ChoiceField(required=False, choices=[
        ('', 'All'),
        ('COAL', 'COAL'),
        ('MINING', 'MINING')
    ], widget=forms.Select(attrs={'class': 'w-full px-4 py-2 border border-gray-300 rounded-xl'}))

    status = forms.ChoiceField(required=False, choices=[
        ('', 'All'),
        ('ACTIVE', 'ACTIVE'),
        ('INACTIVE', 'INACTIVE'),
        ('MAINTENANCE', 'MAINTENANCE')
    ], widget=forms.Select(attrs={'class': 'w-full px-4 py-2 border border-gray-300 rounded-xl'}))

    wheel_config = forms.ChoiceField(required=False, choices=[
        ('', 'All'),
        ('10_WHEEL', '10-WHEEL'),
        ('14_WHEEL', '14-WHEEL'),
        ('16_WHEEL', '16-WHEEL')
    ], widget=forms.Select(attrs={'class': 'w-full px-4 py-2 border border-gray-300 rounded-xl'}))


class DriverForm(forms.ModelForm):
    class Meta:
        model = Driver
        fields = ['name', 'license_number', 'phone', 'status', 'driver_type']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'w-full px-4 py-2 border border-gray-300 rounded-xl'})

    def clean_license_number(self):
        license_no = self.cleaned_data['license_number']
        license_no = license_no.upper().strip()
        if self.instance.pk:
            if Driver.objects.filter(license_number=license_no).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError("A driver with this license number already exists.")
        else:
            if Driver.objects.filter(license_number=license_no).exists():
                raise forms.ValidationError("A driver with this license number already exists.")
        return license_no

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '')
        if phone and not phone.isdigit():
            raise forms.ValidationError("Phone number must contain only digits.")
        return phone

    def save(self, commit=True):
        driver = super().save(commit=False)
        driver.license_number = driver.license_number.upper().strip()
        if commit:
            driver.save()
        return driver


class FuelLogForm(forms.ModelForm):
    class Meta:
        model = FuelLog
        fields = ['truck', 'driver', 'date', 'entry_type', 'odometer',
                  'fuel_liters', 'diesel_price', 'verification_photos']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'truck': forms.Select(attrs={'class': 'w-full px-4 py-2 border border-gray-300 rounded-xl'}),
            'driver': forms.Select(attrs={'class': 'w-full px-4 py-2 border border-gray-300 rounded-xl'}),
            'entry_type': forms.RadioSelect(attrs={
                'class': 'flex space-x-4',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name not in ['verification_photos']:
                field.widget.attrs.update({'class': 'w-full px-4 py-2 border border-gray-300 rounded-xl'})

    def clean_odometer(self):
        odometer = self.cleaned_data['odometer']
        truck = self.cleaned_data.get('truck')
        if truck and odometer < truck.current_odometer:
            raise forms.ValidationError(f"Odometer reading ({odometer}) is less than truck's current ODO ({truck.current_odometer})")
        return odometer

    def save(self, commit=True):
        fuel_log = super().save(commit=False)
        # Calculate attribution date based on entry type
        from .utils.fuel_attribution import calculate_attribution_date
        fuel_log.attribution_date = calculate_attribution_date(fuel_log.date, fuel_log.entry_type)
        # Calculate fuel cost
        fuel_log.fuel_cost = (fuel_log.fuel_liters or 0) * (fuel_log.diesel_price or 0)
        # Set fueling agent
        fuel_log.fueling_agent = self.request.user if hasattr(self, 'request') else None
        if commit:
            fuel_log.save()
        return fuel_log


class DieselPriceForm(forms.Form):
    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    price = forms.DecimalField(max_digits=6, decimal_places=2, widget=forms.NumberInput(attrs={
        'placeholder': 'Price per liter (₹)',
        'class': 'w-full px-4 py-2 border border-gray-300 rounded-xl'
    }))

    def clean_price(self):
        price = self.cleaned_data['price']
        if price <= 0:
            raise forms.ValidationError("Price must be greater than 0.")
        return price


class TireInventoryForm(forms.ModelForm):
    class Meta:
        model = TireInventory
        fields = [
            'serial_number', 'brand', 'status', 'truck', 'position',
            'purchase_cost', 'mounting_cost', 'repair_costs',
            'mounted_at_odometer', 'scrap_reason'
        ]
        widgets = {
            'purchase_cost': forms.NumberInput(attrs={'step': '0.01'}),
            'mounting_cost': forms.NumberInput(attrs={'step': '0.01'}),
            'repair_costs': forms.NumberInput(attrs={'step': '0.01'}),
            'mounted_at_odometer': forms.NumberInput(attrs={'min': 0}),
            'truck': forms.Select(attrs={'class': 'w-full px-4 py-2 border border-gray-300 rounded-xl'}),
            'position': forms.Select(attrs={'class': 'w-full px-4 py-2 border border-gray-300 rounded-xl'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name not in ['mounted_at_odometer', 'scrap_reason']:
                field.widget.attrs.update({'class': 'w-full px-4 py-2 border border-gray-300 rounded-xl'})

    def clean_serial_number(self):
        serial = self.cleaned_data['serial_number'].upper().strip()
        self.cleaned_data['serial_number'] = serial

        # Check uniqueness if editing
        if self.instance.pk:
            if TireInventory.objects.filter(serial_number=serial).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError("A tire with this serial number already exists.")
        else:
            if TireInventory.objects.filter(serial_number=serial).exists():
                raise forms.ValidationError("A tire with this serial number already exists.")
        return serial

    def clean_mounted_at_odometer(self):
        odo = self.cleaned_data['mounted_at_odometer']
        truck = self.cleaned_data.get('truck')

        if truck and odo and odo < truck.current_odometer:
            raise forms.ValidationError(f"Mounting ODO ({odo}) is less than truck's current ODO ({truck.current_odometer})")
        return odo

    def clean(self):
        cleaned_data = super().clean()

        # Validate mount action
        status = cleaned_data.get('status')
        if status == 'MOUNTED':
            if not cleaned_data.get('truck'):
                self.add_error('truck', 'Truck must be selected for mounting.')
            if not cleaned_data.get('position'):
                self.add_error('position', 'Position must be selected for mounting.')
            if not cleaned_data.get('mounted_at_odometer'):
                self.add_error('mounted_at_odometer', 'Odometer reading is required for mounting.')

        # Validate repair action
        if status == 'REPAIR':
            if not cleaned_data.get('repair_costs'):
                cleaned_data['repair_costs'] = 0

        # Validate scrap action
        if status == 'SCRAPPED':
            if not cleaned_data.get('scrap_reason'):
                self.add_error('scrap_reason', 'Scrap reason is required for scrapping.')

        return cleaned_data

    def save(self, commit=True):
        tire = super().save(commit=False)

        # Add history entry for status change
        status = tire.status
        event = {
            'status': status,
            'date': timezone.now().isoformat(),
        }

        if status == 'MOUNTED':
            event['odometer'] = tire.mounted_at_odometer
            event['reason'] = f'Mounted at position {tire.position} on {tire.truck.plate_number}'

        elif status == 'REPAIR':
            event['reason'] = f'Repair done. Cost: ₹{tire.repair_costs}'

        elif status == 'SCRAPPED':
            event['reason'] = f'Scrapped. Reason: {tire.scrap_reason}'

        if not tire.history:
            tire.history = []

        tire.history.append(event)

        # Update truck odometer if mounting
        if status == 'MOUNTED' and tire.truck and tire.mounted_at_odometer:
            tire.truck.current_odometer = tire.mounted_at_odometer
            tire.truck.save()

        if commit:
            tire.save()
        return tire


class TireActionForm(forms.Form):
    ACTION_CHOICES = [
        ('MOUNT', 'Mount Tire'),
        ('UNMOUNT', 'Unmount Tire'),
        ('REPAIR', 'Repair Tire'),
        ('SCRAP', 'Scrap Tire'),
    ]

    action = forms.ChoiceField(choices=ACTION_CHOICES)
    truck = forms.ModelChoiceField(queryset=Truck.objects.all(), required=False)
    truck_odometer = forms.IntegerField(required=False, widget=forms.NumberInput(attrs={
        'placeholder': 'Current ODO reading',
        'class': 'w-full px-4 py-2 border border-gray-300 rounded-xl'
    }))
    position = forms.ChoiceField(choices=[
        ('FL', 'Front Left (FL)'),
        ('FR', 'Front Right (FR)'),
        ('R1 Left Outside', 'R1 Left Outside'),
        ('R1 Left Inside', 'R1 Left Inside'),
        ('R1 Right Inside', 'R1 Right Inside'),
        ('R1 Right Outside', 'R1 Right Outside'),
        ('R2 Left Outside', 'R2 Left Outside'),
        ('R2 Left Inside', 'R2 Left Inside'),
        ('R2 Right Inside', 'R2 Right Inside'),
        ('R2 Right Outside', 'R2 Right Outside'),
        ('R3 Left Outside', 'R3 Left Outside'),
        ('R3 Left Inside', 'R3 Left Inside'),
        ('R3 Right Inside', 'R3 Right Inside'),
        ('R3 Right Outside', 'R3 Right Outside'),
        ('R4 Left Outside', 'R4 Left Outside'),
        ('R4 Left Inside', 'R4 Left Inside'),
        ('R4 Right Inside', 'R4 Right Inside'),
        ('R4 Right Outside', 'R4 Right Outside'),
    ], required=False)
    repair_cost = forms.DecimalField(required=False, widget=forms.NumberInput(attrs={
        'placeholder': 'Repair Cost (₹)',
        'step': '0.01',
        'class': 'w-full px-4 py-2 border border-gray-300 rounded-xl'
    }))
    scrap_reason = forms.CharField(widget=forms.Textarea(attrs={
        'placeholder': 'Scrap reason',
        'rows': 3,
        'class': 'w-full px-4 py-2 border border-gray-300 rounded-xl'
    }), required=False)
    remarks = forms.CharField(widget=forms.Textarea(attrs={
        'placeholder': 'Remarks',
        'rows': 3,
        'class': 'w-full px-4 py-2 border border-gray-300 rounded-xl'
    }), required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name not in ['action']:
                field.widget.attrs.update({'class': 'w-full px-4 py-2 border border-gray-300 rounded-xl'})


class TireSearchForm(forms.Form):
    STATUS_CHOICES = [
        ('', 'All'),
        ('NEW', 'NEW'),
        ('MOUNTED', 'MOUNTED'),
        ('SPARE', 'SPARE'),
        ('REPAIR', 'REPAIR'),
        ('SCRAPPED', 'SCRAPPED'),
    ]

    search = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'placeholder': 'Serial number, brand, or truck plate...',
        'class': 'w-full px-4 py-2 border border-gray-300 rounded-xl'
    }))

    status_filter = forms.ChoiceField(choices=STATUS_CHOICES, required=False)
    truck_filter = forms.ModelChoiceField(queryset=Truck.objects.all(), required=False)

    sort_by = forms.ChoiceField(choices=[
        ('serial_number', 'Serial Number'),
        ('purchase_cost', 'Cost'),
        ('created_at', 'Recently Added'),
    ], required=False, initial='serial_number')


class AlertUpdateForm(forms.ModelForm):
    class Meta:
        model = Alert
        fields = ['status', 'resolution_notes']
        widgets = {
            'status': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-slate-500 focus:border-transparent'
            }),
            'resolution_notes': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-slate-500 focus:border-transparent',
                'rows': 4,
                'placeholder': 'Enter resolution notes or dismissal reason...'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make resolution notes required only when changing to resolved/dismissed
        if self.instance and self.instance.status in [Alert.AlertStatus.RESOLVED, Alert.AlertStatus.DISMISSED]:
            self.fields['resolution_notes'].required = True
        else:
            self.fields['resolution_notes'].required = False


class DailyOdoRegistryForm(forms.ModelForm):
    class Meta:
        model = DailyOdoRegistry
        fields = ['truck', 'date', 'opening_odometer', 'closing_odometer', 'remarks']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'truck': forms.Select(attrs={'class': 'w-full px-4 py-2 border border-gray-300 rounded-xl'}),
            'remarks': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-xl',
                'rows': 3,
                'placeholder': 'Any remarks or notes...'
            })
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        for field_name, field in self.fields.items():
            if field_name not in ['remarks']:
                field.widget.attrs.update({'class': 'w-full px-4 py-2 border border-gray-300 rounded-xl'})
        
        # Auto-populate opening odometer from truck's current odometer
        if 'truck' in self.data:
            truck_id = self.data.get('truck')
            try:
                truck = Truck.objects.get(pk=truck_id)
                self.fields['opening_odometer'].initial = truck.current_odometer
            except (Truck.DoesNotExist, ValueError):
                pass
        elif self.instance and self.instance.pk:
            # For existing instances, keep the original opening odometer
            pass
        elif self.initial.get('truck'):
            truck = self.initial['truck']
            if isinstance(truck, Truck):
                self.fields['opening_odometer'].initial = truck.current_odometer

    def clean(self):
        cleaned_data = super().clean()
        opening_odometer = cleaned_data.get('opening_odometer')
        closing_odometer = cleaned_data.get('closing_odometer')
        truck = cleaned_data.get('truck')
        date = cleaned_data.get('date')
        
        # Validate closing >= opening
        if opening_odometer is not None and closing_odometer is not None:
            if closing_odometer < opening_odometer:
                self.add_error('closing_odometer', 'Closing odometer must be greater than or equal to opening odometer.')
        
        # Check for duplicate entries (same truck, same date)
        if truck and date:
            existing = DailyOdoRegistry.objects.filter(truck=truck, date=date)
            if self.instance and self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                self.add_error('date', f'A daily odometer entry already exists for {truck.plate_number} on {date}.')
        
        return cleaned_data


class DailyOdoRegistrySearchForm(forms.Form):
    truck = forms.ModelChoiceField(
        queryset=Truck.objects.all(),
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-xl'
        })
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'w-full px-4 py-2 border border-gray-300 rounded-xl'})
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'w-full px-4 py-2 border border-gray-300 rounded-xl'})
    )
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-xl',
            'placeholder': 'Search remarks...'
        })
    )


class BulkDailyOdoEntryForm(forms.Form):
    truck_id = forms.IntegerField(widget=forms.HiddenInput())
    truck_name = forms.CharField(disabled=True, required=False, widget=forms.TextInput(attrs={
        'class': 'w-full px-4 py-2 border border-gray-300 rounded-xl bg-gray-100'
    }))
    opening_odometer = forms.IntegerField(disabled=True, required=False, widget=forms.NumberInput(attrs={
        'class': 'w-full px-4 py-2 border border-gray-300 rounded-xl bg-gray-100'
    }))
    closing_odometer = forms.IntegerField(required=False, widget=forms.NumberInput(attrs={
        'class': 'w-full px-4 py-2 border border-gray-300 rounded-xl',
        'min': 0
    }))
    skip = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={
        'class': 'h-4 w-4 text-slate-600 border-gray-300 rounded'
    }))
    remarks = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'class': 'w-full px-4 py-2 border border-gray-300 rounded-xl',
        'placeholder': 'Remarks...'
    }))

    def __init__(self, *args, **kwargs):
        self.truck = kwargs.pop('truck', None)
        super().__init__(*args, **kwargs)
        
        if self.truck:
            self.fields['truck_id'].initial = self.truck.pk
            self.fields['truck_name'].initial = self.truck.plate_number
            self.fields['opening_odometer'].initial = self.truck.current_odometer

    def clean(self):
        cleaned_data = super().clean()
        opening_odometer = cleaned_data.get('opening_odometer')
        closing_odometer = cleaned_data.get('closing_odometer')
        skip = cleaned_data.get('skip', False)
        
        # If skip is checked, no validation needed
        if skip:
            return cleaned_data
        
        # Validate closing odometer
        if closing_odometer is not None and opening_odometer is not None:
            if closing_odometer < opening_odometer:
                self.add_error('closing_odometer', 'Closing odometer must be greater than or equal to opening odometer.')
        
        return cleaned_data


class BulkDailyOdoEntryFormSet(BaseFormSet):
    def __init__(self, *args, **kwargs):
        self.date = kwargs.pop('date', None)
        super().__init__(*args, **kwargs)
    
    def clean(self):
        """Validate that no duplicate trucks exist in the formset"""
        if any(self.errors):
            return
        
        truck_ids = []
        for form in self.forms:
            if not form.cleaned_data.get('skip', False):
                truck_id = form.cleaned_data.get('truck_id')
                if truck_id in truck_ids:
                    form.add_error('truck_id', 'Duplicate truck in bulk entry.')
                truck_ids.append(truck_id)
        
        # Check for existing entries on the same date
        if self.date and truck_ids:
            existing_entries = DailyOdoRegistry.objects.filter(
                date=self.date,
                truck_id__in=truck_ids
            )
            
            for entry in existing_entries:
                for form in self.forms:
                    if form.cleaned_data.get('truck_id') == entry.truck_id and not form.cleaned_data.get('skip', False):
                        form.add_error('truck_id', f'An entry already exists for {entry.truck.plate_number} on {self.date}.')
