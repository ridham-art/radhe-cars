from calendar import month_abbr

from django import forms
from django.contrib import admin
from django.contrib.admin import DateFieldListFilter
from django.http import JsonResponse
from django.urls import path, reverse

from .models import Brand, CarModel, Car, CarImage, Inquiry, Testimonial, Wishlist


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']


@admin.register(CarModel)
class CarModelAdmin(admin.ModelAdmin):
    list_display = ['name', 'brand']
    list_filter = ['brand']
    search_fields = ['name', 'brand__name']


class CarImageInline(admin.TabularInline):
    model = CarImage
    extra = 3
    max_num = 20
    min_num = 3


@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display = ['title', 'brand', 'model', 'year', 'model_month_abbr', 'price', 'fuel_type_label', 'transmission', 'status', 'is_featured', 'listed_at', 'created_at']
    list_filter = [
        'status',
        'is_featured',
        'fuel_type',
        'transmission',
        'body_type',
        'brand',
        'ownership',
        ('listed_at', DateFieldListFilter),
        ('created_at', DateFieldListFilter),
    ]
    search_fields = ['title', 'brand__name', 'model__name', 'variant']
    list_editable = ['status', 'is_featured']
    readonly_fields = ['created_at', 'updated_at', 'listed_at']
    inlines = [CarImageInline]
    change_form_template = 'admin/cars/car/change_form.html'

    @admin.display(description='Fuel')
    def fuel_type_label(self, obj):
        return obj.get_fuel_type_display()

    @admin.display(description='Month')
    def model_month_abbr(self, obj):
        if obj.model_month is None:
            return '—'
        return month_abbr[obj.model_month]

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == 'model_month':
            return forms.TypedChoiceField(
                required=False,
                choices=[('', '— No month —')] + [(str(i), month_abbr[i]) for i in range(1, 13)],
                coerce=lambda x: int(x) if x not in (None, '') else None,
                empty_value=None,
                label=db_field.verbose_name,
                help_text=db_field.help_text,
                widget=forms.Select(attrs={}),
            )
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    def get_urls(self):
        info = self.model._meta.app_label, self.model._meta.model_name
        return [
            path(
                'ajax-models/',
                self.admin_site.admin_view(self.ajax_models_by_brand),
                name='%s_%s_ajax_models' % info,
            ),
        ] + super().get_urls()

    def ajax_models_by_brand(self, request):
        brand_id = request.GET.get('brand')
        if not brand_id:
            return JsonResponse({'models': []})
        qs = CarModel.objects.filter(brand_id=brand_id).order_by('name')
        return JsonResponse({'models': [{'id': m.pk, 'name': str(m)} for m in qs]})

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'model':
            brand_id = None
            if request.method == 'POST':
                brand_id = request.POST.get('brand')
            if not brand_id and request.resolver_match:
                oid = request.resolver_match.kwargs.get('object_id')
                if oid:
                    brand_id = Car.objects.filter(pk=oid).values_list('brand_id', flat=True).first()
            if not brand_id:
                brand_id = request.GET.get('brand')
            if brand_id:
                kwargs['queryset'] = CarModel.objects.filter(brand_id=brand_id).order_by('name')
            else:
                kwargs['queryset'] = CarModel.objects.none()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['ajax_models_url'] = reverse(
            'admin:%s_%s_ajax_models' % (self.model._meta.app_label, self.model._meta.model_name)
        )
        return super().changeform_view(request, object_id, form_url, extra_context)

    fieldsets = (
        ('Basic Info', {
            'fields': ('title', 'brand', 'model', 'year', 'model_month', 'variant', 'color', 'description')
        }),
        ('Pricing', {
            'fields': ('price', 'original_price')
        }),
        ('Specifications', {
            'fields': ('mileage', 'fuel_type', 'transmission', 'body_type', 'ownership')
        }),
        ('Registration & Insurance', {
            'fields': ('registration_year', 'insurance_validity', 'insurance_type', 'rto')
        }),
        ('Location', {
            'fields': ('village_area', 'city')
        }),
        ('Seller', {
            'fields': ('seller', 'contact_name', 'contact_number')
        }),
        ('Status', {
            'fields': ('status', 'is_featured')
        }),
        ('Timestamps (admin only)', {
            'fields': ('listed_at', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


@admin.register(CarImage)
class CarImageAdmin(admin.ModelAdmin):
    list_display = ['car', 'is_primary', 'created_at']
    list_filter = ['is_primary']


@admin.register(Inquiry)
class InquiryAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'email', 'phone', 'subject', 'car', 'created_at']
    list_filter = ['subject', 'created_at']
    search_fields = ['first_name', 'last_name', 'email', 'phone']
    readonly_fields = ['created_at']


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ['name', 'designation', 'is_active', 'order']
    list_editable = ['is_active', 'order']
    list_filter = ['is_active']


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ['user', 'car', 'created_at']
    list_filter = ['created_at']
