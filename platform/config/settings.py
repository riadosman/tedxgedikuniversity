"""Environment configuration. Production refuses local-only fallback settings."""

import os
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BASE_DIR.parent
load_dotenv(os.getenv("TEDX_ENV_FILE", str(ROOT_DIR / ".env")))
VERCEL = os.getenv("VERCEL") == "1"
PRODUCTION = VERCEL or os.getenv("DJANGO_ENV", "development") == "production"
DEBUG = not PRODUCTION
LOCAL_EVENT_PREVIEW = not PRODUCTION
DEV_ONE_CLICK_LOGIN = os.getenv("DEV_ONE_CLICK_LOGIN", "false").lower() == "true"
DEV_LOGIN_EVENT = os.getenv("DEV_LOGIN_EVENT", "tedxgedik")
DEV_EVENT_REHEARSAL = os.getenv("DEV_EVENT_REHEARSAL", "false").lower() == "true"
if PRODUCTION and DEV_EVENT_REHEARSAL:
    raise ImproperlyConfigured("DEV_EVENT_REHEARSAL must be disabled in production.")
if PRODUCTION and DEV_ONE_CLICK_LOGIN:
    raise ImproperlyConfigured("DEV_ONE_CLICK_LOGIN must be disabled in production.")
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
CREDENTIAL_KEY = os.environ["CREDENTIAL_KEY"]
try:
    from cryptography.fernet import Fernet

    Fernet(CREDENTIAL_KEY.encode())
except (ValueError, TypeError) as error:
    raise ImproperlyConfigured("CREDENTIAL_KEY must be a valid Fernet key.") from error
