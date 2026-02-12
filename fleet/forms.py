from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import UserCreationForm as DjangoUserCreationForm
from django.contrib.auth.models import User

from .models import Truck, Driver, FuelLog


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
