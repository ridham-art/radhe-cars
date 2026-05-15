import json
import logging
import os
import re
import tempfile
from datetime import datetime, time, timedelta
from calendar import month_abbr
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.conf import settings
from django.contrib.auth.views import LoginView, LogoutView
from django.http import Http404, HttpResponseRedirect
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.paginator import EmptyPage
from django.db.models import Q, Count, Prefetch
from django.db.models.functions import TruncMonth
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

from cars.models import Brand, Car, CarModel, CarModelVariant, CarImage, Inquiry, Wishlist, _safe_delete_stored_file
from cars.admin_panel.forms import (
    BrandBulkForm,
    BrandForm,
    CarModelBulkForm,
    CarModelForm,
    CarModelVariantForm,
    CarStaffForm,
    CarStaffFormPreview,
    CSVUploadForm,
    CSVUploadFormPreview,
    StaffAuthenticationForm,
    VehicleMasterMakeForm,
    VehicleMasterModelForm,
    VehicleMasterVariantBulkForm,
    VehicleMasterVariantBulkDeleteForm,
    VM_FUEL_OPTIONS,
)
from cars.admin_panel import csv_io
from cars.admin_panel.cache_utils import get_cached_nav_counts, invalidate_admin_nav_counts_cache
from cars.admin_panel.mixins import AdminListPartialMixin, admin_ajax_response

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
    else:
        tab = request.GET.get('tab', '').strip()
        url_name = getattr(getattr(request, 'resolver_match', None), 'url_name', None)
        if url_name in ('car_list', 'car_list_preview') and not tab:
            tab = 'stock'
        if tab == 'sold':
            qs = qs.filter(status='SOLD')
        elif tab == 'stock':
            qs = qs.exclude(status='SOLD')
        elif request.GET.get('not_sold') == '1':
            qs = qs.exclude(status='SOLD')

    year = request.GET.get('year', '').strip()
    if year and year.isdigit():
        qs = qs.filter(year=int(year))

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

    sort = request.GET.get('sort', 'date-desc').strip()
    if sort == 'price-asc':
        return qs.order_by('price')
    if sort == 'price-desc':
        return qs.order_by('-price')
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


def _parse_bulk_variants(text, default_fuel, default_trans, allowed_fuels=None):
    """Parse bulk variant lines into (name, fuel, transmission) tuples."""
    valid_fuels = {c[0] for c in CarModelVariant.FUEL_CHOICES}
    valid_trans = {c[0] for c in CarModelVariant.TRANS_CHOICES}
    allowed = list(allowed_fuels or []) or [default_fuel]
    rows = []
    for line in text.replace('\r', '').split('\n'):
        line = line.strip()
        if not line:
            continue
        if '|' in line:
            parts = [p.strip() for p in line.split('|', 2)]
            name = parts[0]
            fuel = parts[1] if len(parts) > 1 else default_fuel
            trans = parts[2] if len(parts) > 2 else default_trans
        elif ',' in line:
            parts = [p.strip() for p in line.split(',')]
            if (
                len(parts) == 3
                and parts[1] in valid_fuels
                and parts[2] in valid_trans
            ):
                name, fuel, trans = parts
            else:
                for name in parts:
                    if name:
                        rows.append((name, default_fuel, default_trans))
                continue
        else:
            name, fuel, trans = line, default_fuel, default_trans
        if not name:
            continue
        if fuel == 'CNG':
            fuel = 'Petrol + CNG'
        if fuel not in valid_fuels:
            fuel = default_fuel
        if allowed and fuel not in allowed:
            fuel = allowed[0]
        if trans not in valid_trans:
            trans = default_trans
        rows.append((name, fuel, trans))
    return rows


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


class DashboardStatsMixin:
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


_CAR_STATUS_BADGE = {
    'APPROVED': ('live', 'Live'),
    'SOLD': ('sold', 'Sold'),
    'PENDING': ('review', 'Review'),
    'ON_HOLD': ('hold', 'On hold'),
    'REJECTED': ('draft', 'Draft'),
}

_MAKE_CHART_COLORS = ['#2563eb', '#0f9d58', '#c8881a', '#6d4aff', '#0ea5e9']


def _month_window(count=6):
    """Return (month_starts, labels) for the last `count` calendar months."""
    now = timezone.localtime(timezone.now())
    year, month = now.year, now.month
    starts = []
    for _ in range(count):
        starts.append(timezone.make_aware(datetime(year, month, 1)))
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    starts.reverse()
    labels = [month_abbr[s.month] for s in starts]
    return starts, labels


