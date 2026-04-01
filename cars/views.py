from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, F, Prefetch, Count
from django.db.models.functions import Coalesce
from django.http import HttpResponse, JsonResponse
from .models import Car, Brand, CarModel, CarImage, Testimonial, Wishlist

# One query batch for car images (primary first) — avoids dozens of round-trips to the DB per page.
_CAR_IMAGES_PREFETCH = Prefetch(
    'images',
    queryset=CarImage.objects.order_by('-is_primary', 'id'),
)
# Wishlist → Car → images
_WISHLIST_CAR_IMAGES = Prefetch(
    'car__images',
    queryset=CarImage.objects.order_by('-is_primary', 'id'),
)


def _cars_with_related(qs):
    return qs.select_related('brand', 'model').prefetch_related(_CAR_IMAGES_PREFETCH)
from .forms import SignUpForm, ContactForm

MIN_IMAGES = 3
MAX_IMAGES = 20


def health_check(request):
    """No DB — if this returns 200 but / returns 500, the crash is DB or app logic."""
    return HttpResponse('ok', content_type='text/plain')


def home(request):
    featured_cars = _cars_with_related(
        Car.objects.filter(status='APPROVED', is_featured=True).annotate(wishlist_entry_count=Count('wishlisted_by'))
    )[:12]
    recent_cars = _cars_with_related(
        Car.objects.filter(status='APPROVED').order_by('-created_at').annotate(wishlist_entry_count=Count('wishlisted_by'))
    )[:12]
    testimonials = Testimonial.objects.filter(is_active=True)[:4]
    wishlisted_ids = set()
    if request.user.is_authenticated:
        car_ids = list(featured_cars.values_list('pk', flat=True)) + list(recent_cars.values_list('pk', flat=True))
        wishlisted_ids = set(Wishlist.objects.filter(user=request.user, car_id__in=car_ids).values_list('car_id', flat=True))

    context = {
        'featured_cars': featured_cars,
        'recent_cars': recent_cars,
        'testimonials': testimonials,
        'wishlisted_ids': wishlisted_ids,
    }
    return render(request, 'cars/home.html', context)


def home_cars_api(request):
    """AJAX: Return cars filtered by body_type for home page Recently Added section."""
    from django.template.loader import render_to_string
    cars = _cars_with_related(
        Car.objects.filter(status='APPROVED').order_by('-created_at').annotate(wishlist_entry_count=Count('wishlisted_by'))
    )
    body_type = request.GET.get('body_type', '').strip()
    if body_type:
        cars = cars.filter(body_type__iexact=body_type)
    cars = cars[:12]
    wishlisted_ids = set()
    if request.user.is_authenticated:
        wishlisted_ids = set(Wishlist.objects.filter(user=request.user, car__in=cars).values_list('car_id', flat=True))
    html = render_to_string('cars/_home_car_cards.html', {'cars': cars, 'wishlisted_ids': wishlisted_ids}, request=request)
    return JsonResponse({'html': html, 'count': len(cars)})


