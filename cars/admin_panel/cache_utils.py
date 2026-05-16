"""Cached staff admin counts and dashboard aggregates."""

from calendar import month_abbr
from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db.models import Count, Q
from django.db.models.functions import TruncMonth
from django.utils import timezone

ADMIN_NAV_COUNTS_CACHE_KEY = 'admin_panel:nav_counts_v1'
ADMIN_INVENTORY_TAB_COUNTS_CACHE_KEY = 'admin_panel:inventory_tab_counts_v1'
ADMIN_DASHBOARD_STATS_CACHE_KEY = 'admin_panel:dashboard_stats_v1'

ADMIN_NAV_COUNTS_TTL = 180
ADMIN_INVENTORY_TAB_COUNTS_TTL = 180
ADMIN_DASHBOARD_STATS_TTL = 120

_MAKE_CHART_COLORS = ['#2563eb', '#0f9d58', '#c8881a', '#6d4aff', '#0ea5e9']


def _month_window(count=6):
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


def build_nav_counts_dict():
    from cars.models import Car, Inquiry

    return {
        'unread_inquiry_count': Inquiry.objects.filter(is_read=False).count(),
        'sell_inquiry_unread_count': Car.objects.filter(
            submit_via_sell_form=True, sell_inquiry_seen=False
        ).count(),
    }


def build_inventory_tab_counts_dict():
    from cars.models import Car

    return Car.objects.exclude(submit_via_sell_form=True).aggregate(
        stock_count=Count('pk', filter=~Q(status='SOLD')),
        sold_count=Count('pk', filter=Q(status='SOLD')),
    )


def build_dashboard_stats_dict():
    from cars.models import Car, Inquiry, Wishlist

    User = get_user_model()
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

    total_cars = car_stats.get('total_cars') or 0
    active_cars = car_stats.get('active_cars') or 0
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

    return {
        **car_stats,
        **inq_stats,
        **wish_stats,
        'total_customers': User.objects.filter(is_staff=False).count(),
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
        'sales_chart': sales_chart,
        'makes_chart': makes_chart,
    }


def get_cached_nav_counts():
    return cache.get_or_set(
        ADMIN_NAV_COUNTS_CACHE_KEY,
        build_nav_counts_dict,
        ADMIN_NAV_COUNTS_TTL,
    )


def get_cached_inventory_tab_counts():
    return cache.get_or_set(
        ADMIN_INVENTORY_TAB_COUNTS_CACHE_KEY,
        build_inventory_tab_counts_dict,
        ADMIN_INVENTORY_TAB_COUNTS_TTL,
    )


def get_cached_dashboard_stats():
    return cache.get_or_set(
        ADMIN_DASHBOARD_STATS_CACHE_KEY,
        build_dashboard_stats_dict,
        ADMIN_DASHBOARD_STATS_TTL,
    )


def invalidate_admin_nav_counts_cache():
    """Clear nav badges, inventory tab counts, and dashboard stat caches."""
    cache.delete_many(
        [
            ADMIN_NAV_COUNTS_CACHE_KEY,
            ADMIN_INVENTORY_TAB_COUNTS_CACHE_KEY,
            ADMIN_DASHBOARD_STATS_CACHE_KEY,
        ]
    )
