"""CSV import/export helpers for staff admin panel."""
import calendar
import csv
import io
from decimal import Decimal, InvalidOperation

from django.db import transaction

from cars.models import Brand, Car, CarModel
from cars.admin_panel.forms import parse_bool, parse_decimal, parse_int, parse_model_month

CSV_HEADERS = [
    'id',
    'title',
    'brand',
    'model',
    'year',
    'model_month',
    'variant',
    'price',
    'mileage',
    'fuel_type',
    'transmission',
    'body_type',
    'ownership',
    'status',
    'city',
    'color',
    'description',
    'is_featured',
    'original_price',
    'created_at',
    'listed_at',
]


def _norm(s):
    return (s or '').strip()


def _row_dict(reader_row, fieldnames):
    return {k: _norm(reader_row.get(k, '')) for k in fieldnames}


def validate_and_preview_rows(rows_dicts):
    """Return (ok_rows, errors) where errors is list of {row_num, message}."""
    errors = []
    ok_rows = []
    for idx, row in enumerate(rows_dicts, start=2):
        errs = []
        title = row.get('title')
        brand_name = row.get('brand')
        model_name = row.get('model')
        year_s = row.get('year')
        if not title:
            errs.append('Missing title')
        if not brand_name:
            errs.append('Missing brand')
        if not model_name:
            errs.append('Missing model')
        if not year_s:
            errs.append('Missing year')
        try:
            year = parse_int(year_s) if year_s else None
        except ValueError as e:
            errs.append(str(e))
            year = None
        brand = None
        car_model = None
        if brand_name:
            brand = Brand.objects.filter(name__iexact=brand_name).first()
            if not brand:
                errs.append(f'Unknown brand: {brand_name}')
        if brand and model_name:
            car_model = CarModel.objects.filter(brand=brand, name__iexact=model_name).first()
            if not car_model:
                errs.append(f'Model "{model_name}" not found for brand "{brand_name}"')
        if row.get('price'):
            try:
                parse_decimal(row.get('price'))
            except ValueError as e:
                errs.append(str(e))
        if row.get('mileage'):
            try:
                parse_int(row.get('mileage'))
            except ValueError as e:
                errs.append(str(e))
        mm_s = row.get('model_month')
        if mm_s:
            mm = parse_model_month(mm_s)
            if mm is None:
                errs.append('model_month must be 1–12 or Jan–Dec')
        if row.get('original_price'):
            try:
                parse_decimal(row.get('original_price'))
            except ValueError as e:
                errs.append(str(e))
        fuel = row.get('fuel_type')
        if fuel and fuel not in dict(Car.FUEL_CHOICES):
            errs.append(f'Invalid fuel_type: {fuel}')
        trans = row.get('transmission')
        if trans and trans not in dict(Car.TRANSMISSION_CHOICES):
            errs.append(f'Invalid transmission: {trans}')
        body = row.get('body_type')
        if body and body not in dict(Car.BODY_TYPE_CHOICES):
            errs.append(f'Invalid body_type: {body}')
        own = row.get('ownership')
        if own and own not in dict(Car.OWNERSHIP_CHOICES):
            errs.append(f'Invalid ownership: {own}')
        st = row.get('status')
        if st and st not in dict(Car.STATUS_CHOICES):
            errs.append(f'Invalid status: {st}')
        if errs:
            for m in errs:
                errors.append({'row_num': idx, 'message': m})
            continue
        ok_rows.append({'row_num': idx, 'data': row})
    return ok_rows, errors


def parse_uploaded_csv(file_obj):
    raw = file_obj.read()
    try:
        text = raw.decode('utf-8-sig')
    except UnicodeDecodeError:
        text = raw.decode('latin-1')
    f = io.StringIO(text)
    reader = csv.DictReader(f)
    if not reader.fieldnames:
        raise ValueError('CSV has no header row')
    rows = []
    for line in reader:
        row = {(k or '').strip().lower(): _norm(v) for k, v in line.items()}
        rows.append(row)
    return rows


