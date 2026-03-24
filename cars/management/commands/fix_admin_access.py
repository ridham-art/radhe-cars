"""
Ensure a user can log into Django admin (staff + superuser + new password).

Usage (point DATABASE_URL at Supabase):
  python manage.py fix_admin_access dipak 3781
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = 'Set is_staff, is_superuser, and password for admin login'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str)
        parser.add_argument('password', type=str)

    def handle(self, *args, **options):
        User = get_user_model()
        username = options['username']
        password = options['password']
        try:
            u = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stderr.write(self.style.ERROR(f'User "{username}" does not exist.'))
            return
        u.is_staff = True
        u.is_superuser = True
        u.set_password(password)
        u.save()
        self.stdout.write(
            self.style.SUCCESS(f'OK: "{username}" can now log in at /admin/ with the new password.')
        )
