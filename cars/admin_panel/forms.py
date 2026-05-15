from calendar import month_abbr
from decimal import Decimal, InvalidOperation

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.utils.text import capfirst

from cars.models import Brand, Car, CarModel, CarModelVariant


class StaffAuthenticationForm(AuthenticationForm):
    """
    Django's AuthenticationForm.clean() calls authenticate(request, username, password)
    using AUTHENTICATION_BACKENDS (ModelBackend first). Then confirm_login_allowed()
    enforces is_staff for this panel.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        c = 'w-full border border-slate-200 rounded-lg px-3 py-2 text-sm'
        self.fields['username'].widget.attrs.update({'class': c, 'autocomplete': 'username'})
        self.fields['password'].widget.attrs.update({'class': c, 'autocomplete': 'current-password'})

    def clean(self):
        if self.cleaned_data.get('username'):
            self.cleaned_data['username'] = self.cleaned_data['username'].strip()
        return super().clean()

    def confirm_login_allowed(self, user):
        if not user.is_staff:
            raise ValidationError(
                'This account does not have staff access. Please use a staff login.',
                code='no_staff',
            )


class BrandForm(forms.ModelForm):
    class Meta:
        model = Brand
        fields = ['name', 'logo']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'ap-input'}),
        }


class BrandBulkForm(forms.Form):
    """Brand names separated by commas and/or newlines (POST field name: brands)."""

    brands = forms.CharField(
        label='Brand names',
        widget=forms.Textarea(
            attrs={
                'rows': 14,
                'class': 'ap-input font-mono text-sm',
                'placeholder': 'Honda, Hyundai, Tata\nor one per line',
            }
        ),
        help_text='Comma-separated and/or one per line. Existing names are skipped.',
    )


class CarModelBulkForm(forms.Form):
    """Model names comma- and/or newline-separated; POST field name: models."""

    brand = forms.ModelChoiceField(
        queryset=Brand.objects.order_by('name'),
        label='Brand',
        widget=forms.Select(attrs={'class': 'ap-input'}),
    )
    models = forms.CharField(
        label='Model names',
        widget=forms.Textarea(
            attrs={
                'rows': 14,
                'class': 'ap-input font-mono text-sm',
                'placeholder': 'City, Amaze, WR-V\nor one per line',
            }
        ),
        help_text='Comma-separated and/or one per line (same as models.split(",")). Duplicates for this brand are skipped.',
    )


class CarModelForm(forms.ModelForm):
    class Meta:
        model = CarModel
        fields = ['brand', 'name']
        widgets = {
            'brand': forms.Select(attrs={'class': 'ap-input'}),
            'name': forms.TextInput(attrs={'class': 'ap-input'}),
        }


VM_FUEL_OPTIONS = [
    ('Petrol', 'Petrol'),
    ('Diesel', 'Diesel'),
    ('Petrol + CNG', 'Petrol + CNG'),
    ('Electric', 'Electric'),
]


class VehicleMasterMakeForm(forms.ModelForm):
    class Meta:
        model = Brand
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'vm-input', 'placeholder': 'e.g. Mahindra'}),
        }


class VehicleMasterModelForm(forms.Form):
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'vm-input', 'placeholder': 'e.g. Creta'}),
    )
    supported_fuels = forms.MultipleChoiceField(
        choices=VM_FUEL_OPTIONS,
        widget=forms.CheckboxSelectMultiple,
        initial=['Petrol'],
    )

    def clean_supported_fuels(self):
        fuels = self.cleaned_data.get('supported_fuels') or []
        if not fuels:
            raise ValidationError('Select at least one fuel type.')
        return fuels


class VehicleMasterBrandBulkForm(forms.Form):
    brands = forms.CharField(
        label='Brand names',
        widget=forms.Textarea(
            attrs={
                'class': 'vm-textarea',
                'rows': 12,
                'placeholder': 'Honda, Hyundai, Tata\nor one per line',
            }
        ),
        help_text='One brand per line or comma-separated. Existing names are skipped.',
    )


class VehicleMasterBrandBulkDeleteForm(forms.Form):
    brands = forms.CharField(
        label='Brand names to delete',
        widget=forms.Textarea(
            attrs={
                'class': 'vm-textarea',
                'rows': 12,
                'placeholder': 'Audi\nBMW\nTata',
            }
        ),
        help_text='One brand per line or comma-separated. Brands in use by inventory are skipped.',
    )


class VehicleMasterModelBulkForm(forms.Form):
    models = forms.CharField(
        label='Model names',
        widget=forms.Textarea(
            attrs={
                'class': 'vm-textarea',
                'rows': 12,
                'placeholder': 'City, Amaze, WR-V\nor one per line',
            }
        ),
        help_text='One model per line or comma-separated. Duplicates for this brand are skipped.',
    )


class VehicleMasterModelBulkDeleteForm(forms.Form):
    models = forms.CharField(
        label='Model names to delete',
        widget=forms.Textarea(
            attrs={
                'class': 'vm-textarea',
                'rows': 12,
                'placeholder': 'City\nAmaze',
            }
        ),
        help_text='One model per line or comma-separated. Only models under the selected brand are removed.',
    )


class VehicleMasterVariantBulkForm(forms.Form):
    variants = forms.CharField(
        label='Variant names',
        widget=forms.Textarea(
            attrs={
                'class': 'vm-textarea',
                'rows': 12,
                'placeholder': 'LXi\nVXi\nZXi+\n\nOr: ZXi+ | Petrol | Automatic',
            }
        ),
        help_text=(
            'One variant per line, or comma-separated names. '
            'Optional per line: Name | Fuel | Transmission '
            '(e.g. ZXi+ | Petrol | Automatic). '
            'Names only default to the model’s first supported fuel and Manual.'
        ),
    )


class VehicleMasterVariantBulkDeleteForm(forms.Form):
    variants = forms.CharField(
        label='Variant names to delete',
        widget=forms.Textarea(
            attrs={
                'class': 'vm-textarea',
                'rows': 12,
                'placeholder': 'LXi\nVXi\nZXi+',
            }
        ),
        help_text='One variant name per line or comma-separated. Only variants under the selected model are removed.',
    )


class CarModelVariantForm(forms.ModelForm):
    class Meta:
        model = CarModelVariant
        fields = ['name', 'fuel_type', 'transmission']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'vm-input', 'placeholder': 'e.g. ZXi+'}),
            'fuel_type': forms.Select(attrs={'class': 'vm-input'}),
            'transmission': forms.Select(attrs={'class': 'vm-input'}),
        }

    def __init__(self, *args, car_model=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.car_model = car_model
        self.fields['fuel_type'].choices = list(CarModelVariant.FUEL_CHOICES)

    def clean_fuel_type(self):
        return self.cleaned_data['fuel_type']


class CarStaffForm(forms.ModelForm):
    class Meta:
        model = Car
        fields = [
            'seller',
            'title',
            'brand',
            'model',
            'year',
            'model_month',
            'variant',
            'price',
            'original_price',
            'mileage',
            'fuel_type',
            'transmission',
            'body_type',
            'ownership',
            'color',
            'registration_year',
            'insurance_validity',
            'insurance_type',
            'rto',
            'village_area',
            'city',
            'registration_state',
            'sell_timeline',
            'contact_name',
            'contact_number',
            'description',
            'is_featured',
            'status',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'ap-input'}),
            'variant': forms.TextInput(attrs={'class': 'ap-input'}),
            'year': forms.NumberInput(attrs={'class': 'ap-input'}),
            'price': forms.NumberInput(attrs={'class': 'ap-input', 'step': '0.01'}),
            'original_price': forms.NumberInput(attrs={'class': 'ap-input', 'step': '0.01'}),
            'mileage': forms.NumberInput(attrs={'class': 'ap-input'}),
            'fuel_type': forms.Select(attrs={'class': 'ap-input'}),
            'transmission': forms.Select(attrs={'class': 'ap-input'}),
            'body_type': forms.Select(attrs={'class': 'ap-input'}),
            'ownership': forms.Select(attrs={'class': 'ap-input'}),
            'color': forms.TextInput(attrs={'class': 'ap-input'}),
            'registration_year': forms.TextInput(attrs={'class': 'ap-input'}),
            'insurance_validity': forms.TextInput(attrs={'class': 'ap-input'}),
            'insurance_type': forms.TextInput(attrs={'class': 'ap-input'}),
            'rto': forms.TextInput(attrs={'class': 'ap-input'}),
            'village_area': forms.TextInput(attrs={'class': 'ap-input'}),
            'city': forms.TextInput(attrs={'class': 'ap-input'}),
            'registration_state': forms.TextInput(attrs={'class': 'ap-input'}),
            'sell_timeline': forms.TextInput(attrs={'class': 'ap-input'}),
            'contact_name': forms.TextInput(attrs={'class': 'ap-input'}),
            'contact_number': forms.TextInput(attrs={'class': 'ap-input'}),
            'description': forms.Textarea(attrs={'class': 'ap-input', 'rows': 4}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'ap-checkbox'}),
            'status': forms.Select(attrs={'class': 'ap-input'}),
            'brand': forms.Select(attrs={'class': 'ap-input', 'id': 'id_brand'}),
            'model': forms.Select(attrs={'class': 'ap-input', 'id': 'id_model'}),
            'seller': forms.Select(attrs={'class': 'ap-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        mo_f = Car._meta.get_field('model_month')
        _mlbl = mo_f.verbose_name and capfirst(mo_f.verbose_name) or 'Model month'
        self.fields['model_month'] = forms.TypedChoiceField(
            label=_mlbl,
            required=False,
            choices=[('', '— No month —')] + [(str(i), month_abbr[i]) for i in range(1, 13)],
            coerce=lambda x: int(x) if x not in (None, '') else None,
            empty_value=None,
            widget=forms.Select(attrs={'class': 'ap-input'}),
            help_text=mo_f.help_text,
        )
        self.fields['seller'].required = False
        self.fields['seller'].queryset = self.fields['seller'].queryset.order_by('username')
        brand_id = None
        if self.data.get('brand'):
            try:
                brand_id = int(self.data.get('brand'))
            except (TypeError, ValueError):
                pass
        elif self.instance and self.instance.pk and self.instance.brand_id:
            brand_id = self.instance.brand_id
        if brand_id:
            self.fields['model'].queryset = CarModel.objects.filter(brand_id=brand_id).order_by('name')
        else:
            self.fields['model'].queryset = CarModel.objects.none()


class CarStaffFormPreview(CarStaffForm):
    """Same fields as CarStaffForm; widgets styled for base_new car form preview."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'cf-checkbox'
            else:
                field.widget.attrs['class'] = 'cf-input'
        self.fields['variant'].widget.attrs.setdefault(
            'placeholder', 'Or type a custom variant name'
        )