def apply_import(rows_dicts, replace_all=False):
    """
    Import validated rows. Each item is {'row_num', 'data'}.
    Returns dict: created, updated, skipped with reasons.
    """
    created = 0
    updated = 0
    skipped = []

    def process_row(entry):
        nonlocal created, updated
        row = entry['data']
        row_num = entry['row_num']
        cid = row.get('id')
        brand = Brand.objects.filter(name__iexact=row['brand']).first()
        car_model = CarModel.objects.filter(brand=brand, name__iexact=row['model']).first()
        if not brand or not car_model:
            skipped.append({'row_num': row_num, 'message': 'Brand/model resolution failed'})
            return
        try:
            price = parse_decimal(row.get('price'))
            mileage = parse_int(row.get('mileage'))
        except ValueError as e:
            skipped.append({'row_num': row_num, 'message': str(e)})
            return
        orig = None
        if row.get('original_price'):
            try:
                orig = parse_decimal(row.get('original_price'))
            except ValueError:
                orig = None
        mm_val = parse_model_month(row.get('model_month')) if row.get('model_month') else None
        defaults = {
            'seller': None,
            'title': row['title'],
            'brand': brand,
            'model': car_model,
            'year': parse_int(row.get('year')),
            'model_month': mm_val,
            'variant': row.get('variant') or '',
            'price': price,
            'original_price': orig,
            'mileage': mileage,
            'fuel_type': row.get('fuel_type') or 'Petrol',
            'transmission': row.get('transmission') or 'MT',
            'body_type': row.get('body_type') or 'Hatchback',
            'ownership': row.get('ownership') or '1st Owner',
            # CSV import is always draft: staff approves in the panel (ignore status column).
            'status': 'PENDING',
            'city': row.get('city') or 'Ahmedabad',
            'color': row.get('color') or '',
            'registration_year': '',
            'insurance_validity': '',
            'insurance_type': '',
            'rto': '',
            'village_area': '',
            'registration_state': '',
            'sell_timeline': '',
            'contact_name': '',
            'contact_number': '',
            'description': row.get('description') or '',
            'is_featured': parse_bool(row.get('is_featured')),
        }
        car = None
        if cid:
            try:
                car = Car.objects.filter(pk=int(cid)).first()
            except (TypeError, ValueError):
                car = None
        if car is None:
            q = Car.objects.filter(
                title=defaults['title'],
                model=car_model,
                year=defaults['year'],
            )
            if defaults['model_month'] is None:
                q = q.filter(model_month__isnull=True)
            else:
                q = q.filter(model_month=defaults['model_month'])
            car = q.first()
        try:
            if car:
                for k, v in defaults.items():
                    setattr(car, k, v)
                car.full_clean()
                car.save()
                updated += 1
            else:
                c = Car(**defaults)
                c.full_clean()
                c.save()
                created += 1
        except Exception as e:
            skipped.append({'row_num': row_num, 'message': str(e)})

    with transaction.atomic():
        if replace_all:
            Car.objects.all().delete()
        for entry in rows_dicts:
            process_row(entry)

    return {'created': created, 'updated': updated, 'skipped': skipped}


def _car_to_csv_row(car):
    return {
        'id': car.pk,
        'title': car.title,
        'brand': car.brand.name,
        'model': car.model.name,
        'year': car.year,
        'model_month': calendar.month_abbr[car.model_month] if car.model_month else '',
        'variant': car.variant,
        'price': str(car.price),
        'mileage': car.mileage,
        'fuel_type': car.fuel_type,
        'transmission': car.transmission,
        'body_type': car.body_type,
        'ownership': car.ownership,
        'status': car.status,
        'city': car.city,
        'color': car.color,
        'description': car.description,
        'is_featured': '1' if car.is_featured else '0',
        'original_price': str(car.original_price) if car.original_price is not None else '',
        'created_at': car.created_at.isoformat() if car.created_at else '',
        'listed_at': car.listed_at.isoformat() if car.listed_at else '',
    }


def export_cars_csv(queryset=None):
    """Return UTF-8 CSV bytes. If queryset is None, export all cars (newest id first)."""
    qs = queryset
    if qs is None:
        qs = Car.objects.select_related('brand', 'model').order_by('-id')
    out = io.StringIO()
    w = csv.DictWriter(out, fieldnames=CSV_HEADERS, extrasaction='ignore')
    w.writeheader()
    for car in qs.select_related('brand', 'model').iterator(chunk_size=500):
        w.writerow(_car_to_csv_row(car))
    return ('\ufeff' + out.getvalue()).encode('utf-8')
