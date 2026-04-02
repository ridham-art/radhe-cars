"""
Merge two Brand rows that share the same name: move models & cars to the keeper, then delete the duplicate.

Example (auto-pick keeper = brand with most cars):
    python manage.py merge_duplicate_brands --name "Maruti Suzuki"

Example (explicit PKs — keeper first):
    python manage.py merge_duplicate_brands --keep 3 --remove 7

Use --dry-run to print the plan without writing.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count

from cars.models import Brand, Car, CarModel


def reassign_other_fks_to_carmodel(source: CarModel, target: CarModel) -> int:
    """
    Point every FK to `source` (except Car) at `target`. Car is updated separately in merge_brand_into.
    Handles extra tables in DB (e.g. model variants) that reference cars_carmodel.
    """
    from django.db import connection
    from django.db.models.fields.related import ForeignKey

    if source.pk == target.pk:
        return 0
    total = 0
    for rel in CarModel._meta.related_objects:
        if rel.auto_created:
            continue
        fk = rel.field
        if not isinstance(fk, ForeignKey):
            continue
        if fk.remote_field.model is not CarModel:
            continue
        related_model = rel.related_model
        if related_model is Car:
            continue
        n = related_model.objects.filter(**{fk.name: source}).update(**{fk.name: target})
        total += n

    # Tables that reference cars_carmodel but are not (yet) in Django models — e.g. cars_modelvariant
    for table, col in (
        ('cars_modelvariant', 'car_model_id'),
    ):
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    f'UPDATE "{table}" SET "{col}" = %s WHERE "{col}" = %s',
                    [target.pk, source.pk],
                )
                total += cursor.rowcount
        except Exception:
            pass

    return total


def merge_brand_into(keeper: Brand, duplicate: Brand) -> dict:
    """
    Move every CarModel and Car from `duplicate` onto `keeper`, then delete `duplicate`.
    When a model name already exists on `keeper`, cars are reassigned to that model.
    """
    if keeper.pk == duplicate.pk:
        raise ValueError('keeper and duplicate must differ')

    moved = {'models_merged': 0, 'models_relinked': 0, 'cars_updated': 0, 'other_fks': 0}

    with transaction.atomic():
        for m in list(CarModel.objects.filter(brand=duplicate).select_for_update()):
            twin = CarModel.objects.filter(brand=keeper, name=m.name).first()
            if twin:
                n = Car.objects.filter(model=m).update(model=twin, brand=keeper)
                moved['cars_updated'] += n
                moved['models_merged'] += 1
                moved['other_fks'] += reassign_other_fks_to_carmodel(m, twin)
                m.delete()
            else:
                m.brand = keeper
                m.save(update_fields=['brand'])
                n = Car.objects.filter(model=m).update(brand=keeper)
                moved['cars_updated'] += n
                moved['models_relinked'] += 1

        Car.objects.filter(brand=duplicate).update(brand=keeper)
        duplicate.delete()

    return moved


class Command(BaseCommand):
    help = 'Merge duplicate brands (same name): keep one brand, move others into it.'

    def add_arguments(self, parser):
        parser.add_argument('--name', type=str, help='Brand name (e.g. Maruti Suzuki); finds all duplicates')
        parser.add_argument('--keep', type=int, help='PK of brand to keep')
        parser.add_argument('--remove', type=int, help='PK of duplicate brand to merge and delete')
        parser.add_argument('--dry-run', action='store_true', help='Show plan only')

    def handle(self, *args, **options):
        name = (options.get('name') or '').strip()
        keep_id = options.get('keep')
        remove_id = options.get('remove')
        dry = options['dry_run']

        if keep_id and remove_id:
            keeper = Brand.objects.get(pk=keep_id)
            dup = Brand.objects.get(pk=remove_id)
            if keeper.name.strip().lower() != dup.name.strip().lower():
                self.stdout.write(
                    self.style.WARNING(
                        f'Warning: names differ ({keeper.name!r} vs {dup.name!r}); still merging as requested.'
                    )
                )
            self.stdout.write(f'Keeping pk={keeper.pk} {keeper.name!r}, removing pk={dup.pk} {dup.name!r}')
            if dry:
                self.stdout.write(self.style.WARNING('Dry run — no changes.'))
                return
            stats = merge_brand_into(keeper, dup)
            self.stdout.write(self.style.SUCCESS(f'Done: {stats}'))
            return

        if not name:
            self.stderr.write('Provide --name "Brand" or both --keep and --remove.')
            return

        brands = (
            Brand.objects.filter(name__iexact=name)
            .annotate(_cars=Count('car', distinct=True))
            .order_by('-_cars', 'pk')
        )
        if brands.count() < 2:
            self.stdout.write('No duplicate brands found for that name (need at least 2).')
            return

        keeper = brands.first()
        self.stdout.write(
            f'Keeper: pk={keeper.pk} {keeper.name!r} ({keeper._cars} cars)'
        )
        for dup in brands[1:]:
            dup_pk = dup.pk
            self.stdout.write(
                f'  Merge into keeper: pk={dup_pk} {dup.name!r} ({dup._cars} cars)'
            )
            if dry:
                continue
            stats = merge_brand_into(keeper, dup)
            self.stdout.write(self.style.SUCCESS(f'  Merged duplicate pk={dup_pk}: {stats}'))

        if dry:
            self.stdout.write(self.style.WARNING('Dry run — no changes.'))
