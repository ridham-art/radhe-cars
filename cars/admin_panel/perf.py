"""Small helpers for admin-panel performance (fewer DB round-trips)."""
from django.db import connection


def admin_nav_counts_one_query():
    """
    Return (unread_inquiry_count, sell_inquiry_unread_count) in a single SQL round-trip.
    """
    from cars.models import Car, Inquiry

    inv = connection.ops.quote_name(Inquiry._meta.db_table)
    car = connection.ops.quote_name(Car._meta.db_table)
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT
                (SELECT COUNT(*) FROM {inv} WHERE NOT is_read),
                (SELECT COUNT(*) FROM {car} WHERE submit_via_sell_form AND NOT sell_inquiry_seen)
            """
        )
        row = cursor.fetchone()
    return int(row[0]), int(row[1])
