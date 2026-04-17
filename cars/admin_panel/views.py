import json
import logging
import os
import re
import tempfile
from datetime import datetime, time
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.conf import settings
from django.contrib.auth.views import LoginView, LogoutView
from django.http import Http404, HttpResponseRedirect
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.paginator import EmptyPage
from django.db.models import Q, Count, Prefetch
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (
    TemplateView,
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
    FormView,
)

from cars.models import Brand, Car, CarModel, CarImage, Inquiry, Wishlist, _safe_delete_stored_file
from cars.admin_panel.forms import (
    BrandBulkForm,
    BrandForm,
    CarModelBulkForm,
    CarModelForm,
    CarStaffForm,
    CSVUploadForm,
    StaffAuthenticationForm,
)
from cars.admin_panel import csv_io
from cars.admin_panel.cache_utils import get_cached_nav_counts, invalidate_admin_nav_counts_cache

logger = logging.getLogger('cars.admin_panel.auth')

ADMIN_PRIMARY_IMAGE_PREFETCH = Prefetch(
    'images',
    queryset=CarImage.objects.filter(is_primary=True).only(
        'id', 'car_id', 'image', 'image_url', 'is_primary'
    ),
)


def filter_car_list_queryset(request):
    """
    Cars shown on the staff panel list (excludes sell-form inquiries).
    Supports search, brand, fuel, status, not_sold, and listed_at date range (date_from / date_to, YYYY-MM-DD).
    """
    qs = (
        Car.objects.select_related('brand', 'model')
        .prefetch_related(ADMIN_PRIMARY_IMAGE_PREFETCH)
        .exclude(submit_via_sell_form=True)
    )
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(model__name__icontains=q))
    brand = request.GET.get('brand')
    if brand:
        qs = qs.filter(brand_id=brand)
    fuel = request.GET.get('fuel')
    if fuel:
        qs = qs.filter(fuel_type=fuel)
    status = request.GET.get('status')
    if status:
        qs = qs.filter(status=status)
    elif request.GET.get('not_sold') == '1':
        qs = qs.exclude(status='SOLD')

    tz = timezone.get_current_timezone()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()
    if date_from:
        try:
            d = datetime.strptime(date_from, '%Y-%m-%d').date()
            start_dt = timezone.make_aware(datetime.combine(d, time.min), tz)
            qs = qs.filter(listed_at__gte=start_dt)
        except ValueError:
            pass
    if date_to:
        try:
            d = datetime.strptime(date_to, '%Y-%m-%d').date()
            end_dt = timezone.make_aware(datetime.combine(d, time.max), tz)
            qs = qs.filter(listed_at__lte=end_dt)
        except ValueError:
            pass

    return qs.order_by('-created_at')


def car_list_querystring_except_page(request):
    """Preserve filters for pagination and CSV links (drops page)."""
    p = request.GET.copy()
    p.pop('page', None)
    return urlencode(p)


def _parse_bulk_list(text):
    """Split on commas and/or newlines; strip; preserve order; dedupe exact strings."""
    if not text:
        return []
    text = text.replace('\r', '')
    parts = re.split(r'[,\n]+', text)
    out = []
    seen = set()
    for p in parts:
        n = p.strip()
        if not n or n in seen:
            continue
        seen.add(n)
        out.append(n)
    return out


def _resolve_primary_image_id(choice, car, created_images):
    if not choice:
        return None
    choice = str(choice).strip()
    if choice.startswith('existing:'):
        raw_id = choice.split(':', 1)[1]
        if raw_id.isdigit():
            image_id = int(raw_id)
            if car.images.filter(pk=image_id).exists():
                return image_id
        return None
    if choice.startswith('new:'):
        raw_idx = choice.split(':', 1)[1]
        if raw_idx.isdigit():
            idx = int(raw_idx)
            if 0 <= idx < len(created_images):
                return created_images[idx].pk
        return None
    return None


