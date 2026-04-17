import calendar
import io
import uuid

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import models
from django.contrib.auth.models import User
from PIL import Image, ImageOps

WEBP_QUALITY = 75


def _safe_delete_stored_file(name):
    if not name:
        return
    try:
        default_storage.delete(name)
    except Exception:
        pass


def _resize_to_webp_bytes(file_like, max_width):
    """
    Resize (max width, aspect preserved) and encode as WebP at WEBP_QUALITY.
    Returns raw bytes.
    """
    img = Image.open(file_like)
    try:
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass

    if img.mode not in ('RGB', 'RGBA'):
        if img.mode == 'P' and 'transparency' in img.info:
            img = img.convert('RGBA')
        else:
            img = img.convert('RGB')

    w, h = img.size
    if w > max_width:
        new_h = max(1, int(round(h * (max_width / float(w)))))
        img = img.resize((max_width, new_h), Image.Resampling.LANCZOS)

    buf = io.BytesIO()
    save_kw = {'format': 'WEBP', 'quality': WEBP_QUALITY, 'method': 6}
    if img.mode == 'RGBA':
        img.save(buf, **save_kw)
    else:
        rgb = img.convert('RGB')
        rgb.save(buf, **save_kw)
    return buf.getvalue()


def _assign_webp(field, folder, max_width, previous_name):
    """
    Replace ImageField contents with processed WebP. Returns new stored name
    (relative path) or None if processing was skipped/failed.
    """
    if not field:
        return None
    try:
        field.open('rb')
        try:
            raw = field.read()
        finally:
            field.close()
        data = _resize_to_webp_bytes(io.BytesIO(raw), max_width)
        new_name = f'{folder}/{uuid.uuid4().hex}.webp'
        field.save(new_name, ContentFile(data), save=False)
        return field.name
    except Exception:
        return previous_name


class Brand(models.Model):
    name = models.CharField(max_length=100)
    logo = models.ImageField(upload_to='brands/', null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']

    def save(self, *args, **kwargs):
        old_logo_name = None
        if self.pk:
            try:
                prev = Brand.objects.only('logo').get(pk=self.pk)
                if prev.logo:
                    old_logo_name = prev.logo.name
            except Brand.DoesNotExist:
                pass

        if self.logo:
            if not self.pk or not old_logo_name or getattr(self.logo, 'name', None) != old_logo_name:
                try:
                    _assign_webp(self.logo, 'brands', 300, old_logo_name)
                except Exception:
                    pass

        super().save(*args, **kwargs)

        has_logo = bool(self.logo and getattr(self.logo, 'name', None))
        if old_logo_name and has_logo and self.logo.name != old_logo_name:
            _safe_delete_stored_file(old_logo_name)
        elif old_logo_name and not has_logo:
            _safe_delete_stored_file(old_logo_name)


class CarModel(models.Model):
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='models')
    name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.brand.name} {self.name}"

    class Meta:
        ordering = ['brand__name', 'name']


