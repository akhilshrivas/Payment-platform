"""Development-specific settings."""

from .base import *  # noqa: F401, F403

DEBUG = True

# ============================================================
# Development-only apps
# ============================================================
INSTALLED_APPS += ["debug_toolbar"]  # noqa: F405

MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]  # noqa: F405

INTERNAL_IPS = ["127.0.0.1", "localhost"]

# ============================================================
# Email — print to console
# ============================================================
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# ============================================================
# Looser CORS for development
# ============================================================
CORS_ALLOW_ALL_ORIGINS = True

# ============================================================
# Logging — more verbose in dev
# ============================================================
LOGGING["root"]["level"] = "DEBUG"  # noqa: F405
LOGGING["loggers"]["apps"]["level"] = "DEBUG"  # noqa: F405
