import json
import logging
import os
import re
import tempfile

from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.conf import settings
from django.contrib.auth.views import LoginView, LogoutView
from django.http import HttpResponseRedirect
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q, Count
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import (
    TemplateView,
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
    FormView,
)

from cars.models import Brand, Car, CarModel, CarImage, Inquiry, Wishlist
from cars.admin_panel.forms import (
    BrandBulkForm,
    BrandForm,
    CarModelBulkForm,
    CarModelForm,
    CarStaffForm,
    CSVUploadForm,
    StaffAuthenticationForm,
)
from cars.admin_panel import csv_io

logger = logging.getLogger('cars.admin_panel.auth')


def _parse_bulk_list(text):
    """Split on commas and/or newlines; strip; preserve order; dedupe exact strings."""
    if not text:
        return []
    text = text.replace('\r', '')
    parts = re.split(r'[,\n]+', text)
    out = []
    seen = set()
    for p in parts:
        n = p.strip()
        if not n or n in seen:
            continue
        seen.add(n)
        out.append(n)
    return out

# Force username/password auth to ModelBackend (avoids ambiguity with allauth backends).
_MODEL_BACKEND = 'django.contrib.auth.backends.ModelBackend'


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    login_url = '/admin-panel/login/'

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_staff


class AdminPanelContextMixin:
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['unread_inquiry_count'] = Inquiry.objects.filter(is_read=False).count()
        ctx['sell_inquiry_unread_count'] = Car.objects.filter(
            submit_via_sell_form=True, sell_inquiry_seen=False
        ).count()
        return ctx


class StaffLoginView(LoginView):
    template_name = 'admin_panel/login.html'
    authentication_form = StaffAuthenticationForm
    redirect_authenticated_user = True

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Show exact dev credentials only when DEBUG (hidden in production)
        ctx['show_staff_demo_login'] = settings.DEBUG
        return ctx

    def form_valid(self, form):
        """
        AuthenticationForm already ran authenticate(); establish session with a
        single explicit backend so the session stores BACKEND_SESSION_KEY correctly.
        """
        login(self.request, form.get_user(), backend=_MODEL_BACKEND)
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form):
        self._log_staff_login_failure(form)
        return super().form_invalid(form)

    def _log_staff_login_failure(self, form):
        """Diagnose failed staff login (does not log passwords)."""
        username = (form.data.get('username') or '').strip()
        if not username:
            logger.warning('admin_panel.login: empty username')
            return
        User = get_user_model()
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            logger.warning('admin_panel.login: user not found username=%r', username)
            return
        if not user.is_active:
            logger.warning('admin_panel.login: user inactive username=%r', username)
            return
        pwd = form.data.get('password') or ''
        if not user.check_password(pwd):
            logger.warning(
                'admin_panel.login: password incorrect for username=%r (run create_staff_user if needed)',
                username,
            )
            return
        if not user.is_staff:
            logger.warning('admin_panel.login: user is not staff username=%r', username)
            return
        logger.warning(
            'admin_panel.login: form invalid for username=%r errors=%s',
            username,
            form.errors,
        )

    def get_success_url(self):
        n = self.request.GET.get('next')
        if n:
            return n
        return reverse('admin_panel:dashboard')


class StaffLogoutView(LogoutView):
    http_method_names = ['get', 'post', 'options']
    next_page = '/admin-panel/login/'


class DashboardView(StaffRequiredMixin, AdminPanelContextMixin, TemplateView):
    template_name = 'admin_panel/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        User = get_user_model()
        customers = User.objects.filter(is_staff=False)
        wish_qs = Wishlist.objects.filter(user__isnull=False)
        ctx.update(
            {
                'total_cars': Car.objects.count(),
                'active_cars': Car.objects.exclude(status='SOLD').count(),
                'sold_cars': Car.objects.filter(status='SOLD').count(),
                'total_inquiries': Inquiry.objects.count(),
                'unread_inquiries': Inquiry.objects.filter(is_read=False).count(),
                'total_customers': customers.count(),
                'total_wishlist_saves': wish_qs.count(),
                'customers_with_wishlist': wish_qs.values('user_id').distinct().count(),
            }
        )
        return ctx


