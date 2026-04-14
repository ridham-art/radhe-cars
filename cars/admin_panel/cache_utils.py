"""Cached staff nav badge counts (shared key for mixin + JSON API)."""

from django.core.cache import cache

ADMIN_NAV_COUNTS_CACHE_KEY = 'admin_panel:nav_counts_v1'
ADMIN_NAV_COUNTS_TTL = 180


def build_nav_counts_dict():
    from cars.models import Car, Inquiry

    return {
        'unread_inquiry_count': Inquiry.objects.filter(is_read=False).count(),
        'sell_inquiry_unread_count': Car.objects.filter(
            submit_via_sell_form=True, sell_inquiry_seen=False
        ).count(),
    }


def get_cached_nav_counts():
    return cache.get_or_set(
        ADMIN_NAV_COUNTS_CACHE_KEY,
        build_nav_counts_dict,
        ADMIN_NAV_COUNTS_TTL,
    )


def invalidate_admin_nav_counts_cache():
    cache.delete(ADMIN_NAV_COUNTS_CACHE_KEY)