class CSVUploadForm(forms.Form):
    file = forms.FileField(
        label='CSV file',
        widget=forms.ClearableFileInput(attrs={'class': 'ap-input', 'accept': '.csv'}),
    )
    replace_all = forms.BooleanField(
        required=False,
        label='Replace all cars (dangerous — deletes every car first)',
    )


class CSVUploadFormPreview(CSVUploadForm):
    """CSV upload widgets styled for base_new preview."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['file'].widget = forms.FileInput(
            attrs={'class': 'csv-file-native', 'accept': '.csv'},
        )
        self.fields['replace_all'].widget.attrs['class'] = 'cf-checkbox'


class CSVConfirmForm(forms.Form):
    confirm_replace = forms.CharField(required=False, widget=forms.HiddenInput())


def parse_bool(val):
    if val is None or val == '':
        return False
    s = str(val).strip().lower()
    return s in ('1', 'true', 'yes', 'y')


def parse_decimal(val):
    if val is None or str(val).strip() == '':
        raise ValueError('Empty price')
    try:
        return Decimal(str(val).replace(',', '').strip())
    except (InvalidOperation, ValueError) as e:
        raise ValueError(f'Invalid number: {val}') from e


def parse_int(val):
    if val is None or str(val).strip() == '':
        raise ValueError('Empty integer')
    return int(float(str(val).strip()))


def parse_model_month(val):
    """Return month 1–12 or None. Accepts digits or three-letter month (Jan, Feb, …)."""
    if val is None or str(val).strip() == '':
        return None
    s = str(val).strip()
    if s.isdigit():
        m = int(s)
        if 1 <= m <= 12:
            return m
        return None
    pre = s[:3].lower()
    for i in range(1, 13):
        if month_abbr[i].lower() == pre:
            return i
    return None