def _delta_dir(current, previous):
    if current > previous:
        return 'up'
    if current < previous:
        return 'down'
    return 'flat'


def _pct_change(current, previous):
    if previous == 0:
        return '+100%' if current else '0%'
    pct = ((current - previous) / previous) * 100
    sign = '+' if pct >= 0 else ''
    return f'{sign}{pct:.0f}%'


def _car_seller_display(car):
    if car.contact_name:
        return car.contact_name
    if car.seller_id:
        return car.seller.get_full_name() or car.seller.get_username()
    return 'Direct'


def _car_meta_line(car):
    mileage = f'{car.mileage:,} km'
    return f'{car.year} · {car.fuel_type} · {mileage}'


class DashboardPreviewMixin(DashboardStatsMixin):
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        now = timezone.now()
        today = timezone.localdate()

        month_start = timezone.make_aware(datetime(today.year, today.month, 1))
        if today.month == 1:
            prev_month_start = timezone.make_aware(datetime(today.year - 1, 12, 1))
        else:
            prev_month_start = timezone.make_aware(datetime(today.year, today.month - 1, 1))

        last_30 = now - timedelta(days=30)
        prev_30_start = now - timedelta(days=60)
        last_24h = now - timedelta(hours=24)

        sold_this_month = Car.objects.filter(
            status='SOLD', sold_at__gte=month_start
        ).count()
        sold_last_month = Car.objects.filter(
            status='SOLD', sold_at__gte=prev_month_start, sold_at__lt=month_start
        ).count()

        pending_total = Car.objects.filter(
            submit_via_sell_form=True, status='PENDING'
        ).count()
        pending_new_24h = Car.objects.filter(
            submit_via_sell_form=True, status='PENDING', created_at__gte=last_24h
        ).count()

        added_last_30 = Car.objects.filter(created_at__gte=last_30).count()
        added_prev_30 = Car.objects.filter(
            created_at__gte=prev_30_start, created_at__lt=last_30
        ).count()

        total_cars = ctx.get('total_cars') or 0
        active_cars = ctx.get('active_cars') or 0
        stock_pct = (active_cars / total_cars * 100) if total_cars else 0

        month_starts, month_labels = _month_window(6)
        sold_by_month = {
            row['month']: row['count']
            for row in (
                Car.objects.filter(status='SOLD', sold_at__gte=month_starts[0])
                .annotate(month=TruncMonth('sold_at'))
                .values('month')
                .annotate(count=Count('pk'))
            )
        }
        sold_series = [sold_by_month.get(start, 0) for start in month_starts]
        avg_sold = sum(sold_series) / len(sold_series) if sold_series else 0
        ref_target = max(1, round(avg_sold)) if avg_sold else 1
        sales_chart = {
            'labels': month_labels,
            'sold': sold_series,
            'target': [ref_target] * len(month_labels),
        }

        brand_rows = list(
            Car.objects.filter(~Q(status='SOLD'))
            .values('brand__name')
            .annotate(value=Count('pk'))
            .order_by('-value')[:5]
        )
        makes_total = sum(row['value'] for row in brand_rows)
        makes_chart = {
            'labels': [row['brand__name'] for row in brand_rows],
            'values': [row['value'] for row in brand_rows],
            'colors': _MAKE_CHART_COLORS[: len(brand_rows)],
            'total': makes_total,
            'make_count': len(brand_rows),
        }

        recent_qs = (
            Car.objects.select_related('brand', 'model', 'seller')
            .prefetch_related(ADMIN_PRIMARY_IMAGE_PREFETCH)
            .order_by('-created_at')[:5]
        )
        recent_listings = []
        for car in recent_qs:
            badge_cls, badge_label = _CAR_STATUS_BADGE.get(
                car.status, ('draft', car.get_status_display())
            )
            thumb = car.primary_image
            recent_listings.append(
                {
                    'car': car,
                    'badge_cls': badge_cls,
                    'badge_label': badge_label,
                    'meta': _car_meta_line(car),
                    'seller_name': _car_seller_display(car),
                    'seller_loc': car.city or '—',
                    'listed_date': timezone.localtime(car.created_at).strftime('%d %b %Y'),
                    'price': car.price_display,
                    'thumb_url': thumb.display_url if thumb else '',
                }
            )

        pending_qs = (
            Car.objects.filter(submit_via_sell_form=True, status='PENDING')
            .select_related('brand', 'model', 'seller')
            .order_by('-created_at')[:5]
        )
        pending_requests = []
        for car in pending_qs:
            pending_requests.append(
                {
                    'car': car,
                    'seller_name': _car_seller_display(car),
                    'seller_loc': car.city or '—',
                    'submitted': timezone.localtime(car.created_at).strftime('%d %b, %H:%M'),
                }
            )

        ctx.update(
            {
                'dashboard_date': today.strftime('%d %b %Y'),
                'dashboard_updated': timezone.localtime(now).strftime('%d %b, %H:%M'),
                'sold_this_month': sold_this_month,
                'pending_sell_total': pending_total,
                'stat_total_delta': f'+{added_last_30}' if added_last_30 else '0',
                'stat_total_delta_dir': _delta_dir(added_last_30, added_prev_30),
                'stat_stock_delta': f'{stock_pct:.1f}%',
                'stat_stock_delta_dir': 'flat',
                'stat_sold_delta': _pct_change(sold_this_month, sold_last_month),
                'stat_sold_delta_dir': _delta_dir(sold_this_month, sold_last_month),
                'stat_pending_delta': f'+{pending_new_24h}' if pending_new_24h else '0',
                'stat_pending_delta_dir': 'up' if pending_new_24h else 'flat',
                'sales_chart_json': json.dumps(sales_chart),
                'makes_chart_json': json.dumps(makes_chart),
                'recent_listings': recent_listings,
                'pending_requests': pending_requests,
            }
        )
        return ctx


