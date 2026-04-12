import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cars', '0014_car_status_default_pending'),
    ]

    operations = [
        migrations.AlterField(
            model_name='car',
            name='fuel_type',
            field=models.CharField(
                choices=[
                    ('Petrol', 'Petrol'),
                    ('Diesel', 'Diesel'),
                    ('CNG', 'Petrol+CNG'),
                    ('Electric', 'Electric'),
                ],
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='car',
            name='model_month',
            field=models.PositiveSmallIntegerField(
                blank=True,
                help_text='Manufacturing month (1–12); optional. Shown as “Month Year” on listing.',
                null=True,
                validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(12),
                ],
            ),
        ),
    ]