class Car(models.Model):
    FUEL_CHOICES = [
        ('Petrol', 'Petrol'),
        ('Diesel', 'Diesel'),
        ('Petrol + CNG', 'Petrol + CNG'),
        ('Electric', 'Electric'),
    ]
    TRANSMISSION_CHOICES = [
        ('MT', 'Manual'),
        ('AT', 'Auto'),
    ]
    OWNERSHIP_CHOICES = [
        ('1st Owner', '1st Owner'),
        ('2nd Owner', '2nd Owner'),
        ('3rd Owner', '3rd Owner'),
        ('4th+ Owner', '4th+ Owner'),
    ]
    BODY_TYPE_CHOICES = [
        ('Hatchback', 'Hatchback'),
        ('Sedan', 'Sedan'),
        ('SUV', 'SUV'),
        ('MUV', 'MUV'),
        ('Luxury', 'Luxury'),
    ]
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('ON_HOLD', 'On Hold'),
        ('SOLD', 'Sold'),
        ('REJECTED', 'Rejected'),
    ]

    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cars', null=True, blank=True)
    title = models.CharField(max_length=200)
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT)
    model = models.ForeignKey(CarModel, on_delete=models.PROTECT)
    year = models.IntegerField()
    model_month = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        help_text='Optional manufacturing month (stored as 1–12). Choose Jan–Dec in forms; customers see e.g. Jan 2021.',
    )
    variant = models.CharField(max_length=100, blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    original_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Strikethrough price for discount display")
    mileage = models.IntegerField(help_text="KM Driven")
    fuel_type = models.CharField(max_length=20, choices=FUEL_CHOICES)
    transmission = models.CharField(max_length=20, choices=TRANSMISSION_CHOICES)
    body_type = models.CharField(max_length=20, choices=BODY_TYPE_CHOICES, default='Hatchback')
    ownership = models.CharField(max_length=20, choices=OWNERSHIP_CHOICES)
    color = models.CharField(max_length=50, blank=True)
    registration_year = models.CharField(max_length=20, blank=True)
    insurance_validity = models.CharField(max_length=50, blank=True)
    insurance_type = models.CharField(max_length=50, blank=True)
    rto = models.CharField(max_length=20, blank=True)

    village_area = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, default="Ahmedabad")

    registration_state = models.CharField(max_length=50, blank=True, help_text="e.g. GJ - Gujarat")
    sell_timeline = models.CharField(max_length=100, blank=True, help_text="When seller plans to sell")

    contact_name = models.CharField(max_length=100, blank=True)
    contact_number = models.CharField(max_length=20, blank=True)
    description = models.TextField(blank=True)

    is_featured = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    # Sell form (public /sell/) — staff reviews under "Sell car inquiries", not main Cars list
    submit_via_sell_form = models.BooleanField(default=False)
    sell_inquiry_seen = models.BooleanField(
        default=False,
        help_text='Staff has opened Sell car inquiries; used for sidebar badge.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    listed_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        editable=False,
        help_text='When the car was first approved / listed (set automatically; not shown on the public site).',
    )
    sold_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        editable=False,
        help_text='When the car was marked sold (used to auto-hide sold cars from public pages after 7 days).',
    )

    def __str__(self):
        return f"{self.year} {self.brand.name} {self.model.name} - {self.title}"

    def save(self, *args, **kwargs):
        from django.utils import timezone as dj_tz

        prev_status = None
        if self.pk:
            try:
                prev_status = Car.objects.only('status').get(pk=self.pk).status
            except Car.DoesNotExist:
                prev_status = None

        if self.status == 'APPROVED' and self.listed_at is None:
            self.listed_at = dj_tz.now()
        if self.status == 'SOLD':
            if prev_status != 'SOLD' or self.sold_at is None:
                self.sold_at = dj_tz.now()
        elif prev_status == 'SOLD':
            self.sold_at = None
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if self.brand_id and self.model_id and self.model.brand_id != self.brand_id:
            raise ValidationError({'model': 'Selected model must belong to the selected brand.'})
        if self.title and self.model_id and self.year is not None:
            dup = Car.objects.filter(title=self.title, model_id=self.model_id, year=self.year)
            if self.pk:
                dup = dup.exclude(pk=self.pk)
            if self.model_month is None:
                dup = dup.filter(model_month__isnull=True)
            else:
                dup = dup.filter(model_month=self.model_month)
            if dup.exists():
                raise ValidationError('A car with this title, model, year, and month already exists.')

    @property
    def primary_image(self):
        # Use prefetched images when present (avoids N+1 on list pages).
        cache = getattr(self, '_prefetched_objects_cache', None)
        if cache and 'images' in cache:
            imgs = list(self.images.all())
            for img in imgs:
                if img.is_primary:
                    return img
            if imgs:
                return imgs[0]
            # Prefetch may be intentionally restricted (e.g., only primary rows).
            # Fallback to DB for legacy rows where primary flag is missing.
            img = self.images.filter(is_primary=True).first()
            if img:
                return img
            return self.images.first()
        img = self.images.filter(is_primary=True).first()
        if not img:
            img = self.images.first()
        return img

    @property
    def price_display(self):
        p = float(self.price)
        if p >= 100000:
            return f"₹{p / 100000:.1f} Lakh"
        return f"₹{p:,.0f}"

    @property
    def original_price_display(self):
        if not self.original_price:
            return None
        p = float(self.original_price)
        if p >= 100000:
            return f"₹{p / 100000:.2f} Lakh"
        return f"₹{p:,.0f}"

    @property
    def savings_display(self):
        if not self.original_price:
            return None
        diff = float(self.original_price) - float(self.price)
        if diff > 0:
            return f"₹{diff:,.0f}"
        return None

    @property
    def mileage_display(self):
        if self.mileage >= 1000:
            return f"{self.mileage // 1000}K km"
        return f"{self.mileage} km"

    @property
    def make_year_display(self):
        if self.model_month is not None and 1 <= self.model_month <= 12:
            return f"{calendar.month_abbr[self.model_month]} {self.year}"
        return str(self.year)

    @property
    def specs_short(self):
        parts = [self.mileage_display, self.get_fuel_type_display(), self.get_transmission_display()]
        return " • ".join(parts)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at'], name='car_status_created_idx'),
            models.Index(fields=['brand', 'status'], name='car_brand_status_idx'),
            models.Index(
                fields=['submit_via_sell_form', 'sell_inquiry_seen'],
                name='car_sell_seen_idx',
            ),
            models.Index(
                fields=['submit_via_sell_form', 'status', 'created_at'],
                name='car_sell_status_created_idx',
            ),
        ]


