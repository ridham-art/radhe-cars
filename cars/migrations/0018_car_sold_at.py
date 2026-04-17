from django.db import migrations, models
from django.db.models import F


def backfill_sold_at(apps, schema_editor):
    Car = apps.get_model('cars', 'Car')
    Car.objects.filter(status='SOLD', sold_at__isnull=True).update(sold_at=F('updated_at'))


class Migration(migrations.Migration):

    dependencies = [
        ('cars', '0017_admin_speed_indexes'),
    ]

    operations = [
        migrations.AddField(
            model_name='car',
            name='sold_at',
            field=models.DateTimeField(
                blank=True,
                db_index=True,
                editable=False,
                help_text='When the car was marked sold (used to auto-hide sold cars from public pages after 7 days).',
                null=True,
            ),
        ),
        migrations.RunPython(backfill_sold_at, migrations.RunPython.noop),
    ]
