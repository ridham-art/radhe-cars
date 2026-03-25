from django.contrib import admin
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
    list_display = ['title', 'brand', 'model', 'year', 'price', 'fuel_type', 'transmission', 'status', 'is_featured', 'created_at']
    list_filter = ['status', 'is_featured', 'fuel_type', 'transmission', 'body_type', 'brand', 'ownership']
    search_fields = ['title', 'brand__name', 'model__name', 'variant']
    list_editable = ['status', 'is_featured']
    inlines = [CarImageInline]
    change_form_template = 'admin/cars/car/change_form.html'

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
            'fields': ('title', 'brand', 'model', 'year', 'variant', 'color', 'description')
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
