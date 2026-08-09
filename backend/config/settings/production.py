"""Production-specific settings."""

from .base import *  # noqa: F401, F403

DEBUG = False

# ============================================================
# Security
# ============================================================
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = "DENY"

CSRF_TRUSTED_ORIGINS = [
    origin.strip() for origin in config("CSRF_TRUSTED_ORIGINS", default="", cast=Csv()) if origin.strip()
]

# ============================================================
# Email — use real SMTP in production
# ============================================================
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

# ============================================================
# Static files — served by nginx in production
# ============================================================
STORAGES = {
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage",
    },
}
