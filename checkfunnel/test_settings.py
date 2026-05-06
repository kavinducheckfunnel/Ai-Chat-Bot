"""
Test-specific Django settings.
Overrides production settings with fast, isolated, no-external-service equivalents.
"""
from .settings import *  # noqa: F401, F403

# Use a fast in-memory password hasher for speed
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Use in-memory email so we can inspect sent emails
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Use in-memory cache — no Redis required for tests
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Use in-memory channel layer — no Redis required for WebSocket tests
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    }
}

# Run Celery tasks synchronously in-process (no broker needed)
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Silence rate-limit throttles during tests (override in specific test modules)
REST_FRAMEWORK = {
    **REST_FRAMEWORK,  # noqa: F405
    'DEFAULT_THROTTLE_RATES': {
        'chat': '1000/min',
        'chat_session': '1000/min',
    },
}

# Stripe — blank so tests must mock it explicitly
STRIPE_SECRET_KEY = 'sk_test_dummy'
STRIPE_WEBHOOK_SECRET = 'whsec_dummy'

# Static files — no compression in tests
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# Use OS superuser so the test runner can CREATE/DROP the test_* database.
# The 'ram' role has no password on local Homebrew Postgres.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'checkfunnel_db',
        'USER': 'ram',
        'PASSWORD': '',
        'HOST': 'localhost',
        'PORT': '5432',
        'TEST': {
            'NAME': 'test_checkfunnel_db',
        },
    }
}