def _save_car_images_with_primary(request, car):
    files = [f for f in request.FILES.getlist('images') if f]
    created_images = []
    for f in files:
        created_images.append(
            CarImage.objects.create(
                car=car,
                image=f,
                is_primary=False,
            )
        )

    selected_primary_id = _resolve_primary_image_id(
        request.POST.get('primary_image_choice'),
        car,
        created_images,
    )
    if selected_primary_id:
        CarImage.objects.filter(car_id=car.pk).update(is_primary=False)
        CarImage.objects.filter(car_id=car.pk, pk=selected_primary_id).update(is_primary=True)
        return

    if not car.images.filter(is_primary=True).exists():
        first = CarImage.objects.filter(car_id=car.pk).order_by('id').first()
        if first:
            CarImage.objects.filter(car_id=car.pk).update(is_primary=False)
            CarImage.objects.filter(pk=first.pk).update(is_primary=True)

# Force username/password auth to ModelBackend (avoids ambiguity with allauth backends).
_MODEL_BACKEND = 'django.contrib.auth.backends.ModelBackend'


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    login_url = '/admin-panel/login/'

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_staff


class AdminPanelContextMixin:
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(get_cached_nav_counts())
        return ctx


class StaffLoginView(LoginView):
    template_name = 'admin_panel/login.html'
    authentication_form = StaffAuthenticationForm
    redirect_authenticated_user = True

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Show exact dev credentials only when DEBUG (hidden in production)
        ctx['show_staff_demo_login'] = settings.DEBUG
        return ctx

    def form_valid(self, form):
        """
        AuthenticationForm already ran authenticate(); establish session with a
        single explicit backend so the session stores BACKEND_SESSION_KEY correctly.
        """
        login(self.request, form.get_user(), backend=_MODEL_BACKEND)
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form):
        self._log_staff_login_failure(form)
        return super().form_invalid(form)

    def _log_staff_login_failure(self, form):
        """Diagnose failed staff login (does not log passwords)."""
        username = (form.data.get('username') or '').strip()
        if not username:
            logger.warning('admin_panel.login: empty username')
            return
        User = get_user_model()
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            logger.warning('admin_panel.login: user not found username=%r', username)
            return
        if not user.is_active:
            logger.warning('admin_panel.login: user inactive username=%r', username)
            return
        pwd = form.data.get('password') or ''
        if not user.check_password(pwd):
            logger.warning(
                'admin_panel.login: password incorrect for username=%r (run create_staff_user if needed)',
                username,
            )
            return
        if not user.is_staff:
            logger.warning('admin_panel.login: user is not staff username=%r', username)
            return
        logger.warning(
            'admin_panel.login: form invalid for username=%r errors=%s',
            username,
            form.errors,
        )

    def get_success_url(self):
        n = self.request.GET.get('next')
        if n:
            return n
        return reverse('admin_panel:dashboard')


class StaffLogoutView(LogoutView):
    http_method_names = ['get', 'post', 'options']
    next_page = '/admin-panel/login/'


class SafePagePaginationMixin:
    """Invalid ?page= falls back to page 1 instead of raising Http404."""

    def paginate_queryset(self, queryset, page_size):
        paginator = self.get_paginator(
            queryset,
            page_size,
            orphans=self.get_paginate_orphans(),
            allow_empty_first_page=self.get_allow_empty(),
        )
        page_kwarg = self.page_kwarg
        raw = self.request.GET.get(page_kwarg) or 1
        try:
            page_number = int(raw)
        except (TypeError, ValueError):
            page_number = 1
        if page_number < 1:
            page_number = 1
        try:
            page = paginator.page(page_number)
        except EmptyPage:
            page = paginator.page(1)
        return (paginator, page, page.object_list, page.has_other_pages())


