from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cars', '0016_car_fuel_petrol_plus_cng'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='car',
            index=models.Index(fields=['status', 'created_at'], name='car_status_created_idx'),
        ),
        migrations.AddIndex(
            model_name='car',
            index=models.Index(fields=['brand', 'status'], name='car_brand_status_idx'),
        ),
        migrations.AddIndex(
            model_name='car',
            index=models.Index(
                fields=['submit_via_sell_form', 'sell_inquiry_seen'],
                name='car_sell_seen_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='car',
            index=models.Index(
                fields=['submit_via_sell_form', 'status', 'created_at'],
                name='car_sell_status_created_idx',
            ),
        ),
    ]
