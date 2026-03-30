from pathlib import Path
import os
import socket
import dj_database_url
from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured


def _prefer_ipv4_for_supabase(db):
    """
    Supabase DNS can return IPv6 first; some hosts have no IPv6 route.
    Prefer IPv4 via libpq hostaddr when possible.
    Skip pooler hosts — IPv4-proxied; hostaddr can break PgBouncer.
    """
    host = db.get('HOST')
    if not host or 'pooler.' in host:
        return
    if 'supabase.co' not in host and 'supabase.com' not in host:
        return
    port = int(db.get('PORT') or 5432)
    try:
        infos = socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM)
        if infos:
            db.setdefault('OPTIONS', {})['hostaddr'] = infos[0][4][0]
    except OSError:
        pass


# -----------------------------------------------------------------------------
# Paths & env
# -----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

# Development: set DEBUG=True in .env. Production (Lightsail): DEBUG=False or omit.
DEBUG = os.environ.get('DEBUG', 'False').lower() in ('true', '1', 'yes')

# -----------------------------------------------------------------------------
# Required secrets (never commit real values)
# -----------------------------------------------------------------------------
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    raise ImproperlyConfigured('Set the SECRET_KEY environment variable.')

GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
    raise ImproperlyConfigured(
        'Set the GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables.'
    )

# -----------------------------------------------------------------------------
# Hosts / CSRF (production defaults for radheauto.com; override via env for staging)
# -----------------------------------------------------------------------------
# ALLOWED_HOSTS: comma-separated, e.g. radheauto.com,www.radheauto.com,127.0.0.1
_default_hosts = 'radheauto.com,www.radheauto.com'
ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get('ALLOWED_HOSTS', _default_hosts).split(',')
    if h.strip()
]

# Production HTTPS origins (required for CSRF on POST when DEBUG=False).
_production_csrf_origins = [
    'https://www.radheauto.com',
    'https://radheauto.com',
]
_csrf_from_env = [
    o.strip()
    for o in os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',')
    if o.strip()
]
CSRF_TRUSTED_ORIGINS = list(dict.fromkeys(_production_csrf_origins + _csrf_from_env))
if DEBUG:
    # Local dev over HTTP
    CSRF_TRUSTED_ORIGINS.extend(
        [
            'http://127.0.0.1:8000',
            'http://localhost:8000',
            'http://127.0.0.1:8080',
            'http://localhost:8080',
        ]
    )
    for _h in ALLOWED_HOSTS:
        CSRF_TRUSTED_ORIGINS.extend([f'http://{_h}:8000', f'http://{_h}:8080'])
    CSRF_TRUSTED_ORIGINS = list(dict.fromkeys(CSRF_TRUSTED_ORIGINS))

# -----------------------------------------------------------------------------
# Django apps
# -----------------------------------------------------------------------------
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

# django.contrib.sites: set domain to www.radheauto.com (or canonical host) in Admin → Sites.
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
    'radhe_cars.middleware.NormalizeAdminPanelPathMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'cars.admin_panel.middleware.StaffAdminPanelMiddleware',
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

# -----------------------------------------------------------------------------
# Database: PostgreSQL only — either DATABASE_URL (Supabase/production) or DB_* (local Postgres)
# -----------------------------------------------------------------------------
if os.environ.get('DATABASE_URL'):
    _ssl = os.environ.get('DATABASE_SSL_REQUIRE', 'true').lower() in ('true', '1', 'yes')
    _url = os.environ['DATABASE_URL']
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
elif os.environ.get('DB_HOST') and os.environ.get('DB_NAME'):
    # Local/dev Postgres without DATABASE_URL (no SQLite)
    _local = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ['DB_NAME'],
        'USER': os.environ.get('DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ['DB_HOST'],
        'PORT': os.environ.get('DB_PORT', '5432'),
        'CONN_MAX_AGE': int(os.environ.get('DB_CONN_MAX_AGE', '0')),
    }
    if os.environ.get('DB_SSL', '').lower() in ('true', '1', 'yes'):
        _local.setdefault('OPTIONS', {})['sslmode'] = 'require'
    DATABASES = {'default': _local}
else:
    raise ImproperlyConfigured(
        'Set PostgreSQL via .env: either DATABASE_URL=postgresql://... '
        'or DB_HOST, DB_NAME, DB_USER, DB_PASSWORD (and optional DB_PORT). '
        'SQLite is not used.'
    )


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

# -----------------------------------------------------------------------------
# Static (WhiteNoise) & media (Nginx in production — Django does not serve /media/ when DEBUG=False)
# -----------------------------------------------------------------------------
STATIC_URL = 'static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')] if os.path.isdir(os.path.join(BASE_DIR, 'static')) else []
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Production: compressed static files via WhiteNoise. Dev: default finder storage.
if not DEBUG:
    STORAGES = {
        'default': {
            'BACKEND': 'django.core.files.storage.FileSystemStorage',
        },
        'staticfiles': {
            'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage',
        },
    }
    # Long cache for fingerprinted static assets (PageSpeed: cache lifetimes)
    WHITENOISE_MAX_AGE = 31536000

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'
ACCOUNT_LOGIN_URL = '/login/'
ACCOUNT_LOGOUT_REDIRECT_URL = '/'
ACCOUNT_ADAPTER = 'cars.account_adapter.CustomAccountAdapter'

# -----------------------------------------------------------------------------
# Security: HTTPS (Nginx terminates TLS; Gunicorn sees HTTP + X-Forwarded-Proto)
# -----------------------------------------------------------------------------
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Trust proxy when USE_X_FORWARDED_HEADERS=true (default in production) or explicitly set.
_use_proxy = os.environ.get('USE_X_FORWARDED_HEADERS', 'false' if DEBUG else 'true').lower() in (
    'true',
    '1',
    'yes',
)
if _use_proxy:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    USE_X_FORWARDED_HOST = True

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', 'true').lower() in (
        'true',
        '1',
        'yes',
    )
    # Optional HSTS (start small, increase later)
    SECURE_HSTS_SECONDS = int(os.environ.get('SECURE_HSTS_SECONDS', '31536000'))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = False
else:
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    SECURE_SSL_REDIRECT = False
    SECURE_HSTS_SECONDS = 0

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'cars.admin_panel.auth': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
    },
}
