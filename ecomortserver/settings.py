# ecomortserver/settings.py
import os
from pathlib import Path
from datetime import timedelta
from decouple import config
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-0486x9o3r67tw)l9xo-&w*mnj8x1wlw9t(u*zfl299t7q$0q!l')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')

# Application definition
INSTALLED_APPS = [
    'unfold',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'gridmortapp',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', 
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'ecomortserver.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'gridmortapp' / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'ecomortserver.wsgi.application'

# Database - Neon PostgreSQL
DATABASES = {
    'default': dj_database_url.config(
        default=config('DATABASE_URL'),
        conn_max_age=600,
        ssl_require=True
    )
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Nairobi'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static', 
]
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage' 

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ============ CORS SETTINGS ============
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='http://localhost:5173,http://127.0.0.1:5173').split(',')

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# ============ CSRF SETTINGS ============
CSRF_COOKIE_SECURE = config('CSRF_COOKIE_SECURE', default=False, cast=bool)
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='http://localhost:5173').split(',')

# ============ SESSION COOKIE SETTINGS ============
SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', default=False, cast=bool)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

# ============ REST FRAMEWORK ============
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'gridmortapp.authentication.CookieJWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# ============ JWT SETTINGS ============
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    'JWK_URL': None,
    'LEEWAY': 0,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'TOKEN_USER_CLASS': 'rest_framework_simplejwt.models.TokenUser',
    'JTI_CLAIM': 'jti',
    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(minutes=5),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=1),
}

# Unfold settings (keep your existing)
from django.utils.translation import gettext_lazy as _

UNFOLD = {
    "SITE_TITLE": "Support System",
    "SITE_HEADER": "Ticket System",
    "SITE_SUBHEADER": "Infrastructure Management",
    "SITE_SYMBOL": "support_agent",
    "SITE_FAVICONS": [],
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "BORDER_RADIUS": "8px",
    "COLORS": {
        "primary": {
            "50": "oklch(97.5% 0.03 45)",
            "100": "oklch(95% 0.06 45)",
            "200": "oklch(90% 0.12 45)",
            "300": "oklch(85% 0.18 45)",
            "400": "oklch(78% 0.24 45)",
            "500": "oklch(70% 0.30 45)",
            "600": "oklch(62% 0.28 45)",
            "700": "oklch(52% 0.25 45)",
            "800": "oklch(42% 0.22 45)",
            "900": "oklch(32% 0.18 45)",
            "950": "oklch(22% 0.14 45)",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "command_search": False,
        "show_all_applications": False,
        "navigation": [
            {
                "title": _("Authentication & Access"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("API Tokens"),
                        "icon": "key",
                        "link": "/authtoken/token/",
                        "permission": lambda request: request.user.has_perm("authtoken.view_token"),
                    },
                    {
                        "title": _("Users"),
                        "icon": "manage_accounts",
                        "link": "/auth/user/",
                        "permission": lambda request: request.user.has_perm("auth.view_user"),
                    },
                    {
                        "title": _("Groups"),
                        "icon": "groups",
                        "link": "/auth/group/",
                        "permission": lambda request: request.user.has_perm("auth.view_group"),
                    },
                ],
            },
            {
                "title": _("Ticket Management"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Tickets"),
                        "icon": "confirmation_number",
                        "link": "/gridmortapp/ticket/",
                        "permission": lambda request: request.user.has_perm("gridmortapp.view_ticket"),
                    },
                    {
                        "title": _("Ticket Categories"),
                        "icon": "category",
                        "link": "/gridmortapp/ticketcategory/",
                        "permission": lambda request: request.user.has_perm("gridmortapp.view_ticketcategory"),
                    },
                    {
                        "title": _("Ticket Priorities"),
                        "icon": "low_priority",
                        "link": "/gridmortapp/ticketpriority/",
                        "permission": lambda request: request.user.has_perm("gridmortapp.view_ticketpriority"),
                    },
                    {
                        "title": _("Ticket Statuses"),
                        "icon": "rule",
                        "link": "/gridmortapp/ticketstatus/",
                        "permission": lambda request: request.user.has_perm("gridmortapp.view_ticketstatus"),
                    },
                    {
                        "title": _("Ticket Messages"),
                        "icon": "chat",
                        "link": "/gridmortapp/ticketmessage/",
                        "permission": lambda request: request.user.has_perm("gridmortapp.view_ticketmessage"),
                    },
                ],
            },
            {
                "title": _("User Management"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Departments"),
                        "icon": "corporate_fare",
                        "link": "/gridmortapp/department/",
                        "permission": lambda request: request.user.has_perm("gridmortapp.view_department"),
                    },
                    {
                        "title": _("Employee Profiles"),
                        "icon": "badge",
                        "link": "/gridmortapp/employeeprofile/",
                        "permission": lambda request: request.user.has_perm("gridmortapp.view_employeeprofile"),
                    },
                ],
            },
            {
                "title": _("Inventory Management"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Hardware Items"),
                        "icon": "devices",
                        "link": "/gridmortapp/hardwareitem/",
                        "permission": lambda request: request.user.has_perm("gridmortapp.view_hardwareitem"),
                    },
                    {
                        "title": _("Hardware Categories"),
                        "icon": "inventory_2",
                        "link": "/gridmortapp/hardwarecategory/",
                        "permission": lambda request: request.user.has_perm("gridmortapp.view_hardwarecategory"),
                    },
                    {
                        "title": _("Inventory Movements"),
                        "icon": "local_shipping",
                        "link": "/gridmortapp/inventorymovement/",
                        "permission": lambda request: request.user.has_perm("gridmortapp.view_inventorymovement"),
                    },
                ],
            },
            {
                "title": _("Reports"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Reports"),
                        "icon": "analytics",
                        "link": "/gridmortapp/report/",
                        "permission": lambda request: request.user.has_perm("gridmortapp.view_report"),
                    },
                    {
                        "title": _("Report Types"),
                        "icon": "assignment_turned_in",
                        "link": "/gridmortapp/reporttype/",
                        "permission": lambda request: request.user.has_perm("gridmortapp.view_reporttype"),
                    },
                    {
                        "title": _("Report Logs"),
                        "icon": "history_toggle_off",
                        "link": "/gridmortapp/reportlog/",
                        "permission": lambda request: request.user.has_perm("gridmortapp.view_reportlog"),
                    },
                ],
            },
            {
                "title": _("Audit Logs"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Audit Logs"),
                        "icon": "history",
                        "link": "/gridmortapp/auditlog/",
                        "permission": lambda request: request.user.has_perm("gridmortapp.view_auditlog"),
                    },
                ]
            }
        ],
    },
    "ENVIRONMENT": "development",
    "EXTENSIONS": {
        "modeltranslation": {
            "flags": {
                "en": "UK",
                "fr": "FR",
                "nl": "NL",
            },
        },
    },
}