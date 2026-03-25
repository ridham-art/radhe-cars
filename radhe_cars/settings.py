from pathlib import Path
import os
import socket
import dj_database_url
from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured


def _prefer_ipv4_for_supabase(db):
    """
    Supabase DNS can return IPv6 first; Render build/runtime often has no IPv6 route
    ('Network is unreachable'). Prefer IPv4 via libpq hostaddr when possible.
    Skip pooler hosts — they are IPv4-proxied; hostaddr can break routing/TLS with PgBouncer.
    """
    host = db.get('HOST')
    if not host or 'pooler.' in host:
        return
    # Direct: *.supabase.co — Pooler: *.pooler.supabase.com (handled above)
    if 'supabase.co' not in host and 'supabase.com' not in host:
        return
    port = int(db.get('PORT') or 5432)
    try:
        infos = socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM)
        if infos:
            db.setdefault('OPTIONS', {})['hostaddr'] = infos[0][4][0]
    except OSError:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
# Load project root .env into os.environ (file is optional; gitignored)
load_dotenv(BASE_DIR / '.env')

DEBUG = os.environ.get('DEBUG', 'True').lower() in ('true', '1', 'yes')

SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-radhe-cars-dev-key-change-in-production')
if not DEBUG:
    if not SECRET_KEY or SECRET_KEY.startswith('django-insecure-') or len(SECRET_KEY) < 50:
        raise ImproperlyConfigured(
            'Production requires SECRET_KEY: a long random value (50+ chars, 5+ unique chars). '
            'Generate: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"'
        )
    if len(set(SECRET_KEY)) < 5:
        raise ImproperlyConfigured(
            'Production SECRET_KEY must use at least 5 different characters (use get_random_secret_key()).'
        )

_allowed_raw = os.environ.get('ALLOWED_HOSTS', '').strip()
if _allowed_raw:
    ALLOWED_HOSTS = [h.strip() for h in _allowed_raw.split(',') if h.strip()]
elif not DEBUG:
    raise ImproperlyConfigured(
        'Set ALLOWED_HOSTS in the environment (comma-separated), e.g. radheauto.com,www.radheauto.com'
    )
else:
    ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'cars',
]

SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'password1*', 'password2*']
ACCOUNT_EMAIL_VERIFICATION = 'optional'
ACCOUNT_PREVENT_ENUMERATION = False
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_EMAIL_REQUIRED = True
SOCIALACCOUNT_QUERY_EMAIL = True

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
    }
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'radhe_cars.urls'

_template_context_processors = [
    'django.template.context_processors.request',
    'django.contrib.auth.context_processors.auth',
    'django.contrib.messages.context_processors.messages',
]
if DEBUG:
    _template_context_processors.insert(0, 'django.template.context_processors.debug')

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': _template_context_processors,
        },
    },
]

WSGI_APPLICATION = 'radhe_cars.wsgi.application'

# Use DATABASE_URL from Render/Supabase when set; otherwise use local PostgreSQL
# ssl_require: Supabase requires TLS (set DATABASE_SSL_REQUIRE=false only for local non-SSL Postgres)
if os.environ.get('DATABASE_URL'):
    _ssl = os.environ.get('DATABASE_SSL_REQUIRE', 'true').lower() in ('true', '1', 'yes')
    _url = os.environ.get('DATABASE_URL')
    # Session/transaction pooler (PgBouncer): no persistent conn + no server-side cursors
    _pooler = 'pooler.' in _url
    _max_age = 0 if _pooler else int(os.environ.get('DB_CONN_MAX_AGE', '600'))
    _db = dj_database_url.parse(
        _url,
        conn_max_age=_max_age,
        ssl_require=_ssl,
        disable_server_side_cursors=_pooler,
    )
    if os.environ.get('DATABASE_IPV4_PREFER', 'true').lower() in ('true', '1', 'yes'):
        _prefer_ipv4_for_supabase(_db)
    DATABASES = {'default': _db}
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': 'radhe_auto',
            'USER': 'postgres',
            'PASSWORD': '1234',
            'HOST': 'localhost',
            'PORT': '5432',
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')] if os.path.isdir(os.path.join(BASE_DIR, 'static')) else []
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'
ACCOUNT_LOGIN_URL = '/login/'
ACCOUNT_LOGOUT_REDIRECT_URL = '/'
ACCOUNT_ADAPTER = 'cars.account_adapter.CustomAccountAdapter'

# Google OAuth - set via environment variables (never commit secrets)
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')

# HTTPS / cookies — only when DEBUG=False (production)
if not DEBUG:
    SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', 'true').lower() in ('true', '1', 'yes')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(os.environ.get('SECURE_HSTS_SECONDS', '31536000'))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = os.environ.get('SECURE_HSTS_INCLUDE_SUBDOMAINS', 'true').lower() in (
        'true',
        '1',
        'yes',
    )
    SECURE_HSTS_PRELOAD = os.environ.get('SECURE_HSTS_PRELOAD', 'true').lower() in ('true', '1', 'yes')
    SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
    # Behind nginx, ALB, Render, etc. (set when TLS terminates at the proxy)
    if os.environ.get('USE_X_FORWARDED_HEADERS', '').lower() in ('true', '1', 'yes'):
        SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
        USE_X_FORWARDED_HOST = True

_csrf_origins = os.environ.get('CSRF_TRUSTED_ORIGINS', '').strip()
_csrf_list = [o.strip() for o in _csrf_origins.split(',') if o.strip()] if _csrf_origins else []
# LAN / phone testing: Django 4+ CSRF checks need the full origin (e.g. http://192.168.x.x:8000)
if DEBUG:
    _csrf_list.extend(
        [
            'http://127.0.0.1:8000',
            'http://localhost:8000',
            'http://127.0.0.1:8080',
            'http://localhost:8080',
        ]
    )
    for _h in ALLOWED_HOSTS:
        if _h and _h != '*':
            _csrf_list.extend([f'http://{_h}:8000', f'http://{_h}:8080'])
    _csrf_list = list(dict.fromkeys(_csrf_list))
if _csrf_list:
    CSRF_TRUSTED_ORIGINS = _csrf_list

if not DEBUG:
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'handlers': {'console': {'class': 'logging.StreamHandler'}},
        'loggers': {
            'django.request': {
                'handlers': ['console'],
                'level': 'ERROR',
                'propagate': False,
            },
        },
    }