class DashboardView(StaffRequiredMixin, AdminPanelContextMixin, DashboardStatsMixin, TemplateView):
    template_name = 'admin_panel/dashboard.html'


class DashboardPreviewView(
    StaffRequiredMixin, AdminPanelContextMixin, DashboardPreviewMixin, TemplateView
):
    template_name = 'admin_panel/dashboard_new.html'


class ShellPreviewView(StaffRequiredMixin, AdminPanelContextMixin, TemplateView):
    template_name = 'admin_panel/shell_preview.html'


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


class CustomerListPreviewView(AdminListPartialMixin, CustomerListView):
    template_name = 'admin_panel/customer_list_new.html'
    partial_template_name = 'admin_panel/partials/customer_list_partial.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['list_querystring'] = car_list_querystring_except_page(self.request)
        ctx['list_url'] = reverse('admin_panel:customer_list')
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


class WishlistListPreviewView(AdminListPartialMixin, WishlistActivityListView):
    template_name = 'admin_panel/wishlist_list_new.html'
    partial_template_name = 'admin_panel/partials/wishlist_list_partial.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['list_querystring'] = car_list_querystring_except_page(self.request)
        ctx['list_url'] = reverse('admin_panel:wishlist_list')
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


class CarListPreviewView(
    AdminListPartialMixin,
    StaffRequiredMixin,
    AdminPanelContextMixin,
    SafePagePaginationMixin,
    ListView,
):
    model = Car
    template_name = 'admin_panel/car_list_new.html'
    partial_template_name = 'admin_panel/partials/car_list_partial.html'
    context_object_name = 'cars'
    paginate_by = 24

    def get_queryset(self):
        return filter_car_list_queryset(self.request)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        base = Car.objects.exclude(submit_via_sell_form=True)
        tab = self.request.GET.get('tab', 'stock').strip()
        if tab not in ('stock', 'sold'):
            tab = 'stock'

        ctx['brands'] = Brand.objects.order_by('name')
        ctx['years'] = (
            base.values_list('year', flat=True).distinct().order_by('-year')
        )
        ctx['search_q'] = self.request.GET.get('q', '')
        _b = self.request.GET.get('brand')
        ctx['filter_brand'] = int(_b) if _b and str(_b).isdigit() else None
        ctx['filter_year'] = self.request.GET.get('year', '')
        ctx['filter_sort'] = self.request.GET.get('sort', 'date-desc')
        ctx['active_tab'] = tab
        ctx['stock_count'] = base.exclude(status='SOLD').count()
        ctx['sold_count'] = base.filter(status='SOLD').count()
        ctx['tab_total'] = ctx['sold_count'] if tab == 'sold' else ctx['stock_count']
        ctx['car_list_querystring'] = car_list_querystring_except_page(self.request)
        filt = self.request.GET.copy()
        filt.pop('page', None)
        filt.pop('tab', None)
        ctx['filter_querystring'] = urlencode(filt)
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