class CarImage(models.Model):
    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='cars/', null=True, blank=True)
    image_url = models.URLField(max_length=500, blank=True, help_text="External image URL (used for seed/demo data)")
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def display_url(self):
        if self.image and self.image.name:
            try:
                return self.image.url
            except (ValueError, AttributeError):
                pass
        return self.image_url or ''

    def __str__(self):
        return f"Image for {self.car.title}"

    def save(self, *args, **kwargs):
        old_image_name = None
        if self.pk:
            try:
                prev = CarImage.objects.only('image').get(pk=self.pk)
                if prev.image:
                    old_image_name = prev.image.name
            except CarImage.DoesNotExist:
                pass

        if self.image:
            if not self.pk or not old_image_name or getattr(self.image, 'name', None) != old_image_name:
                try:
                    _assign_webp(self.image, 'cars', 1200, old_image_name)
                except Exception:
                    pass

        super().save(*args, **kwargs)

        has_img = bool(self.image and getattr(self.image, 'name', None))
        if old_image_name and has_img and self.image.name != old_image_name:
            _safe_delete_stored_file(old_image_name)
        elif old_image_name and not has_img:
            _safe_delete_stored_file(old_image_name)


class Inquiry(models.Model):
    SUBJECT_CHOICES = [
        ('buy', 'I want to buy a car'),
        ('sell', 'I want to sell my car'),
        ('support', 'General Inquiry / Support'),
    ]

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    subject = models.CharField(max_length=20, choices=SUBJECT_CHOICES, blank=True)
    message = models.TextField()
    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name='inquiries', null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Inquiries"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.get_subject_display() or 'Inquiry'}"


class Testimonial(models.Model):
    name = models.CharField(max_length=100)
    designation = models.CharField(max_length=200, blank=True)
    image = models.ImageField(upload_to='testimonials/')
    video_url = models.URLField(blank=True, help_text="Optional YouTube/video link")
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        old_image_name = None
        if self.pk:
            try:
                prev = Testimonial.objects.only('image').get(pk=self.pk)
                if prev.image:
                    old_image_name = prev.image.name
            except Testimonial.DoesNotExist:
                pass

        if self.image:
            if not self.pk or not old_image_name or getattr(self.image, 'name', None) != old_image_name:
                try:
                    _assign_webp(self.image, 'testimonials', 500, old_image_name)
                except Exception:
                    pass

        super().save(*args, **kwargs)

        has_img = bool(self.image and getattr(self.image, 'name', None))
        if old_image_name and has_img and self.image.name != old_image_name:
            _safe_delete_stored_file(old_image_name)
        elif old_image_name and not has_img:
            _safe_delete_stored_file(old_image_name)


class Wishlist(models.Model):
    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name='wishlisted_by')
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['car', 'user']

    def __str__(self):
        return f"{self.user} - {self.car.title}"
