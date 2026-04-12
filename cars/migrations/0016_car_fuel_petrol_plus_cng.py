from django.db import migrations, models


def forwards_cng_to_petrol_cng(apps, schema_editor):
    Car = apps.get_model('cars', 'Car')
    Car.objects.filter(fuel_type='CNG').update(fuel_type='Petrol + CNG')


def backwards_petrol_cng_to_cng(apps, schema_editor):
    Car = apps.get_model('cars', 'Car')
    Car.objects.filter(fuel_type='Petrol + CNG').update(fuel_type='CNG')


class Migration(migrations.Migration):

    dependencies = [
        ('cars', '0015_car_model_month'),
    ]

    operations = [
        migrations.RunPython(forwards_cng_to_petrol_cng, backwards_petrol_cng_to_cng),
        migrations.AlterField(
            model_name='car',
            name='fuel_type',
            field=models.CharField(
                choices=[
                    ('Petrol', 'Petrol'),
                    ('Diesel', 'Diesel'),
                    ('Petrol + CNG', 'Petrol + CNG'),
                    ('Electric', 'Electric'),
                ],
                max_length=20,
            ),
        ),
    ]