def car_list(request):
    cars = Car.objects.filter(status='APPROVED')
    brands = Brand.objects.all()

    q = request.GET.get('q')
    brand = request.GET.get('brand')
    model = request.GET.get('model')
    body_type = request.GET.get('body_type')
    fuel = request.GET.get('fuel')
    transmission = request.GET.get('transmission')
    ownership = request.GET.get('ownership')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    min_year = request.GET.get('min_year')
    max_year = request.GET.get('max_year')
    min_km = request.GET.get('min_km')
    max_km = request.GET.get('max_km')
    sort = request.GET.get('sort', 'relevance')

    if q:
        cars = cars.filter(
            Q(title__icontains=q) | Q(model__name__icontains=q) | Q(brand__name__icontains=q)
        )
    if brand:
        cars = cars.filter(brand__name__iexact=brand)
    if model:
        cars = cars.filter(model__name__iexact=model)
    if body_type:
        cars = cars.filter(body_type__iexact=body_type)
    if fuel:
        cars = cars.filter(fuel_type__iexact=fuel)
    if transmission:
        cars = cars.filter(transmission__iexact=transmission)
    if ownership:
        cars = cars.filter(ownership__iexact=ownership)
    if min_price:
        cars = cars.filter(price__gte=min_price)
    if max_price:
        cars = cars.filter(price__lte=max_price)
    if min_year:
        cars = cars.filter(year__gte=min_year)
    if max_year:
        cars = cars.filter(year__lte=max_year)
    if min_km:
        cars = cars.filter(mileage__gte=min_km)
    if max_km:
        cars = cars.filter(mileage__lte=max_km)

    if sort == 'discount':
        cars = cars.annotate(discount=Coalesce(F('original_price'), F('price')) - F('price')).order_by('-discount', '-created_at')
    elif sort == 'price_low':
        cars = cars.order_by('price', '-created_at')
    elif sort == 'price_high':
        cars = cars.order_by('-price', '-created_at')
    elif sort == 'km_low':
        cars = cars.order_by('mileage', '-created_at')
    elif sort == 'year_new':
        cars = cars.order_by('-year', '-created_at')
    elif sort == 'newest':
        cars = cars.order_by('-created_at')
    else:
        cars = cars.order_by('-created_at')

    cars = _cars_with_related(cars.annotate(wishlist_entry_count=Count('wishlisted_by')))

    import datetime
    current_year = datetime.datetime.now().year
    year_range = list(range(current_year, 2004, -1))

    per_page = request.GET.get('per_page', 30)
    try:
        per_page = min(50, max(9, int(per_page)))
    except (ValueError, TypeError):
        per_page = 30
    paginator = Paginator(cars, per_page)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    cars_page = page_obj.object_list

    wishlisted_ids = set()
    if request.user.is_authenticated:
        wishlisted_ids = set(Wishlist.objects.filter(car__in=cars_page).filter(user=request.user).values_list('car_id', flat=True))

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        from django.template.loader import render_to_string
        html = render_to_string('cars/_car_grid.html', {'cars': cars_page, 'wishlisted_ids': wishlisted_ids}, request=request)
        pagination_html = render_to_string('cars/_pagination.html', {'page_obj': page_obj, 'request': request}, request=request)
        return JsonResponse({
            'html': html,
            'count': paginator.count,
            'pagination_html': pagination_html,
            'page': page_obj.number,
            'total_pages': paginator.num_pages,
            'per_page': per_page,
        })

    context = {
        'cars': cars_page,
        'page_obj': page_obj,
        'brands': brands,
        'body_types': Car.BODY_TYPE_CHOICES,
        'fuel_types': Car.FUEL_CHOICES,
        'transmission_types': Car.TRANSMISSION_CHOICES,
        'ownership_types': Car.OWNERSHIP_CHOICES,
        'year_range': year_range,
        'wishlisted_ids': wishlisted_ids,
    }
    return render(request, 'cars/car_list.html', context)


def car_detail(request, pk):
    car = get_object_or_404(
        _cars_with_related(Car.objects.filter(status='APPROVED')),
        pk=pk,
    )
    similar_cars = _cars_with_related(
        Car.objects.filter(status='APPROVED', brand=car.brand).exclude(pk=car.pk)
    )[:3]
    testimonials = Testimonial.objects.filter(is_active=True)[:3]
    wishlist_count = car.wishlisted_by.count()
    in_wishlist = request.user.is_authenticated and car.wishlisted_by.filter(user=request.user).exists()

    context = {
        'car': car,
        'similar_cars': similar_cars,
        'testimonials': testimonials,
        'wishlist_count': wishlist_count,
        'in_wishlist': in_wishlist,
    }
    return render(request, 'cars/car_detail.html', context)


def contact(request):
    if request.method == 'POST':
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            if is_ajax:
                return JsonResponse({'success': True, 'message': 'Your message has been sent successfully! We will get back to you soon.'})
            messages.success(request, 'Your message has been sent successfully! We will get back to you soon.')
            return redirect('contact')
        else:
            if is_ajax:
                return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    else:
        form = ContactForm()
    return render(request, 'cars/contact.html', {'form': form})


def _km_range_to_mileage(km_range):
    if not km_range:
        return 0
    import re
    s = km_range.replace(',', '').replace(' ', '')
    nums = re.findall(r'\d+', s)
    if not nums:
        return 0
    nums = [int(n) for n in nums]
    if 'Upto' in km_range or 'upto' in km_range.lower():
        return nums[0] // 2 if nums else 0
    if 'Above' in km_range or 'above' in km_range.lower():
        return nums[0] + 25000 if nums else 0
    if len(nums) >= 2:
        return (nums[0] + nums[1]) // 2
    return nums[0] if nums else 0


def _map_transmission(val):
    if not val:
        return 'MT'
    v = str(val).upper()
    if v in ('AUTOMATIC', 'AT'):
        return 'AT'
    return 'MT'


def _map_fuel(val):
    if not val:
        return 'Petrol'
    v = str(val).upper()
    mapping = {'PETROL': 'Petrol', 'DIESEL': 'Diesel', 'CNG': 'CNG', 'ELECTRIC': 'Electric'}
    return mapping.get(v, 'Petrol')