class CustomerUserListView(StaffRequiredMixin, AdminPanelContextMixin, ListView):
    """Non-staff accounts (customers who signed up on the site)."""

    template_name = 'admin_panel/user_list.html'
    context_object_name = 'customers'
    paginate_by = 25

    def get_queryset(self):
        User = get_user_model()
        qs = User.objects.filter(is_staff=False).order_by('-date_joined')
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(Q(email__icontains=q) | Q(username__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['search_q'] = self.request.GET.get('q', '')
        return ctx


class WishlistActivityListView(StaffRequiredMixin, AdminPanelContextMixin, ListView):
    """Wishlist rows for logged-in users only."""

    template_name = 'admin_panel/wishlist_list.html'
    context_object_name = 'wishlists'
    paginate_by = 25

    def get_queryset(self):
        qs = (
            Wishlist.objects.filter(user__isnull=False)
            .select_related('user', 'car', 'car__brand', 'car__model')
            .order_by('-created_at')
        )
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(user__email__icontains=q)
                | Q(car__title__icontains=q)
                | Q(user__username__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['search_q'] = self.request.GET.get('q', '')
        return ctx


class CarListView(StaffRequiredMixin, AdminPanelContextMixin, ListView):
    model = Car
    template_name = 'admin_panel/car_list.html'
    context_object_name = 'cars'
    paginate_by = 25

    def get_queryset(self):
        qs = (
            Car.objects.select_related('brand', 'model')
            .prefetch_related('images')
            .exclude(submit_via_sell_form=True)
        )
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(model__name__icontains=q))
        brand = self.request.GET.get('brand')
        if brand:
            qs = qs.filter(brand_id=brand)
        fuel = self.request.GET.get('fuel')
        if fuel:
            qs = qs.filter(fuel_type=fuel)
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)
        return qs.order_by('-created_at')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['brands'] = Brand.objects.all()
        ctx['fuel_types'] = Car.FUEL_CHOICES
        ctx['statuses'] = Car.STATUS_CHOICES
        ctx['search_q'] = self.request.GET.get('q', '')
        _b = self.request.GET.get('brand')
        ctx['filter_brand'] = int(_b) if _b and str(_b).isdigit() else None
        ctx['filter_fuel'] = self.request.GET.get('fuel', '')
        ctx['filter_status'] = self.request.GET.get('status', '')
        return ctx


class CarCreateView(StaffRequiredMixin, AdminPanelContextMixin, CreateView):
    model = Car
    form_class = CarStaffForm
    template_name = 'admin_panel/car_form.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['cancel_url'] = reverse_lazy('admin_panel:car_list')
        ctx['return_to_sell'] = False
        return ctx

    def get_success_url(self):
        return reverse_lazy('admin_panel:car_list')

    def form_valid(self, form):
        messages.success(self.request, 'Car created successfully.')
        response = super().form_valid(form)
        self._save_images(self.object)
        return response

    def _save_images(self, car):
        files = self.request.FILES.getlist('images')
        has_primary = car.images.filter(is_primary=True).exists()
        first_new = True
        for f in files:
            if not f:
                continue
            CarImage.objects.create(
                car=car,
                image=f,
                is_primary=not has_primary and first_new,
            )
            first_new = False


class CarUpdateView(StaffRequiredMixin, AdminPanelContextMixin, UpdateView):
    model = Car
    form_class = CarStaffForm
    template_name = 'admin_panel/car_form.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['return_to_sell'] = self.request.GET.get('return') == 'sell'
        ctx['cancel_url'] = (
            reverse_lazy('admin_panel:sell_car_inquiry_list')
            if ctx['return_to_sell']
            else reverse_lazy('admin_panel:car_list')
        )
        return ctx

    def get_success_url(self):
        if self.request.POST.get('return') == 'sell':
            return reverse_lazy('admin_panel:sell_car_inquiry_list')
        return reverse_lazy('admin_panel:car_list')

    def form_valid(self, form):
        messages.success(self.request, 'Car updated successfully.')
        response = super().form_valid(form)
        self._save_images(self.object)
        return response

    def _save_images(self, car):
        files = self.request.FILES.getlist('images')
        if not files:
            return
        has_primary = car.images.filter(is_primary=True).exists()
        first_new = True
        for f in files:
            if not f:
                continue
            CarImage.objects.create(
                car=car,
                image=f,
                is_primary=not has_primary and first_new,
            )
            first_new = False


class CarDeleteView(StaffRequiredMixin, AdminPanelContextMixin, DeleteView):
    model = Car
    template_name = 'admin_panel/car_confirm_delete.html'
    success_url = reverse_lazy('admin_panel:car_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['return_to_sell'] = self.request.GET.get('return') == 'sell'
        ctx['cancel_url'] = (
            reverse_lazy('admin_panel:sell_car_inquiry_list')
            if ctx['return_to_sell']
            else reverse_lazy('admin_panel:car_list')
        )
        return ctx

    def get_success_url(self):
        if self.request.POST.get('return') == 'sell':
            return reverse_lazy('admin_panel:sell_car_inquiry_list')
        return reverse_lazy('admin_panel:car_list')

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Car deleted.')
        return super().delete(request, *args, **kwargs)


class CarBulkDeleteView(StaffRequiredMixin, View):
    def post(self, request):
        ids = request.POST.getlist('ids')
        if not ids:
            messages.warning(request, 'No cars selected.')
            return redirect('admin_panel:car_list')
        Car.objects.filter(pk__in=ids).exclude(submit_via_sell_form=True).delete()
        messages.success(request, f'Deleted {len(ids)} car(s).')
        return redirect('admin_panel:car_list')


class SellCarInquiryListView(StaffRequiredMixin, AdminPanelContextMixin, ListView):
    """Cars submitted via the public Sell Car form (pending review)."""

    model = Car
    template_name = 'admin_panel/sell_car_inquiry_list.html'
    context_object_name = 'cars'
    paginate_by = 25

    def dispatch(self, request, *args, **kwargs):
        if request.method == 'GET':
            Car.objects.filter(submit_via_sell_form=True, sell_inquiry_seen=False).update(
                sell_inquiry_seen=True
            )
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        qs = Car.objects.filter(submit_via_sell_form=True).select_related(
            'brand', 'model', 'seller'
        ).prefetch_related('images')
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(contact_number__icontains=q))
        st = self.request.GET.get('status', '').strip()
        if st:
            qs = qs.filter(status=st)
        return qs.order_by('-created_at')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['search_q'] = self.request.GET.get('q', '')
        ctx['filter_status'] = self.request.GET.get('status', '')
        ctx['statuses'] = Car.STATUS_CHOICES
        return ctx


class SellCarInquiryBulkDeleteView(StaffRequiredMixin, View):
    def post(self, request):
        ids = request.POST.getlist('ids')
        if not ids:
            messages.warning(request, 'No listings selected.')
            return redirect('admin_panel:sell_car_inquiry_list')
        n, _ = Car.objects.filter(pk__in=ids, submit_via_sell_form=True).delete()
        messages.success(request, f'Deleted {n} listing(s).')
        return redirect('admin_panel:sell_car_inquiry_list')


class SellCarInquiryApproveView(StaffRequiredMixin, View):
    """Publish listing on the website (same as main car list visibility)."""

    def post(self, request, pk):
        car = get_object_or_404(Car, pk=pk, submit_via_sell_form=True)
        car.status = 'APPROVED'
        car.save()
        messages.success(request, f'Approved: {car.title} is now visible on the site.')
        return redirect('admin_panel:sell_car_inquiry_list')


class SellCarInquiryToggleFeaturedView(StaffRequiredMixin, View):
    def post(self, request, pk):
        car = get_object_or_404(Car, pk=pk, submit_via_sell_form=True)
        car.is_featured = not car.is_featured
        car.save()
        state = 'featured' if car.is_featured else 'removed from featured'
        messages.success(request, f'{car.title}: {state}.')
        return redirect('admin_panel:sell_car_inquiry_list')


class BrandListView(StaffRequiredMixin, AdminPanelContextMixin, ListView):
    model = Brand
    template_name = 'admin_panel/brand_list.html'
    context_object_name = 'brands'
    queryset = Brand.objects.annotate(car_count=Count('models__car', distinct=True)).order_by('name')


class BrandCreateView(StaffRequiredMixin, AdminPanelContextMixin, CreateView):
    model = Brand
    form_class = BrandForm
    template_name = 'admin_panel/brand_form.html'
    success_url = reverse_lazy('admin_panel:brand_list')

    def form_valid(self, form):
        messages.success(self.request, 'Brand created.')
        return super().form_valid(form)


class BrandUpdateView(StaffRequiredMixin, AdminPanelContextMixin, UpdateView):
    model = Brand
    form_class = BrandForm
    template_name = 'admin_panel/brand_form.html'
    success_url = reverse_lazy('admin_panel:brand_list')

    def form_valid(self, form):
        messages.success(self.request, 'Brand updated.')
        return super().form_valid(form)


class BrandDeleteView(StaffRequiredMixin, AdminPanelContextMixin, DeleteView):
    model = Brand
    template_name = 'admin_panel/brand_confirm_delete.html'
    success_url = reverse_lazy('admin_panel:brand_list')

    def delete(self, request, *args, **kwargs):
        if Car.objects.filter(brand=self.get_object()).exists():
            messages.error(request, 'Cannot delete brand: cars still reference it.')
            return redirect('admin_panel:brand_list')
        messages.success(request, 'Brand deleted.')
        return super().delete(request, *args, **kwargs)


class BrandBulkAddView(StaffRequiredMixin, AdminPanelContextMixin, FormView):
    template_name = 'admin_panel/brand_bulk_add.html'
    form_class = BrandBulkForm
    success_url = reverse_lazy('admin_panel:brand_list')

    def form_valid(self, form):
        text = form.cleaned_data['brands']
        names = _parse_bulk_list(text)
        created = 0
        skipped_dup = 0
        for n in names:
            if Brand.objects.filter(name=n).exists():
                skipped_dup += 1
                continue
            Brand.objects.create(name=n)
            created += 1
        if created:
            messages.success(self.request, f'Added {created} brand(s).')
        else:
            messages.warning(self.request, 'No new brands were added.')
        if skipped_dup:
            messages.info(self.request, f'Skipped {skipped_dup} name(s) (already exists).')
        return super().form_valid(form)


class CarModelBulkAddView(StaffRequiredMixin, AdminPanelContextMixin, FormView):
    template_name = 'admin_panel/carmodel_bulk_add.html'
    form_class = CarModelBulkForm
    success_url = reverse_lazy('admin_panel:carmodel_list')

    def form_valid(self, form):
        brand = form.cleaned_data['brand']
        text = form.cleaned_data['models']
        names = []
        seen = set()
        for n in _parse_bulk_list(text):
            key = (brand.pk, n.lower())
            if key in seen:
                continue
            seen.add(key)
            names.append(n)
        created = 0
        skipped_dup = 0
        for n in names:
            if CarModel.objects.filter(brand=brand, name=n).exists():
                skipped_dup += 1
                continue
            CarModel.objects.create(brand=brand, name=n)
            created += 1
        if created:
            messages.success(self.request, f'Added {created} model(s) for {brand.name}.')
        else:
            messages.warning(self.request, 'No new models were added.')
        if skipped_dup:
            messages.info(self.request, f'Skipped {skipped_dup} duplicate(s) for this brand.')
        return super().form_valid(form)


class BrandDeleteAllModelsView(StaffRequiredMixin, View):
    """Delete all CarModel rows for a brand that are not referenced by any Car."""

    template_name = 'admin_panel/brand_delete_all_models_confirm.html'

    def get(self, request, pk):
        brand = get_object_or_404(Brand, pk=pk)
        models_qs = CarModel.objects.filter(brand=brand).order_by('name')
        in_use_ids = set(Car.objects.filter(model__brand=brand).values_list('model_id', flat=True))
        deletable = []
        blocked = []
        for m in models_qs:
            if m.pk in in_use_ids:
                blocked.append(m)
            else:
                deletable.append(m)
        ctx = {
            'unread_inquiry_count': Inquiry.objects.filter(is_read=False).count(),
            'brand': brand,
            'deletable': deletable,
            'blocked': blocked,
        }
        return render(request, self.template_name, ctx)

    def post(self, request, pk):
        brand = get_object_or_404(Brand, pk=pk)
        in_use_ids = set(Car.objects.filter(model__brand=brand).values_list('model_id', flat=True))
        qs = CarModel.objects.filter(brand=brand).exclude(pk__in=in_use_ids)
        n = qs.count()
        qs.delete()
        if n:
            messages.success(request, f'Deleted {n} model(s) for {brand.name}.')
        else:
            messages.info(request, 'No deletable models (none were unused by cars).')
        if in_use_ids:
            messages.warning(
                request,
                f'{len(in_use_ids)} model(s) are still used by cars and were not deleted.',
            )
        return redirect('admin_panel:carmodel_list')


class CarModelListView(StaffRequiredMixin, AdminPanelContextMixin, ListView):
    model = CarModel
    template_name = 'admin_panel/carmodel_list.html'
    context_object_name = 'carmodels'

    def get_queryset(self):
        qs = CarModel.objects.select_related('brand')
        bid = self.request.GET.get('brand')
        if bid:
            qs = qs.filter(brand_id=bid)
        return qs.order_by('brand__name', 'name')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['brands'] = Brand.objects.all()
        _b = self.request.GET.get('brand')
        ctx['filter_brand'] = int(_b) if _b and str(_b).isdigit() else None
        return ctx


class CarModelCreateView(StaffRequiredMixin, AdminPanelContextMixin, CreateView):
    model = CarModel
    form_class = CarModelForm
    template_name = 'admin_panel/carmodel_form.html'
    success_url = reverse_lazy('admin_panel:carmodel_list')

    def form_valid(self, form):
        messages.success(self.request, 'Model created.')
        return super().form_valid(form)


class CarModelUpdateView(StaffRequiredMixin, AdminPanelContextMixin, UpdateView):
    model = CarModel
    form_class = CarModelForm
    template_name = 'admin_panel/carmodel_form.html'
    success_url = reverse_lazy('admin_panel:carmodel_list')

    def form_valid(self, form):
        messages.success(self.request, 'Model updated.')
        return super().form_valid(form)


class CarModelDeleteView(StaffRequiredMixin, AdminPanelContextMixin, DeleteView):
    model = CarModel
    template_name = 'admin_panel/carmodel_confirm_delete.html'
    success_url = reverse_lazy('admin_panel:carmodel_list')

    def delete(self, request, *args, **kwargs):
        if Car.objects.filter(model=self.get_object()).exists():
            messages.error(request, 'Cannot delete model: cars still reference it.')
            return redirect('admin_panel:carmodel_list')
        messages.success(request, 'Model deleted.')
        return super().delete(request, *args, **kwargs)


class InquiryListView(StaffRequiredMixin, AdminPanelContextMixin, ListView):
    model = Inquiry
    template_name = 'admin_panel/inquiry_list.html'
    context_object_name = 'inquiries'
    paginate_by = 30

    def get_queryset(self):
        return Inquiry.objects.order_by('is_read', '-created_at')


class InquiryDetailView(StaffRequiredMixin, AdminPanelContextMixin, DetailView):
    model = Inquiry
    template_name = 'admin_panel/inquiry_detail.html'
    context_object_name = 'inquiry'

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        obj = self.object
        if not obj.is_read:
            obj.is_read = True
            obj.save(update_fields=['is_read'])
        return response


class InquiryMarkReadView(StaffRequiredMixin, View):
    def post(self, request, pk):
        Inquiry.objects.filter(pk=pk).update(is_read=True)
        messages.success(request, 'Marked as read.')
        return redirect('admin_panel:inquiry_list')


class InquiryMarkAllReadView(StaffRequiredMixin, View):
    def post(self, request):
        n = Inquiry.objects.filter(is_read=False).update(is_read=True)
        messages.success(request, f'Marked {n} inquiry(ies) as read.')
        return redirect('admin_panel:inquiry_list')


class InquiryDeleteView(StaffRequiredMixin, View):
    def post(self, request, pk):
        Inquiry.objects.filter(pk=pk).delete()
        messages.success(request, 'Inquiry deleted.')
        return redirect('admin_panel:inquiry_list')


class UnreadInquiryCountJsonView(StaffRequiredMixin, View):
    def get(self, request):
        inquiries = Inquiry.objects.filter(is_read=False).count()
        sell = Car.objects.filter(submit_via_sell_form=True, sell_inquiry_seen=False).count()
        return JsonResponse(
            {
                'count': inquiries,
                'inquiries': inquiries,
                'sell_inquiries': sell,
            }
        )


class BrandModelsJsonView(StaffRequiredMixin, View):
    def get(self, request, pk):
        models = CarModel.objects.filter(brand_id=pk).order_by('name')
        return JsonResponse({'models': [{'id': m.id, 'name': m.name} for m in models]})


class CSVImportView(StaffRequiredMixin, AdminPanelContextMixin, FormView):
    template_name = 'admin_panel/csv_import.html'
    form_class = CSVUploadForm

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['csv_skip_log'] = self.request.session.pop('csv_skip_log', None)
        return ctx

    def form_valid(self, form):
        f = form.cleaned_data['file']
        replace_all = form.cleaned_data.get('replace_all')
        try:
            rows = csv_io.parse_uploaded_csv(f)
        except ValueError as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)
        ok, errs = csv_io.validate_and_preview_rows(rows)
        fd, path = tempfile.mkstemp(suffix='.json')
        with os.fdopen(fd, 'w', encoding='utf-8') as out:
            json.dump(
                {
                    'ok': ok,
                    'errors': errs,
                    'replace_all': bool(replace_all),
                },
                out,
            )
        self.request.session['admin_csv_path'] = path
        if errs and not ok:
            messages.error(self.request, 'CSV has errors; fix the file and try again.')
        return redirect('admin_panel:csv_preview')


