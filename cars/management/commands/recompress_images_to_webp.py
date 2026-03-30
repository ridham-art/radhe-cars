"""
Bulk-recompress existing ImageField files to WebP (same rules as models.save).

Does not call Model.save() — uses queryset.update() so images are not double-processed.

Usage:
  python manage.py recompress_images_to_webp
  python manage.py recompress_images_to_webp --dry-run
  python manage.py recompress_images_to_webp --force   # include already-.webp files
"""
import io
import uuid

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand

from cars.models import Brand, CarImage, Testimonial, _resize_to_webp_bytes, _safe_delete_stored_file

MAX_WIDTH = {
    'brands': 300,
    'cars': 1200,
    'testimonials': 500,
}


def _safe_repr_path(path):
    """Avoid UnicodeEncodeError on Windows consoles."""
    if path is None:
        return ''
    try:
        return str(path).encode('ascii', errors='replace').decode('ascii')
    except Exception:
        return repr(path)


def _recompress_one(path, folder, max_width):
    """
    Read file at path from default storage, return new storage path or (None, error).
    """
    if not path:
        return None, 'empty path'
    try:
        if not default_storage.exists(path):
            return None, 'missing on storage'
    except Exception as e:
        return None, str(e)
    try:
        with default_storage.open(path, 'rb') as fh:
            raw = fh.read()
        data = _resize_to_webp_bytes(io.BytesIO(raw), max_width)
        new_name = f'{folder}/{uuid.uuid4().hex}.webp'
        saved = default_storage.save(new_name, ContentFile(data))
        return saved, None
    except Exception as e:
        return None, str(e)


class Command(BaseCommand):
    help = 'Recompress Brand, CarImage, and Testimonial images to WebP in bulk'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Print actions without writing or deleting files',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Recompress even if path already ends with .webp',
        )

    def handle(self, *args, **options):
        dry = options['dry_run']
        force = options['force']
        stats = {'ok': 0, 'skip': 0, 'err': 0}

        def maybe_skip_webp(path):
            if force:
                return False
            return path.lower().endswith('.webp')

        # --- Brand ---
        for brand in Brand.objects.exclude(logo__isnull=True).exclude(logo='').iterator():
            path = brand.logo.name
            if maybe_skip_webp(path):
                self.stdout.write(f'[Brand {brand.pk}] skip (already webp): {_safe_repr_path(path)}')
                stats['skip'] += 1
                continue
            if dry:
                self.stdout.write(f'[Brand {brand.pk}] would convert: {_safe_repr_path(path)}')
                stats['ok'] += 1
                continue
            new_path, err = _recompress_one(path, 'brands', MAX_WIDTH['brands'])
            if err:
                self.stderr.write(f'[Brand {brand.pk}] {_safe_repr_path(path)}: {err}')
                stats['err'] += 1
                continue
            Brand.objects.filter(pk=brand.pk).update(logo=new_path)
            if new_path != path:
                _safe_delete_stored_file(path)
            self.stdout.write(
                self.style.SUCCESS(
                    f'[Brand {brand.pk}] {_safe_repr_path(path)} -> {_safe_repr_path(new_path)}'
                )
            )
            stats['ok'] += 1

        # --- CarImage (skip rows with no file, only external URL) ---
        for ci in CarImage.objects.exclude(image__isnull=True).exclude(image='').iterator():
            path = ci.image.name
            if maybe_skip_webp(path):
                self.stdout.write(f'[CarImage {ci.pk}] skip (already webp): {_safe_repr_path(path)}')
                stats['skip'] += 1
                continue
            if dry:
                self.stdout.write(f'[CarImage {ci.pk}] would convert: {_safe_repr_path(path)}')
                stats['ok'] += 1
                continue
            new_path, err = _recompress_one(path, 'cars', MAX_WIDTH['cars'])
            if err:
                self.stderr.write(f'[CarImage {ci.pk}] {_safe_repr_path(path)}: {err}')
                stats['err'] += 1
                continue
            CarImage.objects.filter(pk=ci.pk).update(image=new_path)
            if new_path != path:
                _safe_delete_stored_file(path)
            self.stdout.write(
                self.style.SUCCESS(
                    f'[CarImage {ci.pk}] {_safe_repr_path(path)} -> {_safe_repr_path(new_path)}'
                )
            )
            stats['ok'] += 1

        # --- Testimonial ---
        for t in Testimonial.objects.exclude(image__isnull=True).exclude(image='').iterator():
            path = t.image.name
            if maybe_skip_webp(path):
                self.stdout.write(f'[Testimonial {t.pk}] skip (already webp): {_safe_repr_path(path)}')
                stats['skip'] += 1
                continue
            if dry:
                self.stdout.write(f'[Testimonial {t.pk}] would convert: {_safe_repr_path(path)}')
                stats['ok'] += 1
                continue
            new_path, err = _recompress_one(path, 'testimonials', MAX_WIDTH['testimonials'])
            if err:
                self.stderr.write(f'[Testimonial {t.pk}] {_safe_repr_path(path)}: {err}')
                stats['err'] += 1
                continue
            Testimonial.objects.filter(pk=t.pk).update(image=new_path)
            if new_path != path:
                _safe_delete_stored_file(path)
            self.stdout.write(
                self.style.SUCCESS(
                    f'[Testimonial {t.pk}] {_safe_repr_path(path)} -> {_safe_repr_path(new_path)}'
                )
            )
            stats['ok'] += 1

        if dry:
            self.stdout.write(
                self.style.WARNING(
                    f'Done (dry-run). would_process={stats["ok"]} skipped={stats["skip"]} errors={stats["err"]}'
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f'Done. converted={stats["ok"]} skipped={stats["skip"]} errors={stats["err"]}'
                )
            )
