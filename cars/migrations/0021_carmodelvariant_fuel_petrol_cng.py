from django.db import migrations


def forwards(apps, schema_editor):
    CarModelVariant = apps.get_model('cars', 'CarModelVariant')
    CarModel = apps.get_model('cars', 'CarModel')
    CarModelVariant.objects.filter(fuel_type='CNG').update(fuel_type='Petrol + CNG')
    for m in CarModel.objects.exclude(supported_fuels=[]).iterator():
        raw = m.supported_fuels or []
        if not raw:
            continue
        seen = set()
        new_list = []
        for x in raw:
            if x == 'CNG':
                x = 'Petrol + CNG'
            if not x:
                continue
            k = str(x).casefold()
            if k in seen:
                continue
            seen.add(k)
            new_list.append(x)
        if new_list != raw:
            m.supported_fuels = new_list
            m.save(update_fields=['supported_fuels'])


def backwards(apps, schema_editor):
    CarModelVariant = apps.get_model('cars', 'CarModelVariant')
    CarModel = apps.get_model('cars', 'CarModel')
    CarModelVariant.objects.filter(fuel_type='Petrol + CNG').update(fuel_type='CNG')
    for m in CarModel.objects.exclude(supported_fuels=[]).iterator():
        raw = m.supported_fuels or []
        new_list = ['CNG' if x == 'Petrol + CNG' else x for x in raw]
        if new_list != raw:
            m.supported_fuels = new_list
            m.save(update_fields=['supported_fuels'])


class Migration(migrations.Migration):

    dependencies = [
        ('cars', '0020_carmodel_supported_fuels_carmodelvariant'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