ALLOWED_HOSTS = [
    host.strip() for host in os.getenv("ALLOWED_HOSTS", "127.0.0.1,localhost").split(",") if host.strip()
]
if VERCEL:
    # Deployment, branch alias and production domain are different hostnames.
    # Trust only this project's platform-provided names, not every vercel.app site.
    for variable in ("VERCEL_URL", "VERCEL_BRANCH_URL", "VERCEL_PROJECT_PRODUCTION_URL"):
        host = os.getenv(variable, "").strip()
        if host and host not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(host)
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CSRF_TRUSTED_ORIGINS", PUBLIC_BASE_URL).split(",")
    if origin.strip()
]
db = urlparse(os.environ["DATABASE_URL"])
if db.scheme not in {"postgres", "postgresql"}:
    raise ImproperlyConfigured("PostgreSQL is required, including for transaction tests.")
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": unquote(db.path.lstrip("/")),
        "USER": unquote(db.username or ""),
        "PASSWORD": unquote(db.password or ""),
        "HOST": db.hostname,
        "PORT": db.port or 5432,
        "CONN_MAX_AGE": 0 if VERCEL else 60,
        "CONN_HEALTH_CHECKS": True,
        "DISABLE_SERVER_SIDE_CURSORS": VERCEL,
        "OPTIONS": {
            "sslmode": os.getenv("DB_SSLMODE")
            or parse_qs(db.query).get("sslmode", ["require" if PRODUCTION else "prefer"])[0],
            "connect_timeout": 10,
        },
    }
}
if os.getenv("TEST_DATABASE_NAME"):
    DATABASES["default"]["TEST"] = {"NAME": os.environ["TEST_DATABASE_NAME"]}
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_otp",
    "django_otp.plugins.otp_totp",
    "django_otp.plugins.otp_static",
    "core",
    "admissions",
    "team",
    "program",
    "operations",
    "communications",
    "documents",
    "payments",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "core.language.LanguageLinkMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_otp.middleware.OTPMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.SecurityMiddleware",
]
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
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
                "core.context.site_context",
            ]
        },
    }
]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]
LANGUAGE_CODE = "en"
LANGUAGES = [("en", "English"), ("tr", "Türkçe"), ("ar", "العربية")]
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = "Europe/Istanbul"
USE_I18N = True
FORM_RENDERER = "core.renderers.LocalizedFormRenderer"
FORMS_URLFIELD_ASSUME_HTTPS = True
USE_TZ = True
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
        if PRODUCTION
        else "core.storage.PreviewStaticFilesStorage"
    },
}
MEDIA_ROOT = Path(
    os.getenv("PRIVATE_MEDIA_ROOT", "/tmp/tedx-media" if VERCEL else str(ROOT_DIR / ".local" / "media"))
)
FILE_UPLOADS_ENABLED = not VERCEL
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/staff/"
LOGOUT_REDIRECT_URL = "/"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = PRODUCTION
CSRF_COOKIE_SECURE = PRODUCTION
SESSION_COOKIE_AGE = 8 * 3600
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SECURE_SSL_REDIRECT = PRODUCTION
if VERCEL or os.getenv("TRUST_PROXY_HTTPS", "false").lower() == "true":
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = 31536000 if PRODUCTION else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = (
    PRODUCTION and os.getenv("HSTS_INCLUDE_SUBDOMAINS", "false").lower() == "true"
)
SECURE_HSTS_PRELOAD = PRODUCTION and os.getenv("HSTS_PRELOAD", "false").lower() == "true"
# Domain-wide HSTS and browser preload require separate domain-owner approval.
# Keep host HTTPS/HSTS enforced; these two advisory checks are intentionally scoped.
SILENCED_SYSTEM_CHECKS = (
    (
        (["security.W005"] if not SECURE_HSTS_INCLUDE_SUBDOMAINS else [])
        + (["security.W021"] if not SECURE_HSTS_PRELOAD else [])
    )
    if PRODUCTION
    else []
)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
MFA_REQUIRED = os.getenv("MFA_REQUIRED", "true").lower() == "true"
FILE_SCAN_COMMAND = os.getenv("FILE_SCAN_COMMAND", "")
FILE_UPLOAD_PERMISSIONS = 0o600
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o700
PAYMENT_PROVIDER = os.getenv("PAYMENT_PROVIDER", "")
DATA_UPLOAD_MAX_MEMORY_SIZE = 30 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024
OUTGOING_EMAIL_ENABLED = os.getenv("OUTGOING_EMAIL_ENABLED", "true").lower() == "true"
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.filebased.EmailBackend")
EMAIL_FILE_PATH = os.getenv("EMAIL_FILE_PATH", str(ROOT_DIR / ".local" / "mail"))
EMAIL_HOST = os.getenv("EMAIL_HOST", "")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "true").lower() == "true"
EMAIL_TIMEOUT = 15
if not OUTGOING_EMAIL_ENABLED:
    EMAIL_BACKEND = "django.core.mail.backends.dummy.EmailBackend"
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "")
if PRODUCTION and (len(SECRET_KEY) < 50 or not PUBLIC_BASE_URL.startswith("https://") or not MFA_REQUIRED):
    raise ImproperlyConfigured("Production requires a strong secret, HTTPS origin and MFA.")
if (
    PRODUCTION
    and OUTGOING_EMAIL_ENABLED
    and (
        not DEFAULT_FROM_EMAIL
        or EMAIL_BACKEND
        in {
            "django.core.mail.backends.filebased.EmailBackend",
            "django.core.mail.backends.console.EmailBackend",
            "django.core.mail.backends.locmem.EmailBackend",
            "django.core.mail.backends.dummy.EmailBackend",
        }
    )
):
    raise ImproperlyConfigured("Configure a real transactional email backend for production.")
if (
    PRODUCTION
    and OUTGOING_EMAIL_ENABLED
    and EMAIL_BACKEND.endswith("smtp.EmailBackend")
    and (not EMAIL_HOST or not EMAIL_USE_TLS)
):
    raise ImproperlyConfigured("Production SMTP requires an explicit host and TLS.")
if PRODUCTION and "*" in ALLOWED_HOSTS:
    raise ImproperlyConfigured("Production requires explicit allowed hostnames.")
if PRODUCTION and any(not origin.startswith("https://") or "*" in origin for origin in CSRF_TRUSTED_ORIGINS):
    raise ImproperlyConfigured("Production CSRF origins must be explicit HTTPS origins.")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {"redact": {"()": "core.logging.RedactingFilter"}},
    "formatters": {"safe": {"()": "core.logging.RedactingFormatter"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "filters": ["redact"], "formatter": "safe"}},
    "root": {"handlers": ["console"], "level": os.getenv("LOG_LEVEL", "INFO")},
}