class CarCreatePreviewView(CarCreateView):
    form_class = CarStaffFormPreview
    template_name = 'admin_panel/car_form_new.html'


class CarUpdatePreviewView(CarUpdateView):
    form_class = CarStaffFormPreview
    template_name = 'admin_panel/car_form_new.html'


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


def _sell_inquiry_redirect(request, fallback_name='admin_panel:sell_car_inquiry_list'):
    from django.utils.http import url_has_allowed_host_and_scheme

    nxt = request.POST.get('next', '').strip()
    if nxt and url_has_allowed_host_and_scheme(
        nxt, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return redirect(nxt)
    return redirect(fallback_name)


def _sell_inquiry_base_qs():
    return Car.objects.filter(submit_via_sell_form=True)


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


class SellCarInquiryPreviewView(
    AdminListPartialMixin,
    StaffRequiredMixin,
    AdminPanelContextMixin,
    SafePagePaginationMixin,
    ListView,
):
    model = Car
    template_name = 'admin_panel/sell_car_inquiry_list_new.html'
    partial_template_name = 'admin_panel/partials/sell_car_inquiry_partial.html'
    context_object_name = 'cars'
    paginate_by = 25

    def dispatch(self, request, *args, **kwargs):
        if request.method == 'GET' and not request.GET:
            n = _sell_inquiry_base_qs().filter(sell_inquiry_seen=False).update(
                sell_inquiry_seen=True
            )
            if n:
                invalidate_admin_nav_counts_cache()
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        qs = (
            _sell_inquiry_base_qs()
            .select_related('brand', 'model', 'seller')
            .prefetch_related(ADMIN_PRIMARY_IMAGE_PREFETCH)
        )
        tab = self.request.GET.get('tab', 'pending').strip()
        if tab == 'approved':
            qs = qs.filter(status='APPROVED')
        elif tab == 'rejected':
            qs = qs.filter(status='REJECTED')
        else:
            qs = qs.filter(status='PENDING')
        return qs.order_by('-created_at')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        tab = self.request.GET.get('tab', 'pending').strip()
        if tab not in ('pending', 'approved', 'rejected'):
            tab = 'pending'
        base = _sell_inquiry_base_qs()
        ctx['active_tab'] = tab
        ctx['pending_count'] = base.filter(status='PENDING').count()
        ctx['approved_count'] = base.filter(status='APPROVED').count()
        ctx['rejected_count'] = base.filter(status='REJECTED').count()
        filt = self.request.GET.copy()
        filt.pop('page', None)
        ctx['filter_querystring'] = urlencode(filt)
        ctx['list_querystring'] = car_list_querystring_except_page(self.request)
        ctx['preview_return_url'] = reverse('admin_panel:sell_car_inquiry_list') + '?tab=' + tab
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
        car.rejection_reason = ''
        car.save()
        invalidate_admin_nav_counts_cache()
        msg = f'Approved: {car.title} is now visible on the site.'
        reload = request.build_absolute_uri(
            reverse('admin_panel:sell_car_inquiry_list') + '?tab=pending'
        )
        return admin_ajax_response(
            request,
            redirect_to=reverse('admin_panel:sell_car_inquiry_list'),
            message=msg,
            reload_url=reload,
        )


class SellCarInquiryRejectView(StaffRequiredMixin, View):
    def post(self, request, pk):
        car = get_object_or_404(Car, pk=pk, submit_via_sell_form=True)
        reason = request.POST.get('reason', '').strip()
        if not reason:
            return admin_ajax_response(
                request,
                redirect_to=reverse('admin_panel:sell_car_inquiry_list'),
                message='A rejection reason is required.',
                level='error',
            )
        car.status = 'REJECTED'
        car.rejection_reason = reason
        car.save()
        invalidate_admin_nav_counts_cache()
        reload = request.build_absolute_uri(
            reverse('admin_panel:sell_car_inquiry_list') + '?tab=rejected'
        )
        return admin_ajax_response(
            request,
            redirect_to=reverse('admin_panel:sell_car_inquiry_list'),
            message=f'Rejected: {car.title}',
            level='warning',
            reload_url=reload,
        )


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


class InquiryListPreviewView(AdminListPartialMixin, InquiryListView):
    template_name = 'admin_panel/inquiry_list_new.html'
    partial_template_name = 'admin_panel/partials/inquiry_list_partial.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['list_querystring'] = car_list_querystring_except_page(self.request)
        ctx['list_url'] = reverse('admin_panel:inquiry_list')
        unread_qs = ''
        if self.request.GET.get('unread') == '1':
            unread_qs = '?unread=1'
        ctx['inquiry_list_url'] = reverse('admin_panel:inquiry_list') + unread_qs
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


class InquiryDetailPreviewView(InquiryDetailView):
    template_name = 'admin_panel/inquiry_detail_new.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['back_url'] = reverse('admin_panel:inquiry_list')
        return ctx


def _inquiry_redirect(request, fallback_name='admin_panel:inquiry_list'):
    from django.utils.http import url_has_allowed_host_and_scheme

    nxt = (request.POST.get('next') or request.GET.get('next') or '').strip()
    if nxt and url_has_allowed_host_and_scheme(
        nxt, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return redirect(nxt)
    return redirect(fallback_name)


class InquiryMarkReadView(StaffRequiredMixin, View):
    def post(self, request, pk):
        n = Inquiry.objects.filter(pk=pk).update(is_read=True)
        if n:
            invalidate_admin_nav_counts_cache()
        reload = request.build_absolute_uri(reverse('admin_panel:inquiry_list'))
        return admin_ajax_response(
            request,
            redirect_to=reverse('admin_panel:inquiry_list'),
            message='Marked as read.',
            reload_url=reload,
        )


class InquiryMarkAllReadView(StaffRequiredMixin, View):
    def post(self, request):
        n = Inquiry.objects.filter(is_read=False).update(is_read=True)
        if n:
            invalidate_admin_nav_counts_cache()
        reload = request.build_absolute_uri(reverse('admin_panel:inquiry_list'))
        return admin_ajax_response(
            request,
            redirect_to=reverse('admin_panel:inquiry_list'),
            message=f'Marked {n} inquiry(ies) as read.',
            reload_url=reload,
        )


class InquiryDeleteView(StaffRequiredMixin, View):
    def post(self, request, pk):
        Inquiry.objects.filter(pk=pk).delete()
        invalidate_admin_nav_counts_cache()
        reload = request.build_absolute_uri(reverse('admin_panel:inquiry_list'))
        return admin_ajax_response(
            request,
            redirect_to=reverse('admin_panel:inquiry_list'),
            message='Inquiry deleted.',
            reload_url=reload,
        )


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


def _vehicle_master_redirect(request, make_id=None, model_id=None):
    params = {}
    for key in ('make', 'model', 'q_make', 'q_model', 'q_variant'):
        val = (request.POST.get(key) or request.GET.get(key) or '').strip()
        if val:
            params[key] = val
    if make_id is not None:
        params['make'] = make_id
    if model_id is not None:
        params['model'] = model_id
    qs = urlencode(params)
    url = reverse('admin_panel:vehicle_master')
    if qs:
        url = f'{url}?{qs}'
    return redirect(url)


def _vm_model_display_fuels(car_model):
    def _norm(f):
        if f is None or f == '':
            return None
        s = str(f).strip()
        if s == 'CNG':
            return 'Petrol + CNG'
        return s

    fuels = [_norm(x) for x in (car_model.supported_fuels or [])]
    fuels = [f for f in fuels if f]
    if not fuels:
        fuels = [_norm(x) for x in car_model.variants.values_list('fuel_type', flat=True).distinct()]
        fuels = [f for f in fuels if f]
    seen = set()
    out = []
    for f in fuels:
        k = f.casefold()
        if k in seen:
            continue
        seen.add(k)
        out.append(f)
    return out


class VehicleMasterPreviewView(StaffRequiredMixin, AdminPanelContextMixin, TemplateView):
    template_name = 'admin_panel/vehicle_master_new.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        q_make = self.request.GET.get('q_make', '').strip()
        q_model = self.request.GET.get('q_model', '').strip()
        q_variant = self.request.GET.get('q_variant', '').strip()

        makes_qs = Brand.objects.annotate(
            model_count=Count('models', distinct=True),
            variant_count=Count('models__variants', distinct=True),
        ).order_by('name')
        if q_make:
            makes_qs = makes_qs.filter(name__icontains=q_make)

        ctx['total_makes'] = Brand.objects.count()
        ctx['total_models'] = CarModel.objects.count()
        ctx['total_variants'] = CarModelVariant.objects.count()
        ctx['q_make'] = q_make
        ctx['q_model'] = q_model
        ctx['q_variant'] = q_variant
        ctx['makes'] = list(makes_qs)
        ctx['vm_fuel_options'] = VM_FUEL_OPTIONS

        make_pk = self.request.GET.get('make', '').strip()
        model_pk = self.request.GET.get('model', '').strip()
        selected_make = None
        selected_model = None
        models_list = []
        variants_list = []

        if make_pk.isdigit():
            selected_make = (
                Brand.objects.filter(pk=int(make_pk))
                .annotate(
                    model_count=Count('models', distinct=True),
                    variant_count=Count('models__variants', distinct=True),
                )
                .first()
            )

        if not selected_make and ctx['makes']:
            selected_make = ctx['makes'][0]
            make_pk = str(selected_make.pk)

        if selected_make:
            models_qs = (
                CarModel.objects.filter(brand=selected_make)
                .annotate(variant_count=Count('variants', distinct=True))
                .order_by('name')
            )
            if q_model:
                models_qs = models_qs.filter(name__icontains=q_model)
            models_list = list(models_qs)
            for m in models_list:
                m.display_fuels = _vm_model_display_fuels(m)

        if model_pk.isdigit() and selected_make:
            selected_model = CarModel.objects.filter(
                pk=int(model_pk), brand=selected_make
            ).first()

        if selected_make and models_list and not selected_model:
            selected_model = models_list[0]

        if selected_model:
            variants_qs = CarModelVariant.objects.filter(
                car_model=selected_model
            ).order_by('name')
            if q_variant:
                variants_qs = variants_qs.filter(name__icontains=q_variant)
            variants_list = list(variants_qs)
            selected_model.display_fuels = _vm_model_display_fuels(selected_model)

        ctx['selected_make'] = selected_make
        ctx['selected_model'] = selected_model
        ctx['models'] = models_list
        ctx['variants'] = variants_list
        return ctx


class VehicleMasterMakeAddView(StaffRequiredMixin, View):
    def post(self, request):
        form = VehicleMasterMakeForm(request.POST)
        if form.is_valid():
            brand = form.save()
            messages.success(request, f'Added make · {brand.name}')
            return _vehicle_master_redirect(request, make_id=brand.pk, model_id='')
        messages.error(request, 'Could not add make. Check the name and try again.')
        return _vehicle_master_redirect(request)


class VehicleMasterMakeEditView(StaffRequiredMixin, View):
    def post(self, request, pk):
        brand = get_object_or_404(Brand, pk=pk)
        form = VehicleMasterMakeForm(request.POST, instance=brand)
        if form.is_valid():
            brand = form.save()
            messages.success(request, f'Renamed make · {brand.name}')
        else:
            messages.error(request, 'Could not save make.')
        return _vehicle_master_redirect(request, make_id=brand.pk)


class VehicleMasterMakeDeleteView(StaffRequiredMixin, View):
    def post(self, request, pk):
        brand = get_object_or_404(Brand, pk=pk)
        if Car.objects.filter(brand=brand).exists():
            messages.error(request, 'Cannot delete make: cars still reference it.')
            return _vehicle_master_redirect(request, make_id=brand.pk)
        name = brand.name
        brand.delete()
        messages.success(request, f'Deleted make · {name}')
        return _vehicle_master_redirect(request, make_id='', model_id='')


class VehicleMasterModelAddView(StaffRequiredMixin, View):
    def post(self, request):
        brand_id = request.POST.get('brand_id', '').strip()
        if not brand_id.isdigit():
            messages.error(request, 'Select a make first.')
            return _vehicle_master_redirect(request)
        brand = get_object_or_404(Brand, pk=int(brand_id))
        form = VehicleMasterModelForm(request.POST)
        if form.is_valid():
            car_model = CarModel.objects.create(
                brand=brand,
                name=form.cleaned_data['name'],
                supported_fuels=form.cleaned_data['supported_fuels'],
            )
            messages.success(request, f'Added model · {car_model.name}')
            return _vehicle_master_redirect(
                request, make_id=brand.pk, model_id=car_model.pk
            )
        messages.error(request, 'Could not add model.')
        return _vehicle_master_redirect(request, make_id=brand.pk)


class VehicleMasterModelEditView(StaffRequiredMixin, View):
    def post(self, request, pk):
        car_model = get_object_or_404(CarModel.objects.select_related('brand'), pk=pk)
        form = VehicleMasterModelForm(request.POST)
        if form.is_valid():
            car_model.name = form.cleaned_data['name']
            car_model.supported_fuels = form.cleaned_data['supported_fuels']
            car_model.save()
            messages.success(request, f'Saved model · {car_model.name}')
        else:
            messages.error(request, 'Could not save model.')
        return _vehicle_master_redirect(
            request, make_id=car_model.brand_id, model_id=car_model.pk
        )


class VehicleMasterModelDeleteView(StaffRequiredMixin, View):
    def post(self, request, pk):
        car_model = get_object_or_404(CarModel.objects.select_related('brand'), pk=pk)
        brand_id = car_model.brand_id
        if Car.objects.filter(model=car_model).exists():
            messages.error(request, 'Cannot delete model: cars still reference it.')
            return _vehicle_master_redirect(
                request, make_id=brand_id, model_id=car_model.pk
            )
        name = car_model.name
        car_model.delete()
        messages.success(request, f'Deleted model · {name}')
        return _vehicle_master_redirect(request, make_id=brand_id, model_id='')


class VehicleMasterVariantAddView(StaffRequiredMixin, View):
    def post(self, request):
        model_id = request.POST.get('car_model_id', '').strip()
        if not model_id.isdigit():
            messages.error(request, 'Select a model first.')
            return _vehicle_master_redirect(request)
        car_model = get_object_or_404(CarModel, pk=int(model_id))
        form = CarModelVariantForm(request.POST, car_model=car_model)
        if form.is_valid():
            variant = form.save(commit=False)
            variant.car_model = car_model
            variant.save()
            messages.success(request, f'Added variant · {variant.name}')
        else:
            messages.error(request, 'Could not add variant.')
        return _vehicle_master_redirect(
            request, make_id=car_model.brand_id, model_id=car_model.pk
        )


class VehicleMasterVariantBulkAddView(StaffRequiredMixin, View):
    def post(self, request):
        model_id = request.POST.get('car_model_id', '').strip()
        if not model_id.isdigit():
            messages.error(request, 'Select a model first.')
            return _vehicle_master_redirect(request)
        car_model = get_object_or_404(CarModel, pk=int(model_id))
        form = VehicleMasterVariantBulkForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Could not parse bulk variants. Check the format.')
            return _vehicle_master_redirect(
                request, make_id=car_model.brand_id, model_id=car_model.pk
            )

        allowed = [c[0] for c in CarModelVariant.FUEL_CHOICES]
        default_fuel = 'Petrol'
        default_trans = 'Manual'
        parsed = _parse_bulk_variants(
            form.cleaned_data['variants'],
            default_fuel,
            default_trans,
            allowed,
        )
        if not parsed:
            messages.warning(request, 'No variant names were found in your list.')
            return _vehicle_master_redirect(
                request, make_id=car_model.brand_id, model_id=car_model.pk
            )

        created = 0
        skipped_dup = 0
        for name, fuel, trans in parsed:
            if CarModelVariant.objects.filter(
                car_model=car_model, name__iexact=name
            ).exists():
                skipped_dup += 1
                continue
            CarModelVariant.objects.create(
                car_model=car_model,
                name=name,
                fuel_type=fuel,
                transmission=trans,
            )
            created += 1

        if created:
            messages.success(
                request, f'Added {created} variant(s) to {car_model.name}.'
            )
        else:
            messages.warning(request, 'No new variants were added.')
        if skipped_dup:
            messages.info(
                request,
                f'Skipped {skipped_dup} name(s) that already exist for this model.',
            )
        return _vehicle_master_redirect(
            request, make_id=car_model.brand_id, model_id=car_model.pk
        )


def _parse_bulk_delete_names(text):
    """Variant names only (first segment before | if present)."""
    names = []
    for line in text.replace('\r', '').split('\n'):
        line = line.strip()
        if not line:
            continue
        if '|' in line:
            line = line.split('|', 1)[0].strip()
        for n in _parse_bulk_list(line):
            names.append(n)
    seen = set()
    out = []
    for n in names:
        key = n.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(n)
    return out


class VehicleMasterVariantBulkDeleteView(StaffRequiredMixin, View):
    def post(self, request):
        model_id = (
            request.POST.get('car_model_id') or request.POST.get('model') or ''
        ).strip()
        if not model_id.isdigit():
            messages.error(request, 'Select a model first.')
            return _vehicle_master_redirect(request)
        car_model = get_object_or_404(CarModel, pk=int(model_id))

        ids = request.POST.getlist('ids')
        if ids:
            qs = CarModelVariant.objects.filter(
                car_model=car_model, pk__in=ids
            )
            count = qs.count()
            if not count:
                messages.warning(request, 'No matching variants to delete.')
            else:
                qs.delete()
                messages.success(request, f'Deleted {count} variant(s).')
            return _vehicle_master_redirect(
                request, make_id=car_model.brand_id, model_id=car_model.pk
            )

        form = VehicleMasterVariantBulkDeleteForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Could not read variant names to delete.')
            return _vehicle_master_redirect(
                request, make_id=car_model.brand_id, model_id=car_model.pk
            )

        names = _parse_bulk_delete_names(form.cleaned_data['variants'])
        if not names:
            messages.warning(request, 'No variant names were found in your list.')
            return _vehicle_master_redirect(
                request, make_id=car_model.brand_id, model_id=car_model.pk
            )

        deleted = 0
        not_found = 0
        for name in names:
            qs = CarModelVariant.objects.filter(
                car_model=car_model, name__iexact=name
            )
            count = qs.count()
            if count:
                qs.delete()
                deleted += count
            else:
                not_found += 1

        if deleted:
            messages.success(
                request, f'Deleted {deleted} variant(s) from {car_model.name}.'
            )
        else:
            messages.warning(request, 'No matching variants were deleted.')
        if not_found:
            messages.info(
                request,
                f'{not_found} name(s) did not match any variant for this model.',
            )
        return _vehicle_master_redirect(
            request, make_id=car_model.brand_id, model_id=car_model.pk
        )


class VehicleMasterVariantEditView(StaffRequiredMixin, View):
    def post(self, request, pk):
        variant = get_object_or_404(
            CarModelVariant.objects.select_related('car_model__brand'), pk=pk
        )
        car_model = variant.car_model
        form = CarModelVariantForm(
            request.POST, instance=variant, car_model=car_model
        )
        if form.is_valid():
            form.save()
            messages.success(request, f'Saved variant · {variant.name}')
        else:
            messages.error(request, 'Could not save variant.')
        return _vehicle_master_redirect(
            request, make_id=car_model.brand_id, model_id=car_model.pk
        )


class VehicleMasterVariantDeleteView(StaffRequiredMixin, View):
    def post(self, request, pk):
        variant = get_object_or_404(
            CarModelVariant.objects.select_related('car_model__brand'), pk=pk
        )
        car_model = variant.car_model
        name = variant.name
        variant.delete()
        messages.success(request, f'Deleted variant · {name}')
        return _vehicle_master_redirect(
            request, make_id=car_model.brand_id, model_id=car_model.pk
        )


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
        return redirect(self.get_preview_redirect_name())

    def get_preview_redirect_name(self):
        return 'admin_panel:csv_preview'


class CSVImportPreviewView(CSVImportView):
    template_name = 'admin_panel/csv_import_new.html'
    form_class = CSVUploadFormPreview


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


class CSVPreviewPreviewView(CSVPreviewView):
    template_name = 'admin_panel/csv_preview_new.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['import_url'] = reverse('admin_panel:csv_import')
        return ctx


def _csv_import_redirect(request):
    return redirect('admin_panel:csv_import')


def _csv_preview_redirect(request):
    return redirect('admin_panel:csv_preview')


class CSVConfirmView(StaffRequiredMixin, View):
    def post(self, request):
        path = request.session.get('admin_csv_path')
        if not path or not os.path.isfile(path):
            messages.error(request, 'No import session; upload again.')
            return _csv_import_redirect(request)
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        ok = data.get('ok', [])
        replace_all = data.get('replace_all', False)
        confirm = request.POST.get('confirm_replace')
        if replace_all and confirm != 'REPLACE':
            messages.error(request, 'Type REPLACE to confirm deleting all cars.')
            return _csv_preview_redirect(request)
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
