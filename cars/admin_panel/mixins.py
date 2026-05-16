"""AJAX partial rendering helpers for the admin panel."""

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect


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
