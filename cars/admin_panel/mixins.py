"""AJAX partial rendering helpers for the admin panel."""

import json

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect
from django.template.loader import render_to_string


class AdminListPartialMixin:
    """Return a list partial when ?partial=list and X-Requested-With: XMLHttpRequest."""

    partial_template_name = None

    def _is_ajax_partial(self, name):
        return (
            self.request.headers.get('x-requested-with') == 'XMLHttpRequest'
            and self.request.GET.get('partial') == name
        )

    def render_to_response(self, context, **response_kwargs):
        if self._is_ajax_partial('list') and self.partial_template_name:
            from django.shortcuts import render

            return render(self.request, self.partial_template_name, context)
        return super().render_to_response(context, **response_kwargs)


def admin_ajax_response(request, *, redirect_to, message=None, level='success', reload_url=None):
    """JSON for XHR POST actions; otherwise redirect with messages."""
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        payload = {'ok': level != 'error'}
        if message:
            payload['message'] = message
            payload['level'] = level
        if reload_url:
            payload['reload'] = reload_url
        elif redirect_to:
            payload['redirect'] = redirect_to
        return JsonResponse(payload)
    if message:
        if level == 'success':
            messages.success(request, message)
        elif level == 'error':
            messages.error(request, message)
        elif level == 'warning':
            messages.warning(request, message)
        else:
            messages.info(request, message)
    return redirect(redirect_to)


class CarFormAjaxMixin:
    """XHR save / validation for car add/edit (AutoVault preview templates)."""

    car_form_partial_template = 'admin_panel/partials/car_form_body_partial.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        obj = ctx.get('object') or getattr(self, 'object', None)
        model_id = None
        variant = ''
        if obj and getattr(obj, 'pk', None):
            model_id = obj.model_id
            variant = obj.variant or ''
        ctx['cf_config_json'] = json.dumps({'modelId': model_id, 'variant': variant})
        return ctx

    def _is_car_form_xhr(self):
        return self.request.headers.get('x-requested-with') == 'XMLHttpRequest'

    def _car_form_success_message(self):
        if getattr(self, 'object', None) and getattr(self.object, 'pk', None):
            return 'Car updated successfully.'
        return 'Car created successfully.'

    def form_valid(self, form):
        if not self._is_car_form_xhr():
            return super().form_valid(form)
        messages.success(self.request, self._car_form_success_message())
        self.object = form.save()
        self._save_images(self.object)
        return admin_ajax_response(
            self.request,
            redirect_to=str(self.get_success_url()),
            message=self._car_form_success_message(),
        )

    def form_invalid(self, form):
        if not self._is_car_form_xhr():
            return super().form_invalid(form)
        ctx = self.get_context_data(form=form)
        partial_html = render_to_string(
            self.car_form_partial_template,
            ctx,
            request=self.request,
        )
        return JsonResponse(
            {
                'ok': False,
                'level': 'error',
                'message': 'Please correct the errors below.',
                'partialHtml': partial_html,
            }
        )
