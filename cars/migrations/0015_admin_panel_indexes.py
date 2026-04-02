# Indexes to speed admin-panel badge counts and sell-inquiry filters.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cars', '0014_car_status_default_pending'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='inquiry',
            index=models.Index(fields=['is_read'], name='cars_inquiry_is_read_idx'),
        ),
        migrations.AddIndex(
            model_name='car',
            index=models.Index(
                fields=['submit_via_sell_form', 'sell_inquiry_seen'],
                name='cars_car_sell_seen_idx',
            ),
        ),
    ]
