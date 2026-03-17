"""
Django settings for shop project
"""
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

# =========================
# ENV
# =========================
env = environ.Env(
    DEBUG=(bool, True),
)
environ.Env.read_env(BASE_DIR / ".env")

# =========================
# SECURITY / CORE
# =========================
SECRET_KEY = env("SECRET_KEY", default="django-insecure-dev-key")
DEBUG = env.bool("DEBUG", default=True)

ALLOWED_HOSTS = env.list(
    "ALLOWED_HOSTS",
    default=["127.0.0.1", "localhost"],
)

CSRF_TRUSTED_ORIGINS = env.list(
    "CSRF_TRUSTED_ORIGINS",
    default=[
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ],
)

# Если сайт будет за reverse proxy / nginx / cloudflare
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# =========================
# APPLICATIONS
# =========================
INSTALLED_APPS = [
    "jazzmin",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "catalog",
    "orders",
    "accounts",
    "support",
    "reviews",
    "modeltranslation",
    "dashboard",
]

# =========================
# MIDDLEWARE
# =========================
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",

    "payments.middleware.CloudflareMiddleware",
]

ROOT_URLCONF = "shop.urls"

# =========================
# TEMPLATES
# =========================
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "shop.wsgi.application"

# =========================
# DATABASE
# =========================
DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default=(
            f"postgres://{env('DB_USER', default='shopuser')}:"
            f"{env('DB_PASSWORD', default='')}"
            f"@{env('DB_HOST', default='localhost')}:"
            f"{env('DB_PORT', default='5432')}/"
            f"{env('DB_NAME', default='shopdb')}"
        ),
    )
}

# Держим соединения чуть дольше в проде
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DB_CONN_MAX_AGE", default=60)

# =========================
# PASSWORD VALIDATION
# =========================
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# =========================
# INTERNATIONALIZATION
# =========================
LANGUAGE_CODE = "ru-ru"
TIME_ZONE = "Europe/Moscow"
USE_I18N = True
USE_TZ = True

# =========================
# STATIC / MEDIA
# =========================
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# WhiteNoise + versioned static files
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

WHITENOISE_MAX_AGE = 31536000

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# =========================
# YANDEX DELIVERY
# =========================
YANDEX_DELIVERY_BASE_URL = env(
    "YANDEX_DELIVERY_BASE_URL",
    default="https://b2b.taxi.tst.yandex.net",
)
YANDEX_DELIVERY_TOKEN = env("YANDEX_DELIVERY_TOKEN", default="")
YANDEX_PLATFORM_STATION_ID = env("YANDEX_PLATFORM_STATION_ID", default="")
YANDEX_PAYMENT_METHOD = env("YANDEX_PAYMENT_METHOD", default="already_paid")

# =========================
# YOOKASSA
# =========================
YOOKASSA_SHOP_ID = env("YOOKASSA_SHOP_ID", default="")
YOOKASSA_API_KEY = env("YOOKASSA_API_KEY", default="")

# =========================
# EMAIL
# =========================
EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    default=(
        "django.core.mail.backends.console.EmailBackend"
        if DEBUG else
        "django.core.mail.backends.smtp.EmailBackend"
    ),
)
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL", default=False)

DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@shop.local")
SERVER_EMAIL = env("SERVER_EMAIL", default=DEFAULT_FROM_EMAIL)

# =========================
# PRODUCTION SECURITY
# =========================
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)

    SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31536000)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True)
    SECURE_HSTS_PRELOAD = env.bool("SECURE_HSTS_PRELOAD", default=True)

    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"
    SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

    SESSION_COOKIE_HTTPONLY = True
else:
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    SECURE_SSL_REDIRECT = False