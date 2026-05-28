from django.core.cache import cache
from django.test import TestCase, override_settings

from cars.admin_panel.cache_utils import (
    ADMIN_DASHBOARD_STATS_CACHE_KEY,
    ADMIN_INVENTORY_TAB_COUNTS_CACHE_KEY,
    ADMIN_NAV_COUNTS_CACHE_KEY,
    ADMIN_SELL_INQUIRY_TAB_COUNTS_CACHE_KEY,
    build_inventory_tab_counts_dict,
    build_sell_inquiry_tab_counts_dict,
    get_cached_dashboard_stats,
    get_cached_inventory_tab_counts,
    get_cached_nav_counts,
    get_cached_sell_inquiry_tab_counts,
    invalidate_admin_nav_counts_cache,
)
from cars.models import Brand, Car, CarModel


@override_settings(
    DEBUG=False,
    ACCOUNT_EMAIL_REQUIRED=True,
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'admin-panel-cache-tests',
        }
    },
)
class AdminPanelCacheTests(TestCase):
    def setUp(self):
        cache.clear()
        self.brand = Brand.objects.create(name='TestMake')
        self.model = CarModel.objects.create(brand=self.brand, name='TestModel')

    def _make_car(self, **kwargs):
        defaults = {
            'title': 'Test Car',
            'brand': self.brand,
            'model': self.model,
            'year': 2020,
            'price': 100000,
            'mileage': 10000,
            'fuel_type': 'Petrol',
            'transmission': 'MT',
            'ownership': '1st Owner',
            'status': 'APPROVED',
            'submit_via_sell_form': False,
        }
        defaults.update(kwargs)
        return Car.objects.create(**defaults)

    def test_inventory_tab_counts_match_builder(self):
        self._make_car(status='APPROVED')
        self._make_car(status='SOLD')
        self._make_car(status='APPROVED', submit_via_sell_form=True)

        expected = build_inventory_tab_counts_dict()
        cached = get_cached_inventory_tab_counts()

        self.assertEqual(cached['stock_count'], expected['stock_count'])
        self.assertEqual(cached['sold_count'], expected['sold_count'])
        self.assertEqual(cached['stock_count'], 1)
        self.assertEqual(cached['sold_count'], 1)

    def test_inventory_tab_counts_cached_second_call(self):
        self._make_car()
        first = get_cached_inventory_tab_counts()
        cache_key = ADMIN_INVENTORY_TAB_COUNTS_CACHE_KEY
        self.assertIsNotNone(cache.get(cache_key))
        second = get_cached_inventory_tab_counts()
        self.assertEqual(first, second)

    def test_sell_inquiry_tab_counts_match_builder(self):
        self._make_car(status='PENDING', submit_via_sell_form=True)
        self._make_car(status='APPROVED', submit_via_sell_form=True)
        self._make_car(status='REJECTED', submit_via_sell_form=True)

        expected = build_sell_inquiry_tab_counts_dict()
        cached = get_cached_sell_inquiry_tab_counts()

        self.assertEqual(cached, expected)
        self.assertEqual(cached['pending_count'], 1)
        self.assertEqual(cached['approved_count'], 1)
        self.assertEqual(cached['rejected_count'], 1)

    def test_sell_inquiry_tab_counts_cached_second_call(self):
        self._make_car(status='PENDING', submit_via_sell_form=True)
        first = get_cached_sell_inquiry_tab_counts()
        self.assertIsNotNone(cache.get(ADMIN_SELL_INQUIRY_TAB_COUNTS_CACHE_KEY))
        second = get_cached_sell_inquiry_tab_counts()
        self.assertEqual(first, second)

    def test_dashboard_stats_has_expected_keys(self):
        stats = get_cached_dashboard_stats()
        for key in (
            'total_cars',
            'active_cars',
            'sales_chart',
            'makes_chart',
            'sold_this_month',
            'pending_sell_total',
        ):
            self.assertIn(key, stats)
        self.assertIsInstance(stats['sales_chart'], dict)
        self.assertIn('labels', stats['sales_chart'])

    def test_invalidate_rebuilds_after_data_change(self):
        self._make_car(status='APPROVED')
        first = get_cached_inventory_tab_counts()['stock_count']
        self.assertEqual(first, 1)

        self._make_car(status='APPROVED')
        second_stale = get_cached_inventory_tab_counts()['stock_count']
        self.assertEqual(second_stale, 1)

        invalidate_admin_nav_counts_cache()
        self.assertIsNone(cache.get(ADMIN_INVENTORY_TAB_COUNTS_CACHE_KEY))
        self.assertIsNone(cache.get(ADMIN_SELL_INQUIRY_TAB_COUNTS_CACHE_KEY))
        self.assertIsNone(cache.get(ADMIN_DASHBOARD_STATS_CACHE_KEY))
        self.assertIsNone(cache.get(ADMIN_NAV_COUNTS_CACHE_KEY))

        refreshed = get_cached_inventory_tab_counts()['stock_count']
        self.assertEqual(refreshed, 2)

    def test_nav_counts_cached(self):
        first = get_cached_nav_counts()
        self.assertIsNotNone(cache.get(ADMIN_NAV_COUNTS_CACHE_KEY))
        second = get_cached_nav_counts()
        self.assertEqual(first, second)
