from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Car, Inquiry


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': 'w-full bg-white border border-gray-200 rounded-lg py-3 px-4 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors shadow-sm'
            })


class ContactForm(forms.ModelForm):
    class Meta:
        model = Inquiry
        fields = ['first_name', 'last_name', 'email', 'phone', 'subject', 'message', 'car']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['car'].queryset = Car.objects.filter(status='APPROVED')
        self.fields['car'].required = False
        self.fields['car'].widget = forms.HiddenInput()
        base_class = 'w-full bg-white border border-gray-200 rounded-xl py-3 px-4 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors shadow-sm min-h-[44px]'
        self.fields['first_name'].widget.attrs.update({'class': base_class, 'placeholder': 'John'})
        self.fields['last_name'].widget.attrs.update({'class': base_class, 'placeholder': 'Doe'})
        self.fields['email'].widget.attrs.update({'class': base_class, 'placeholder': 'john@example.com'})
        self.fields['phone'].widget = forms.HiddenInput(attrs={'id': 'contact-phone'})
        self.fields['subject'].widget.attrs.update({
            'class': 'w-full appearance-none bg-white border border-gray-200 rounded-xl py-3 px-4 pr-10 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors shadow-sm cursor-pointer'
        })
        self.fields['message'].widget = forms.Textarea(attrs={
            'class': base_class + ' resize-none',
            'rows': 5,
            'placeholder': "Tell us more about what you're looking for..."
        })

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        digits = ''.join(c for c in phone if c.isdigit())
        if len(digits) == 10:
            return '+91' + digits
        if len(digits) == 12 and digits.startswith('91'):
            return '+' + digits
        if not digits:
            raise forms.ValidationError('Please enter a valid 10-digit phone number.')
        raise forms.ValidationError('Phone number must be exactly 10 digits.')


class SellCarForm(forms.ModelForm):
    class Meta:
        model = Car
        fields = [
            'title', 'brand', 'model', 'year', 'variant', 'price',
            'mileage', 'fuel_type', 'transmission', 'body_type',
            'ownership', 'color', 'city', 'village_area',
            'contact_name', 'contact_number', 'description'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        base_class = 'w-full bg-white border border-gray-200 rounded-lg py-3 px-4 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors shadow-sm'
        for field in self.fields.values():
            field.widget.attrs.update({'class': base_class})
