from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth.models import User


class Brand(models.Model):
    name = models.CharField(max_length=100)
    logo = models.ImageField(upload_to='brands/', null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


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
        ('CNG', 'CNG'),
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
    ]

    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cars', null=True, blank=True)
    title = models.CharField(max_length=200)
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT)
    model = models.ForeignKey(CarModel, on_delete=models.PROTECT)
    year = models.IntegerField()
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
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='APPROVED')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.year} {self.brand.name} {self.model.name} - {self.title}"

    def clean(self):
        super().clean()
        if self.brand_id and self.model_id and self.model.brand_id != self.brand_id:
            raise ValidationError({'model': 'Selected model must belong to the selected brand.'})
        if self.title and self.model_id and self.year is not None:
            dup = Car.objects.filter(title=self.title, model_id=self.model_id, year=self.year)
            if self.pk:
                dup = dup.exclude(pk=self.pk)
            if dup.exists():
                raise ValidationError('A car with this title, model, and year already exists.')

    @property
    def primary_image(self):
        # Use prefetched images when present (avoids N+1 on list pages).
        cache = getattr(self, '_prefetched_objects_cache', None)
        if cache and 'images' in cache:
            imgs = list(self.images.all())
            if not imgs:
                return None
            for img in imgs:
                if img.is_primary:
                    return img
            return imgs[0]
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
    def specs_short(self):
        parts = [self.mileage_display, self.fuel_type, self.get_transmission_display()]
        return " • ".join(parts)

    class Meta:
        ordering = ['-created_at']


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


class Wishlist(models.Model):
    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name='wishlisted_by')
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['car', 'user']

    def __str__(self):
        return f"{self.user} - {self.car.title}"
