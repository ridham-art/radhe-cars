"""
Setup production: update Site domain, create admin user from env.
Run during deploy. Set SUPERUSER_EMAIL and SUPERUSER_PASSWORD in Render Environment.
"""
import os
from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Setup production: Site domain + create admin from env'

    def handle(self, *args, **options):
        # Update Site for allauth (required for OAuth callbacks)
        site = Site.objects.get(id=1)
        site.domain = os.environ.get('SITE_DOMAIN', 'radheauto.com')
        site.name = 'Radhe Auto'
        site.save()
        self.stdout.write(self.style.SUCCESS(f'Site updated: {site.domain}'))

        # Create superuser from env if set
        username = os.environ.get('SUPERUSER_USERNAME', 'admin').strip()
        email = os.environ.get('SUPERUSER_EMAIL', f'{username}@radheauto.com').strip()
        password = os.environ.get('SUPERUSER_PASSWORD', '').strip()
        if username and password:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={'email': email, 'is_staff': True, 'is_superuser': True}
            )
            if created:
                user.set_password(password)
                user.save()
                self.stdout.write(self.style.SUCCESS(f'Superuser created: {username}'))
            else:
                user.set_password(password)
                user.is_staff = True
                user.is_superuser = True
                user.save()
                self.stdout.write(self.style.SUCCESS(f'Superuser {username} password updated'))
        else:
            self.stdout.write('Set SUPERUSER_USERNAME, SUPERUSER_EMAIL, SUPERUSER_PASSWORD in Environment.')
