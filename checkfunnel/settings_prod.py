"""
Production settings for Checkfunnel.
Inherits from settings.py and overrides unsafe dev values.

Usage:
  DJANGO_SETTINGS_MODULE=checkfunnel.settings_prod daphne ...
Or set in .env:
  DJANGO_SETTINGS_MODULE=checkfunnel.settings_prod
"""

from .settings import *  # noqa: F401, F403
import os

# ── Security ──────────────────────────────────────────────────────────────────
DEBUG = False

SECRET_KEY = os.environ['DJANGO_SECRET_KEY']   # must be set in .env — no default

ALLOWED_HOSTS = os.environ.get(
    'ALLOWED_HOSTS', 'app.checkfunnel.ai'
).split(',')

# HTTPS enforcements
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 63072000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'SAMEORIGIN'

# ── Static & media files ──────────────────────────────────────────────────────
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATIC_URL = '/static/'
MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_URL = '/media/'

# WhiteNoise is already in base MIDDLEWARE — just override storage
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Tell WhiteNoise to also serve the Vue dist output
WHITENOISE_ROOT = BASE_DIR / 'widget-vue' / 'dist'

# ── Email (production SMTP) ────────────────────────────────────────────────────
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# All other EMAIL_* vars come from .env via settings.py

# ── Logging ────────────────────────────────────────────────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
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
        'django': {'handlers': ['console'], 'level': 'WARNING', 'propagate': False},
        'celery': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
    },
}

# ── CORS (production) ─────────────────────────────────────────────────────────
# The widget is embedded via <script> on any customer website, so all origins
# must be allowed for the widget-facing API paths (/api/chat/, /api/analytics/).
# Admin API security relies on JWT auth, not CORS, so this is safe.
CORS_ALLOW_ALL_ORIGINS = True

# ── CSRF trusted origins ─────────────────────────────────────────────────────
CSRF_TRUSTED_ORIGINS = os.environ.get(
    'CSRF_TRUSTED_ORIGINS',
    'https://ai.checkfunnels.com',
).split(',')