def sell_car(request):
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
    if request.method == 'POST':
        post = request.POST
        images = request.FILES.getlist('images')

        if len(images) < MIN_IMAGES:
            if is_ajax:
                return JsonResponse({'success': False, 'message': f'Please upload at least {MIN_IMAGES} images.'}, status=400)
            messages.error(request, f'Please upload at least {MIN_IMAGES} images.')
        elif len(images) > MAX_IMAGES:
            if is_ajax:
                return JsonResponse({'success': False, 'message': f'You can upload maximum {MAX_IMAGES} images.'}, status=400)
            messages.error(request, f'You can upload maximum {MAX_IMAGES} images.')
        else:
            brand_id = post.get('brand')
            model_id = post.get('model')
            year = post.get('year')
            price = post.get('price')

            errors = []
            if not brand_id:
                errors.append('Brand is required.')
            if not model_id:
                errors.append('Model is required.')
            if not year:
                errors.append('Year is required.')
            if not price:
                errors.append('Price is required.')

            if errors:
                if is_ajax:
                    return JsonResponse({'success': False, 'message': ' '.join(errors), 'errors': {}}, status=400)
                for e in errors:
                    messages.error(request, e)
            else:
                try:
                    brand = Brand.objects.get(pk=brand_id)
                    car_model = CarModel.objects.get(pk=model_id, brand=brand)
                    year = int(year)
                    price = float(str(price).replace(',', ''))
                    mileage = _km_range_to_mileage(post.get('km_range', ''))
                    fuel_type = _map_fuel(post.get('fuel_type', 'Petrol'))
                    transmission = _map_transmission(post.get('transmission', 'MANUAL'))
                    variant = post.get('variant', '').strip()
                    rto = post.get('rto_code', '').strip()
                    city = post.get('city', 'Ahmedabad').strip() or 'Ahmedabad'
                    registration_state = post.get('registration_state', 'GJ - Gujarat').strip()
                    sell_timeline = post.get('sell_timeline', '').strip()
                    contact_number = post.get('contact_number', '').strip()
                    description = post.get('description', '').strip()

                    title_parts = [str(year), brand.name, car_model.name]
                    if variant:
                        title_parts.append(variant)
                    title = ' '.join(title_parts)

                    if sell_timeline:
                        description = f"Sell timeline: {sell_timeline}. " + description if description else f"Sell timeline: {sell_timeline}"

                    car = Car(
                        title=title,
                        brand=brand,
                        model=car_model,
                        year=year,
                        variant=variant,
                        price=price,
                        mileage=mileage,
                        fuel_type=fuel_type,
                        transmission=transmission,
                        body_type=post.get('body_type', 'Sedan') or 'Sedan',
                        ownership=post.get('ownership', '1st Owner') or '1st Owner',
                        city=city,
                        rto=rto,
                        registration_state=registration_state,
                        sell_timeline=sell_timeline,
                        contact_number=contact_number,
                        description=description,
                        status='PENDING',
                        submit_via_sell_form=True,
                        sell_inquiry_seen=False,
                    )
                    if request.user.is_authenticated:
                        car.seller = request.user
                    car.save()

                    for i, img in enumerate(images):
                        CarImage.objects.create(car=car, image=img, is_primary=(i == 0))

                    if is_ajax:
                        return JsonResponse({'success': True, 'message': 'Your car has been submitted for review!', 'redirect': '/'})
                    messages.success(request, 'Your car has been submitted for review!')
                    return redirect('home')
                except (Brand.DoesNotExist, CarModel.DoesNotExist):
                    err_msg = 'Invalid brand or model selected.'
                    if is_ajax:
                        return JsonResponse({'success': False, 'message': err_msg}, status=400)
                    messages.error(request, err_msg)
                except (ValueError, TypeError):
                    err_msg = 'Invalid data. Please check year and price.'
                    if is_ajax:
                        return JsonResponse({'success': False, 'message': err_msg}, status=400)
                    messages.error(request, err_msg)

    brands = Brand.objects.all()
    context = {
        'brands': brands,
        'min_images': MIN_IMAGES,
        'max_images': MAX_IMAGES,
    }
    return render(request, 'cars/sell_car.html', context)


def get_models(request):
    brand_id = request.GET.get('brand_id')
    models_qs = CarModel.objects.filter(brand_id=brand_id).values('id', 'name')
    return JsonResponse(list(models_qs), safe=False)


def get_variants(request):
    from .variant_data import get_variants_for_model
    model_id = request.GET.get('model_id')
    if not model_id:
        return JsonResponse([], safe=False)
    try:
        car_model = CarModel.objects.select_related('brand').get(pk=model_id)
        variants = get_variants_for_model(car_model.brand.name, car_model.name)
        return JsonResponse(variants, safe=False)
    except CarModel.DoesNotExist:
        return JsonResponse([], safe=False)