class CSVPreviewView(StaffRequiredMixin, AdminPanelContextMixin, TemplateView):
    template_name = 'admin_panel/csv_preview.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        path = self.request.session.get('admin_csv_path')
        if not path or not os.path.isfile(path):
            ctx['missing'] = True
            return ctx
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        ctx['preview_ok'] = data.get('ok', [])
        ctx['preview_errors'] = data.get('errors', [])
        ctx['replace_all'] = data.get('replace_all', False)
        ctx['can_confirm'] = bool(data.get('ok'))
        return ctx


class CSVConfirmView(StaffRequiredMixin, View):
    def post(self, request):
        path = request.session.get('admin_csv_path')
        if not path or not os.path.isfile(path):
            messages.error(request, 'No import session; upload again.')
            return redirect('admin_panel:csv_import')
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        ok = data.get('ok', [])
        replace_all = data.get('replace_all', False)
        confirm = request.POST.get('confirm_replace')
        if replace_all and confirm != 'REPLACE':
            messages.error(request, 'Type REPLACE to confirm deleting all cars.')
            return redirect('admin_panel:csv_preview')
        try:
            result = csv_io.apply_import(ok, replace_all=replace_all)
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass
            request.session.pop('admin_csv_path', None)
        messages.success(
            request,
            f"Import finished: {result['created']} created, {result['updated']} updated.",
        )
        if result['skipped']:
            messages.warning(request, f"{len(result['skipped'])} row(s) skipped — see logs.")
            request.session['csv_skip_log'] = result['skipped'][:200]
        return redirect('admin_panel:csv_import')


class CSVExportView(StaffRequiredMixin, View):
    def get(self, request):
        data = csv_io.export_cars_csv()
        resp = HttpResponse(data, content_type='text/csv; charset=utf-8')
        resp['Content-Disposition'] = 'attachment; filename="cars_export.csv"'
        return resp
