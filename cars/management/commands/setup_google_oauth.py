"""
Run once to add Google OAuth credentials to database.
Requires GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET (env or settings).
Optional: SITE_DOMAIN (default www.radheauto.com for live).

Usage:
  python manage.py setup_google_oauth
"""
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp


class Command(BaseCommand):
    help = 'Add Google OAuth app with credentials from settings'

    def handle(self, *args, **options):
        client_id = getattr(settings, 'GOOGLE_CLIENT_ID', '') or os.environ.get('GOOGLE_CLIENT_ID', '')
        client_secret = getattr(settings, 'GOOGLE_CLIENT_SECRET', '') or os.environ.get('GOOGLE_CLIENT_SECRET', '')
        if not client_id or not client_secret:
            self.stderr.write('Error: GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set')
            return

        # Live domain (no scheme). For local dev use SITE_DOMAIN=127.0.0.1:8000
        domain = os.environ.get('SITE_DOMAIN', 'www.radheauto.com')
        site_id = settings.SITE_ID
        # domain is UNIQUE: remove stray rows using the same domain with a different pk
        Site.objects.filter(domain=domain).exclude(pk=site_id).delete()
        site, site_created = Site.objects.get_or_create(
            pk=site_id,
            defaults={'domain': domain, 'name': 'Radhe Auto'},
        )
        if not site_created:
            site.domain = domain
            site.name = 'Radhe Auto'
            site.save()
        else:
            self.stdout.write(self.style.WARNING(f'Created django.contrib.sites Site id={site_id} ({domain}).'))
        app, created = SocialApp.objects.update_or_create(
            provider='google',
            defaults={
                'name': 'Google',
                'client_id': client_id,
                'secret': client_secret,
                'key': '',
            }
        )
        if site not in app.sites.all():
            app.sites.add(site)
        self.stdout.write(self.style.SUCCESS('Google OAuth configured successfully.'))