def signup_view(request):
    if request.user.is_authenticated:
        next_url = _safe_next_url(request)
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'redirect': next_url})
        return redirect(next_url)
    if request.method == 'POST':
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            next_url = _safe_next_url(request)
            if is_ajax:
                return JsonResponse({'success': True, 'message': 'Account created successfully!', 'redirect': next_url})
            messages.success(request, 'Account created successfully!')
            return redirect(next_url)
        else:
            if is_ajax:
                return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    else:
        form = SignUpForm()
    return render(request, 'registration/signup.html', {'form': form})


def _safe_next_url(request, default='/'):
    next_url = request.GET.get('next', default)
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return next_url
    return default


def login_view(request):
    if request.user.is_authenticated:
        next_url = _safe_next_url(request)
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'redirect': next_url})
        return redirect(next_url)
    if request.method == 'POST':
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            next_url = _safe_next_url(request)
            messages.success(request, 'Logged in successfully!')
            if is_ajax:
                return JsonResponse({'success': True, 'message': 'Logged in successfully!', 'redirect': next_url})
            return redirect(next_url)
        else:
            if is_ajax:
                return JsonResponse({'success': False, 'message': 'Invalid username or password.'}, status=400)
            messages.error(request, 'Invalid username or password.')
    return render(request, 'registration/login.html')


def logout_view(request):
    logout(request)
    return redirect('home')


@never_cache
@login_required
def toggle_wishlist(request, pk):
    car = get_object_or_404(Car, pk=pk)
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
    # AJAX must use POST so browsers cannot serve a cached GET response (breaks undo).
    if is_ajax and request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    wishlist_item = Wishlist.objects.filter(car=car, user=request.user).first()
    if wishlist_item:
        wishlist_item.delete()
        added = False
    else:
        Wishlist.objects.create(car=car, user=request.user)
        added = True

    if is_ajax:
        wishlist_count = car.wishlisted_by.count()
        resp = JsonResponse({'added': added, 'wishlist_count': wishlist_count})
        resp['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
        resp['Pragma'] = 'no-cache'
        return resp
    next_url = _safe_next_url(request, default=reverse('car_detail', args=[pk]))
    return redirect(next_url)


@login_required
def wishlist_view(request):
    wishlist_items = (
        Wishlist.objects.filter(user=request.user)
        .select_related('car', 'car__brand', 'car__model')
        .prefetch_related(_WISHLIST_CAR_IMAGES)
    )
    car_ids = list(wishlist_items.values_list('car_id', flat=True))
    count_map = dict(
        Car.objects.filter(pk__in=car_ids)
        .annotate(wishlist_entry_count=Count('wishlisted_by'))
        .values_list('pk', 'wishlist_entry_count')
    )
    cars = []
    for item in wishlist_items:
        c = item.car
        c.wishlist_entry_count = count_map.get(c.pk, 0)
        cars.append(c)
    return render(request, 'cars/wishlist.html', {'cars': cars})


def _sell_dashboard_context(request, skip_counts=False):
    """Shared by full page and AJAX partials. Counts use one aggregate query when needed."""
    bucket = request.GET.get('bucket', 'pending')
    if bucket not in ('pending', 'approved', 'rejected'):
        bucket = 'pending'

    base = Car.objects.filter(seller=request.user, submit_via_sell_form=True)
    if not skip_counts:
        stats = base.aggregate(
            cp=Count('pk', filter=Q(status='PENDING')),
            ca=Count('pk', filter=Q(status__in=('APPROVED', 'ON_HOLD', 'SOLD'))),
            cr=Count('pk', filter=Q(status='REJECTED')),
        )
        count_pending = stats['cp']
        count_approved = stats['ca']
        count_rejected = stats['cr']
    else:
        count_pending = count_approved = count_rejected = 0

    qs = base
    if bucket == 'pending':
        qs = qs.filter(status='PENDING')
    elif bucket == 'rejected':
        qs = qs.filter(status='REJECTED')
    else:
        qs = qs.filter(status__in=('APPROVED', 'ON_HOLD', 'SOLD'))

    cars = _cars_with_related(qs.order_by('-created_at'))

    return {
        'bucket': bucket,
        'cars': cars,
        'count_pending': count_pending,
        'count_approved': count_approved,
        'count_rejected': count_rejected,
    }


@login_required
def sell_requests_dashboard(request):
    """Cars submitted via /sell/ — Pending / Approved / Rejected tabs; AJAX swaps list only (no full reload)."""
    is_xhr = request.headers.get('x-requested-with') == 'XMLHttpRequest'
    if is_xhr and request.GET.get('partial') == 'list':
        ctx = _sell_dashboard_context(request, skip_counts=True)
        return render(request, 'cars/_sell_dashboard_list_inner.html', ctx)
    ctx = _sell_dashboard_context(request)
    if is_xhr:
        return render(request, 'cars/_sell_dashboard_fragment.html', ctx)
    return render(request, 'cars/sell_requests_dashboard.html', ctx)