class DashboardView(StaffRequiredMixin, AdminPanelContextMixin, TemplateView):
    template_name = 'admin_panel/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        User = get_user_model()
        car_stats = Car.objects.aggregate(
            total_cars=Count('pk'),
            active_cars=Count('pk', filter=~Q(status='SOLD')),
            sold_cars=Count('pk', filter=Q(status='SOLD')),
        )
        inq_stats = Inquiry.objects.aggregate(
            total_inquiries=Count('pk'),
            unread_inquiries=Count('pk', filter=Q(is_read=False)),
        )
        wish_stats = Wishlist.objects.filter(user__isnull=False).aggregate(
            total_wishlist_saves=Count('pk'),
            customers_with_wishlist=Count('user_id', distinct=True),
        )
        ctx.update(
            {
                **car_stats,
                **inq_stats,
                'total_customers': User.objects.filter(is_staff=False).count(),
                **wish_stats,
            }
        )
        return ctx


class CustomerListView(
    StaffRequiredMixin,
    AdminPanelContextMixin,
    SafePagePaginationMixin,
    ListView,
):
    """Website sign-ups (non-staff). Newest first."""

    template_name = 'admin_panel/customer_list.html'
    context_object_name = 'customers'
    paginate_by = 25

    def get_queryset(self):
        User = get_user_model()
        qs = User.objects.filter(is_staff=False).order_by('-date_joined')
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(email__icontains=q)
                | Q(username__icontains=q)
                | Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
            )
        if self.request.GET.get('has_wishlist') == '1':
            qs = qs.filter(wishlist__isnull=False).distinct()
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['search_q'] = self.request.GET.get('q', '')
        ctx['filter_has_wishlist'] = self.request.GET.get('has_wishlist') == '1'
        return ctx


