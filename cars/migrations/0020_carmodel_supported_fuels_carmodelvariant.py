from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('cars', '0019_car_rejection_reason'),
    ]

    operations = [
        migrations.AddField(
            model_name='carmodel',
            name='supported_fuels',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.CreateModel(
            name='CarModelVariant',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120)),
                ('fuel_type', models.CharField(choices=[('Petrol', 'Petrol'), ('Diesel', 'Diesel'), ('CNG', 'CNG'), ('Electric', 'Electric')], max_length=20)),
                ('transmission', models.CharField(choices=[('Manual', 'Manual'), ('Automatic', 'Automatic')], max_length=20)),
                ('car_model', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='variants', to='cars.carmodel')),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.AddConstraint(
            model_name='carmodelvariant',
            constraint=models.UniqueConstraint(fields=('car_model', 'name'), name='uniq_variant_per_model'),
        ),
    ]
