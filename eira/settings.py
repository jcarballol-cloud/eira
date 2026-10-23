# SPDX-License-Identifier: EUPL-1.2
"""Configuración de Eira. Todo o sensible chega por variables de contorno (ver .env.example)."""

import os
from pathlib import Path
from urllib.parse import unquote, urlparse

from django.utils.translation import gettext_lazy as _

BASE_DIR = Path(__file__).resolve().parent.parent


def env(name, default=None):
    return os.environ.get(name, default)


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "si", "on"}


def env_list(name, default=""):
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


def parse_database_url(url):
    """Interpreta DATABASE_URL (postgres://… ou sqlite:///…) sen dependencias externas."""
    parsed = urlparse(url)
    if parsed.scheme in {"sqlite", "sqlite3"}:
        # sqlite:///relativo.db, sqlite:////absoluto.db, sqlite:///C:/ruta.db
        name = unquote(parsed.path)[1:]
        return {"ENGINE": "django.db.backends.sqlite3", "NAME": name or BASE_DIR / "db.sqlite3"}
    if parsed.scheme in {"postgres", "postgresql", "pgsql"}:
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": unquote(parsed.path.lstrip("/")),
            "USER": unquote(parsed.username or ""),
            "PASSWORD": unquote(parsed.password or ""),
            "HOST": parsed.hostname or "",
            "PORT": str(parsed.port or ""),
            "CONN_MAX_AGE": 60,
        }
    raise ValueError(f"DATABASE_URL non soportada: {parsed.scheme}")


DEBUG = env_bool("EIRA_DEBUG", False)
# En desenvolvemento xérase unha chave efémera; en produción é obrigatoria.
SECRET_KEY = env("EIRA_SECRET_KEY") or ("dev-insecure-key-only-for-local-use" if DEBUG else None)
if not SECRET_KEY:
    raise RuntimeError("Define EIRA_SECRET_KEY (ou EIRA_DEBUG=1 en desenvolvemento).")

ALLOWED_HOSTS = env_list("EIRA_ALLOWED_HOSTS", "localhost,127.0.0.1,.localhost,testserver")
CSRF_TRUSTED_ORIGINS = env_list("EIRA_CSRF_TRUSTED_ORIGINS", "")

# Dominio base para resolver concellos por subdominio: <slug>.EIRA_BASE_DOMAIN
EIRA_BASE_DOMAIN = env("EIRA_BASE_DOMAIN", "localhost")
# Ferramentas de demostración (/dev/…): bandexa de correo, TPV simulado, simulador de pechadura…
EIRA_DEMO_TOOLS = env_bool("EIRA_DEMO_TOOLS", DEBUG)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "apps.tenants",
    "apps.accounts",
    "apps.facilities",
    "apps.bookings",
    "apps.access",
    "apps.maintenance",
    "apps.incidents",
    "apps.activities",
    "apps.notifications",
    "apps.analytics",
    "apps.integrations",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "apps.tenants.middleware.SecurityHeadersMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "apps.tenants.middleware.SubdomainTenantMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.tenants.middleware.TenantMiddleware",
]

ROOT_URLCONF = "eira.urls"
WSGI_APPLICATION = "eira.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.i18n",
                "apps.tenants.context_processors.eira",
            ],
        },
    }
]

DATABASES = {
    "default": parse_database_url(env("DATABASE_URL", f"sqlite:///{BASE_DIR / 'db.sqlite3'}"))
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = "accounts:login"

AUTHENTICATION_BACKENDS = ["django.contrib.auth.backends.ModelBackend"]

# Só o persoal técnico do admin de Django usa contrasinal; a cidadanía accede sen contrasinal.
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
]

LANGUAGE_CODE = "gl"
LANGUAGES = [("gl", _("Galego")), ("es", _("Castelán"))]
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = "Europe/Madrid"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "/media/"
MEDIA_ROOT = Path(env("EIRA_MEDIA_ROOT", BASE_DIR / "media"))
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"
        if not DEBUG
        else "django.contrib.staticfiles.storage.StaticFilesStorage"
    },
}

# Subidas: límite de tamaño (as fotos reescálanse e límpanse de EXIF ao gardar).
EIRA_MAX_UPLOAD_BYTES = int(env("EIRA_MAX_UPLOAD_BYTES", 5 * 1024 * 1024))
DATA_UPLOAD_MAX_MEMORY_SIZE = EIRA_MAX_UPLOAD_BYTES + 512 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = EIRA_MAX_UPLOAD_BYTES