class WishlistActivityListView(
    StaffRequiredMixin,
    AdminPanelContextMixin,
    SafePagePaginationMixin,
    ListView,
):
    """Cars saved by logged-in users. Newest first."""

    model = Wishlist
    template_name = 'admin_panel/wishlist_list.html'
    context_object_name = 'wishlists'
    paginate_by = 25

    def get_queryset(self):
        qs = (
            Wishlist.objects.filter(user__isnull=False)
            .select_related('user', 'car')
            .order_by('-created_at')
        )
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(user__email__icontains=q)
                | Q(user__username__icontains=q)
                | Q(car__title__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['search_q'] = self.request.GET.get('q', '')
        return ctx


class CarListView(
    StaffRequiredMixin,
    AdminPanelContextMixin,
    SafePagePaginationMixin,
    ListView,
):
    model = Car
    template_name = 'admin_panel/car_list.html'
    context_object_name = 'cars'
    paginate_by = 25

    def get_queryset(self):
        return filter_car_list_queryset(self.request)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['brands'] = Brand.objects.all()
        ctx['fuel_types'] = Car.FUEL_CHOICES
        ctx['statuses'] = Car.STATUS_CHOICES
        ctx['search_q'] = self.request.GET.get('q', '')
        _b = self.request.GET.get('brand')
        ctx['filter_brand'] = int(_b) if _b and str(_b).isdigit() else None
        ctx['filter_fuel'] = self.request.GET.get('fuel', '')
        ctx['filter_status'] = self.request.GET.get('status', '')
        ctx['filter_not_sold'] = self.request.GET.get('not_sold') == '1'
        ctx['filter_date_from'] = self.request.GET.get('date_from', '')
        ctx['filter_date_to'] = self.request.GET.get('date_to', '')
        ctx['car_list_querystring'] = car_list_querystring_except_page(self.request)
        return ctx


class CarCreateView(StaffRequiredMixin, AdminPanelContextMixin, CreateView):
    model = Car
    form_class = CarStaffForm
    template_name = 'admin_panel/car_form.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['cancel_url'] = reverse_lazy('admin_panel:car_list')
        ctx['return_to_sell'] = False
        return ctx

    def get_success_url(self):
        return reverse_lazy('admin_panel:car_list')

    def form_valid(self, form):
        messages.success(self.request, 'Car created successfully.')
        response = super().form_valid(form)
        self._save_images(self.object)
        return response

    def _save_images(self, car):
        _save_car_images_with_primary(self.request, car)


class CarUpdateView(StaffRequiredMixin, AdminPanelContextMixin, UpdateView):
    model = Car
    form_class = CarStaffForm
    template_name = 'admin_panel/car_form.html'

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.prefetch_related(
            Prefetch(
                'images',
                queryset=CarImage.objects.order_by('-is_primary', 'id'),
            )
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['return_to_sell'] = self.request.GET.get('return') == 'sell'
        ctx['cancel_url'] = (
            reverse_lazy('admin_panel:sell_car_inquiry_list')
            if ctx['return_to_sell']
            else reverse_lazy('admin_panel:car_list')
        )
        return ctx

    def get_success_url(self):
        if self.request.POST.get('return') == 'sell':
            return reverse_lazy('admin_panel:sell_car_inquiry_list')
        return reverse_lazy('admin_panel:car_list')

    def form_valid(self, form):
        messages.success(self.request, 'Car updated successfully.')
        response = super().form_valid(form)
        self._save_images(self.object)
        return response

    def _save_images(self, car):
        _save_car_images_with_primary(self.request, car)


class CarImageDeleteView(StaffRequiredMixin, View):
    http_method_names = ['post']

    def post(self, request, car_pk, image_pk):
        car_image = get_object_or_404(CarImage, pk=image_pk)
        if car_image.car_id != car_pk:
            raise Http404()
        was_primary = car_image.is_primary
        if car_image.image and getattr(car_image.image, 'name', None):
            _safe_delete_stored_file(car_image.image.name)
        car_image.delete()
        if was_primary:
            CarImage.objects.filter(car_id=car_pk).update(is_primary=False)
            first = CarImage.objects.filter(car_id=car_pk).order_by('id').first()
            if first:
                CarImage.objects.filter(pk=first.pk).update(is_primary=True)
        messages.success(request, 'Image removed.')
        url = reverse('admin_panel:car_edit', kwargs={'pk': car_pk})
        if request.POST.get('return') == 'sell':
            url = f'{url}?{urlencode({"return": "sell"})}'
        return HttpResponseRedirect(url)


class CarImageDeleteAllView(StaffRequiredMixin, View):
    http_method_names = ['post']

    def post(self, request, car_pk):
        car = get_object_or_404(Car, pk=car_pk)
        images = list(car.images.all())
        if not images:
            messages.info(request, 'No images to remove.')
        else:
            for car_image in images:
                if car_image.image and getattr(car_image.image, 'name', None):
                    _safe_delete_stored_file(car_image.image.name)
            CarImage.objects.filter(car_id=car.pk).delete()
            messages.success(request, f'Removed all images ({len(images)}).')

        url = reverse('admin_panel:car_edit', kwargs={'pk': car_pk})
        if request.POST.get('return') == 'sell':
            url = f'{url}?{urlencode({"return": "sell"})}'
        return HttpResponseRedirect(url)


class CarDeleteView(StaffRequiredMixin, AdminPanelContextMixin, DeleteView):
    model = Car
    template_name = 'admin_panel/car_confirm_delete.html'
    success_url = reverse_lazy('admin_panel:car_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['return_to_sell'] = self.request.GET.get('return') == 'sell'
        ctx['cancel_url'] = (
            reverse_lazy('admin_panel:sell_car_inquiry_list')
            if ctx['return_to_sell']
            else reverse_lazy('admin_panel:car_list')
        )
        return ctx

    def get_success_url(self):
        if self.request.POST.get('return') == 'sell':
            return reverse_lazy('admin_panel:sell_car_inquiry_list')
        return reverse_lazy('admin_panel:car_list')

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Car deleted.')
        return super().delete(request, *args, **kwargs)


class CarBulkDeleteView(StaffRequiredMixin, View):
    def post(self, request):
        ids = request.POST.getlist('ids')
        if not ids:
            messages.warning(request, 'No cars selected.')
            return redirect('admin_panel:car_list')
        Car.objects.filter(pk__in=ids).exclude(submit_via_sell_form=True).delete()
        messages.success(request, f'Deleted {len(ids)} car(s).')
        return redirect('admin_panel:car_list')


class SellCarInquiryListView(
    StaffRequiredMixin,
    AdminPanelContextMixin,
    SafePagePaginationMixin,
    ListView,
):
    """Cars submitted via the public Sell Car form (pending review)."""

    model = Car
    template_name = 'admin_panel/sell_car_inquiry_list.html'
    context_object_name = 'cars'
    paginate_by = 25

    def dispatch(self, request, *args, **kwargs):
        # Mark sell inquiries as seen only on the initial list open
        # (skip for filter/pagination clicks to reduce repeated write work).
        if request.method == 'GET' and not request.GET:
            n = Car.objects.filter(submit_via_sell_form=True, sell_inquiry_seen=False).update(
                sell_inquiry_seen=True
            )
            if n:
                invalidate_admin_nav_counts_cache()
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        qs = Car.objects.filter(submit_via_sell_form=True).select_related(
            'brand', 'model', 'seller'
        ).prefetch_related(ADMIN_PRIMARY_IMAGE_PREFETCH)
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(contact_number__icontains=q))
        st = self.request.GET.get('status', '').strip()
        if st:
            qs = qs.filter(status=st)
        return qs.order_by('-created_at')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['search_q'] = self.request.GET.get('q', '')
        ctx['filter_status'] = self.request.GET.get('status', '')
        ctx['statuses'] = Car.STATUS_CHOICES
        return ctx


class SellCarInquiryBulkDeleteView(StaffRequiredMixin, View):
    def post(self, request):
        ids = request.POST.getlist('ids')
        if not ids:
            messages.warning(request, 'No listings selected.')
            return redirect('admin_panel:sell_car_inquiry_list')
        n, _ = Car.objects.filter(pk__in=ids, submit_via_sell_form=True).delete()
        if n:
            invalidate_admin_nav_counts_cache()
        messages.success(request, f'Deleted {n} listing(s).')
        return redirect('admin_panel:sell_car_inquiry_list')


class SellCarInquiryApproveView(StaffRequiredMixin, View):
    """Publish listing on the website (same as main car list visibility)."""

    def post(self, request, pk):
        car = get_object_or_404(Car, pk=pk, submit_via_sell_form=True)
        car.status = 'APPROVED'
        car.save()
        messages.success(request, f'Approved: {car.title} is now visible on the site.')
        return redirect('admin_panel:sell_car_inquiry_list')


class SellCarInquiryToggleFeaturedView(StaffRequiredMixin, View):
    def post(self, request, pk):
        car = get_object_or_404(Car, pk=pk, submit_via_sell_form=True)
        car.is_featured = not car.is_featured
        car.save()
        state = 'featured' if car.is_featured else 'removed from featured'
        messages.success(request, f'{car.title}: {state}.')
        return redirect('admin_panel:sell_car_inquiry_list')


class BrandListView(StaffRequiredMixin, AdminPanelContextMixin, ListView):
    model = Brand
    template_name = 'admin_panel/brand_list.html'
    context_object_name = 'brands'
    queryset = Brand.objects.annotate(car_count=Count('car', distinct=True)).order_by('name')


class BrandCreateView(StaffRequiredMixin, AdminPanelContextMixin, CreateView):
    model = Brand
    form_class = BrandForm
    template_name = 'admin_panel/brand_form.html'
    success_url = reverse_lazy('admin_panel:brand_list')

    def form_valid(self, form):
        messages.success(self.request, 'Brand created.')
        return super().form_valid(form)


class BrandUpdateView(StaffRequiredMixin, AdminPanelContextMixin, UpdateView):
    model = Brand
    form_class = BrandForm
    template_name = 'admin_panel/brand_form.html'
    success_url = reverse_lazy('admin_panel:brand_list')

    def form_valid(self, form):
        messages.success(self.request, 'Brand updated.')
        return super().form_valid(form)


class BrandDeleteView(StaffRequiredMixin, AdminPanelContextMixin, DeleteView):
    model = Brand
    template_name = 'admin_panel/brand_confirm_delete.html'
    success_url = reverse_lazy('admin_panel:brand_list')

    def delete(self, request, *args, **kwargs):
        if Car.objects.filter(brand=self.get_object()).exists():
            messages.error(request, 'Cannot delete brand: cars still reference it.')
            return redirect('admin_panel:brand_list')
        messages.success(request, 'Brand deleted.')
        return super().delete(request, *args, **kwargs)


class BrandBulkAddView(StaffRequiredMixin, AdminPanelContextMixin, FormView):
    template_name = 'admin_panel/brand_bulk_add.html'
    form_class = BrandBulkForm
    success_url = reverse_lazy('admin_panel:brand_list')

    def form_valid(self, form):
        text = form.cleaned_data['brands']
        names = _parse_bulk_list(text)
        created = 0
        skipped_dup = 0
        for n in names:
            if Brand.objects.filter(name=n).exists():
                skipped_dup += 1
                continue
            Brand.objects.create(name=n)
            created += 1
        if created:
            messages.success(self.request, f'Added {created} brand(s).')
        else:
            messages.warning(self.request, 'No new brands were added.')
        if skipped_dup:
            messages.info(self.request, f'Skipped {skipped_dup} name(s) (already exists).')
        return super().form_valid(form)


class CarModelBulkAddView(StaffRequiredMixin, AdminPanelContextMixin, FormView):
    template_name = 'admin_panel/carmodel_bulk_add.html'
    form_class = CarModelBulkForm
    success_url = reverse_lazy('admin_panel:carmodel_list')

    def form_valid(self, form):
        brand = form.cleaned_data['brand']
        text = form.cleaned_data['models']
        names = []
        seen = set()
        for n in _parse_bulk_list(text):
            key = (brand.pk, n.lower())
            if key in seen:
                continue
            seen.add(key)
            names.append(n)
        created = 0
        skipped_dup = 0
        for n in names:
            if CarModel.objects.filter(brand=brand, name=n).exists():
                skipped_dup += 1
                continue
            CarModel.objects.create(brand=brand, name=n)
            created += 1
        if created:
            messages.success(self.request, f'Added {created} model(s) for {brand.name}.')
        else:
            messages.warning(self.request, 'No new models were added.')
        if skipped_dup:
            messages.info(self.request, f'Skipped {skipped_dup} duplicate(s) for this brand.')
        return super().form_valid(form)


class BrandDeleteAllModelsView(StaffRequiredMixin, View):
    """Delete all CarModel rows for a brand that are not referenced by any Car."""

    template_name = 'admin_panel/brand_delete_all_models_confirm.html'

    def get(self, request, pk):
        brand = get_object_or_404(Brand, pk=pk)
        models_qs = CarModel.objects.filter(brand=brand).order_by('name')
        in_use_ids = set(Car.objects.filter(model__brand=brand).values_list('model_id', flat=True))
        deletable = []
        blocked = []
        for m in models_qs:
            if m.pk in in_use_ids:
                blocked.append(m)
            else:
                deletable.append(m)
        ctx = {
            **get_cached_nav_counts(),
            'brand': brand,
            'deletable': deletable,
            'blocked': blocked,
        }
        return render(request, self.template_name, ctx)

    def post(self, request, pk):
        brand = get_object_or_404(Brand, pk=pk)
        in_use_ids = set(Car.objects.filter(model__brand=brand).values_list('model_id', flat=True))
        qs = CarModel.objects.filter(brand=brand).exclude(pk__in=in_use_ids)
        n = qs.count()
        qs.delete()
        if n:
            messages.success(request, f'Deleted {n} model(s) for {brand.name}.')
        else:
            messages.info(request, 'No deletable models (none were unused by cars).')
        if in_use_ids:
            messages.warning(
                request,
                f'{len(in_use_ids)} model(s) are still used by cars and were not deleted.',
            )
        return redirect('admin_panel:carmodel_list')


class CarModelListView(StaffRequiredMixin, AdminPanelContextMixin, ListView):
    model = CarModel
    template_name = 'admin_panel/carmodel_list.html'
    context_object_name = 'carmodels'

    def get_queryset(self):
        qs = CarModel.objects.select_related('brand')
        bid = self.request.GET.get('brand')
        if bid:
            qs = qs.filter(brand_id=bid)
        return qs.order_by('brand__name', 'name')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['brands'] = Brand.objects.all()
        _b = self.request.GET.get('brand')
        ctx['filter_brand'] = int(_b) if _b and str(_b).isdigit() else None
        return ctx


class CarModelCreateView(StaffRequiredMixin, AdminPanelContextMixin, CreateView):
    model = CarModel
    form_class = CarModelForm
    template_name = 'admin_panel/carmodel_form.html'
    success_url = reverse_lazy('admin_panel:carmodel_list')

    def form_valid(self, form):
        messages.success(self.request, 'Model created.')
        return super().form_valid(form)


class CarModelUpdateView(StaffRequiredMixin, AdminPanelContextMixin, UpdateView):
    model = CarModel
    form_class = CarModelForm
    template_name = 'admin_panel/carmodel_form.html'
    success_url = reverse_lazy('admin_panel:carmodel_list')

    def form_valid(self, form):
        messages.success(self.request, 'Model updated.')
        return super().form_valid(form)


class CarModelDeleteView(StaffRequiredMixin, AdminPanelContextMixin, DeleteView):
    model = CarModel
    template_name = 'admin_panel/carmodel_confirm_delete.html'
    success_url = reverse_lazy('admin_panel:carmodel_list')

    def delete(self, request, *args, **kwargs):
        if Car.objects.filter(model=self.get_object()).exists():
            messages.error(request, 'Cannot delete model: cars still reference it.')
            return redirect('admin_panel:carmodel_list')
        messages.success(request, 'Model deleted.')
        return super().delete(request, *args, **kwargs)


class InquiryListView(
    StaffRequiredMixin,
    AdminPanelContextMixin,
    SafePagePaginationMixin,
    ListView,
):
    model = Inquiry
    template_name = 'admin_panel/inquiry_list.html'
    context_object_name = 'inquiries'
    paginate_by = 30

    def get_queryset(self):
        qs = Inquiry.objects.select_related('car', 'car__brand', 'car__model').order_by('is_read', '-created_at')
        if self.request.GET.get('unread') == '1':
            qs = qs.filter(is_read=False)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['filter_unread'] = self.request.GET.get('unread') == '1'
        return ctx


class InquiryDetailView(StaffRequiredMixin, AdminPanelContextMixin, DetailView):
    model = Inquiry
    template_name = 'admin_panel/inquiry_detail.html'
    context_object_name = 'inquiry'

    def get_queryset(self):
        return Inquiry.objects.select_related('car', 'car__brand', 'car__model')

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        obj = self.object
        if not obj.is_read:
            obj.is_read = True
            obj.save(update_fields=['is_read'])
            invalidate_admin_nav_counts_cache()
        return response


class InquiryMarkReadView(StaffRequiredMixin, View):
    def post(self, request, pk):
        n = Inquiry.objects.filter(pk=pk).update(is_read=True)
        if n:
            invalidate_admin_nav_counts_cache()
        messages.success(request, 'Marked as read.')
        return redirect('admin_panel:inquiry_list')


class InquiryMarkAllReadView(StaffRequiredMixin, View):
    def post(self, request):
        n = Inquiry.objects.filter(is_read=False).update(is_read=True)
        if n:
            invalidate_admin_nav_counts_cache()
        messages.success(request, f'Marked {n} inquiry(ies) as read.')
        return redirect('admin_panel:inquiry_list')


class InquiryDeleteView(StaffRequiredMixin, View):
    def post(self, request, pk):
        Inquiry.objects.filter(pk=pk).delete()
        invalidate_admin_nav_counts_cache()
        messages.success(request, 'Inquiry deleted.')
        return redirect('admin_panel:inquiry_list')


class UnreadInquiryCountJsonView(StaffRequiredMixin, View):
    def get(self, request):
        counts = get_cached_nav_counts()
        inquiries = counts['unread_inquiry_count']
        sell = counts['sell_inquiry_unread_count']
        return JsonResponse(
            {
                'count': inquiries,
                'inquiries': inquiries,
                'sell_inquiries': sell,
            }
        )


class BrandModelsJsonView(StaffRequiredMixin, View):
    def get(self, request, pk):
        models = CarModel.objects.filter(brand_id=pk).order_by('name')
        return JsonResponse({'models': [{'id': m.id, 'name': m.name} for m in models]})


class CSVImportView(StaffRequiredMixin, AdminPanelContextMixin, FormView):
    template_name = 'admin_panel/csv_import.html'
    form_class = CSVUploadForm

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['csv_skip_log'] = self.request.session.pop('csv_skip_log', None)
        return ctx

    def form_valid(self, form):
        f = form.cleaned_data['file']
        replace_all = form.cleaned_data.get('replace_all')
        try:
            rows = csv_io.parse_uploaded_csv(f)
        except ValueError as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)
        ok, errs = csv_io.validate_and_preview_rows(rows)
        fd, path = tempfile.mkstemp(suffix='.json')
        with os.fdopen(fd, 'w', encoding='utf-8') as out:
            json.dump(
                {
                    'ok': ok,
                    'errors': errs,
                    'replace_all': bool(replace_all),
                },
                out,
            )
        self.request.session['admin_csv_path'] = path
        if errs and not ok:
            messages.error(self.request, 'CSV has errors; fix the file and try again.')
        return redirect('admin_panel:csv_preview')


class CSVPreviewView(StaffRequiredMixin, AdminPanelContextMixin, TemplateView):
    template_name = 'admin_panel/csv_preview.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        path = self.request.session.get('admin_csv_path')
        if not path or not os.path.isfile(path):
            ctx['missing'] = True
            return ctx
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        ctx['preview_ok'] = data.get('ok', [])
        ctx['preview_errors'] = data.get('errors', [])
        ctx['replace_all'] = data.get('replace_all', False)
        ctx['can_confirm'] = bool(data.get('ok'))
        return ctx


class CSVConfirmView(StaffRequiredMixin, View):
    def post(self, request):
        path = request.session.get('admin_csv_path')
        if not path or not os.path.isfile(path):
            messages.error(request, 'No import session; upload again.')
            return redirect('admin_panel:csv_import')
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        ok = data.get('ok', [])
        replace_all = data.get('replace_all', False)
        confirm = request.POST.get('confirm_replace')
        if replace_all and confirm != 'REPLACE':
            messages.error(request, 'Type REPLACE to confirm deleting all cars.')
            return redirect('admin_panel:csv_preview')
        try:
            result = csv_io.apply_import(ok, replace_all=replace_all)
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass
            request.session.pop('admin_csv_path', None)
        messages.success(
            request,
            f"Import finished: {result['created']} created, {result['updated']} updated.",
        )
        if result['skipped']:
            messages.warning(request, f"{len(result['skipped'])} row(s) skipped — see logs.")
            request.session['csv_skip_log'] = result['skipped'][:200]
        return redirect('admin_panel:csv_import')


class CSVExportView(StaffRequiredMixin, View):
    """Export every car (used from CSV tools)."""

    def get(self, request):
        data = csv_io.export_cars_csv()
        resp = HttpResponse(data, content_type='text/csv; charset=utf-8')
        resp['Content-Disposition'] = 'attachment; filename="cars_export.csv"'
        return resp


class CarListCSVExportView(StaffRequiredMixin, View):
    """Export cars matching the staff car list filters (including date range on listed_at)."""

    def get(self, request):
        qs = filter_car_list_queryset(request)
        data = csv_io.export_cars_csv(queryset=qs)
        resp = HttpResponse(data, content_type='text/csv; charset=utf-8')
        resp['Content-Disposition'] = 'attachment; filename="cars_filtered.csv"'
        return resp