# Seguridade
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = env_bool("EIRA_SECURE_COOKIES", not DEBUG)
CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
SECURE_PROXY_SSL_HEADER = (
    ("HTTP_X_FORWARDED_PROTO", "https") if env_bool("EIRA_BEHIND_PROXY") else None
)
SECURE_SSL_REDIRECT = env_bool("EIRA_SSL_REDIRECT", False)
SECURE_HSTS_SECONDS = int(env("EIRA_HSTS_SECONDS", 0))
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14

# Teselas do mapa: por defecto OpenStreetMap; un concello pode apuntar ao seu propio servidor.
EIRA_TILE_URL = env("EIRA_TILE_URL", "https://tile.openstreetmap.org/{z}/{x}/{y}.png")
EIRA_TILE_ORIGIN = env("EIRA_TILE_ORIGIN", "https://tile.openstreetmap.org")

CACHES = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "eira"}
}
if env("EIRA_CACHE_DIR"):
    CACHES["default"] = {
        "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
        "LOCATION": env("EIRA_CACHE_DIR"),
    }

# Límites de envío de códigos de acceso
EIRA_LOGIN_CODE_TTL_SECONDS = 10 * 60
EIRA_LOGIN_CODE_MAX_ATTEMPTS = 5
EIRA_LOGIN_RATE_LIMIT = int(env("EIRA_LOGIN_RATE_LIMIT", 5))  # envíos por correo e hora
EIRA_LOGIN_RATE_LIMIT_IP = int(env("EIRA_LOGIN_RATE_LIMIT_IP", 20))  # envíos por IP e hora

# Adaptadores de integración (todos simulados por defecto; ver apps/integrations).
EIRA_ADAPTERS = {
    "mail": env("EIRA_MAIL_ADAPTER", "apps.integrations.mail.DevMailboxAdapter"),
    "identity": env("EIRA_IDENTITY_ADAPTER", "apps.integrations.identity.FakeClaveAdapter"),
    "payment": env("EIRA_PAYMENT_ADAPTER", "apps.integrations.payments.FakeRedsysAdapter"),
    "lock": env("EIRA_LOCK_ADAPTER", "apps.integrations.locks.MockConnectedLockAdapter"),
    "weather": env("EIRA_WEATHER_ADAPTER", "apps.integrations.weather.FakeWeatherAdapter"),
    "telegram": env("EIRA_TELEGRAM_ADAPTER", "apps.integrations.telegram.FakeTelegramAdapter"),
    "push": env("EIRA_PUSH_ADAPTER", "apps.integrations.push.FakeWebPushAdapter"),
    "ai": env("EIRA_AI_ADAPTER", "apps.integrations.ai.FakeAIAdapter"),
}
EIRA_AI_ENABLED = env_bool("EIRA_AI_ENABLED", True)
EIRA_AI_BASE_URL = env("EIRA_AI_BASE_URL", "http://localhost:11434/v1")
EIRA_AI_MODEL = env("EIRA_AI_MODEL", "llama3.1")
EIRA_METEOSIX_API_KEY = env("EIRA_METEOSIX_API_KEY", "")
EIRA_DEFAULT_FROM_EMAIL = env("EIRA_FROM_EMAIL", "non-responder@eira.invalid")

# Umbral mínimo de agregación do observatorio (k-anonimato básico)
EIRA_MIN_AGGREGATION = int(env("EIRA_MIN_AGGREGATION", 10))

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticatedOrReadOnly"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_THROTTLE_RATES": {"anon": "120/min", "user": "300/min"},
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
}
SPECTACULAR_SETTINGS = {
    "TITLE": "Eira API",
    "DESCRIPTION": "API aberta de Eira: concellos, instalacións, dispoñibilidade, reservas e incidencias.",
    "VERSION": "0.1.0",
    "OAS_VERSION": "3.1.0",
    "LICENSE": {
        "name": "EUPL-1.2",
        "url": "https://interoperable-europe.ec.europa.eu/collection/eupl",
    },
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": r"/api/v1",
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": env("EIRA_LOG_LEVEL", "INFO")},
    "loggers": {"django.db.backends": {"level": "WARNING"}},
}
