"""
Django base settings for channels_admin project.

This file contains settings that are common to all environments.
"""

import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get(
    "SECRET_KEY", "django-insecure-change-me-in-production"
)

# Site URL for building absolute URLs (needed for Telegram photo uploads)
SITE_URL = os.environ.get("SITE_URL", "http://localhost:8000")

# Application definition
INSTALLED_APPS = [
    "admin_interface",
    "colorfield",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party apps
    "rest_framework",
    "django_filters",
    "corsheaders",
    "django_celery_beat",
    "django_celery_results",
    "django_prometheus",
    # Local apps
    "apps.core",
    "apps.accounts",
    "apps.telegram_channels",
    "apps.posts",
    "apps.stats",
    "apps.integrations.telegram_bot",
    "apps.integrations.translation",
    "apps.monitoring",
]

MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware",
]

ROOT_URLCONF = "backend.urls"

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

WSGI_APPLICATION = "backend.wsgi.application"

# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "channels_admin"),
        "USER": os.environ.get("POSTGRES_USER", "postgres"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "postgres"),
        "HOST": os.environ.get("POSTGRES_HOST", "db"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}

# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators
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

# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Media files
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Django REST Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
}

# Celery Configuration
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = os.environ.get(
    "CELERY_RESULT_BACKEND", "django-db"
)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# Celery Beat Schedule (Periodic Tasks)
# Note: This is the default schedule. You can override it in Django Admin
# or through PeriodicTask model for more flexibility.
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    # Sync channels from Telegram Bot Gateway every 5 minutes
    # This is a backup for webhook mode or primary method for polling mode
    "sync-bot-channels": {
        "task": "apps.integrations.telegram_bot.tasks.process_bot_updates",
        "schedule": crontab(minute="*/5"),
        "options": {
            "expires": 300,  # Task expires after 5 minutes if not executed
        },
    },
    # Sync channel info (title, description, member_count) every 30 minutes
    "sync-all-channels-info": {
        "task": "apps.integrations.telegram_bot.tasks.sync_all_channels",
        "schedule": crontab(minute="*/30"),
    },
    # Verify bot permissions every hour
    "verify-bot-permissions": {
        "task": "apps.integrations.telegram_bot.tasks.verify_all_channel_permissions",
        "schedule": crontab(minute=0),  # Every hour
    },
    # Sync channel statistics every 15 minutes
    "sync-channel-stats": {
        "task": "apps.stats.tasks.sync_all_channel_stats",
        "schedule": crontab(minute="*/15"),
    },
    # Sync recent post statistics every 10 minutes
    "sync-post-stats": {
        "task": "apps.stats.tasks.sync_recent_post_stats",
        "schedule": crontab(minute="*/10"),
    },
    # Calculate global stats daily at 01:00
    "calculate-global-stats": {
        "task": "apps.stats.tasks.calculate_global_stats",
        "schedule": crontab(hour=1, minute=0),
    },
    # Calculate daily stats at 02:00 (for previous day)
    "calculate-daily-stats": {
        "task": "apps.stats.tasks.calculate_daily_stats",
        "schedule": crontab(hour=2, minute=0),
    },
    # Cleanup old stats every Sunday at 03:00
    "cleanup-old-stats": {
        "task": "apps.stats.tasks.cleanup_old_stats",
        "schedule": crontab(hour=3, minute=0, day_of_week=0),
    },
    # Process pending translations every 2 minutes
    "process-pending-translations": {
        "task": "apps.integrations.translation.tasks.process_pending_translations",
        "schedule": crontab(minute="*/2"),
    },
}

# Cache Configuration
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": os.environ.get("REDIS_URL", "redis://redis:6379/0"),
    }
}

# Logging Configuration
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
        "json": {
            "()": "apps.core.logging.JsonFormatter",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "celery": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "apps": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
    },
}

# Integration settings

# Telegram Bot Gateway
# Documentation: See API (2).md or http://<gateway>/docs
TELEGRAM_BOT_SERVICE_URL = os.environ.get(
    "TELEGRAM_BOT_SERVICE_URL", "http://178.217.98.201:8001"
)
TELEGRAM_BOT_SERVICE_TOKEN = os.environ.get(
    "TELEGRAM_BOT_SERVICE_TOKEN", ""
)

# LLM Translation Middleware
# LLM Translation Middleware
TRANSLATION_SERVICE_URL = os.environ.get(
    "TRANSLATION_SERVICE_URL", "http://178.217.98.201:8002"
)
TRANSLATION_SERVICE_TOKEN = os.environ.get(
    "TRANSLATION_SERVICE_TOKEN",
    "669d2bb55f63c5145eff622ce926ad52ef266e39c983b572a5ac45159fddf6e9"
)
TRANSLATION_CONTEXT = os.environ.get("TRANSLATION_CONTEXT", "news channel")
TRANSLATION_TONE = os.environ.get("TRANSLATION_TONE", "professional")

# Request timeouts (in seconds)
HTTP_TIMEOUT_CONNECT = 10
HTTP_TIMEOUT_READ = 60
HTTP_TIMEOUT_WRITE = 60

# Retry settings
HTTP_MAX_RETRIES = 3
HTTP_RETRY_DELAY = 1.0  # seconds

# Telegram Bot Gateway specific settings
TELEGRAM_BOT_GATEWAY_TIMEOUT = float(
    os.environ.get("TELEGRAM_BOT_GATEWAY_TIMEOUT", "30")
)
# Idempotency: Use unique keys to prevent duplicate message sends
TELEGRAM_BOT_ENABLE_IDEMPOTENCY = os.environ.get(
    "TELEGRAM_BOT_ENABLE_IDEMPOTENCY", "true"
).lower() == "true"

# MTProto API for detailed statistics (configured on Gateway side)
# The Gateway needs these settings to enable MTProto:
# - MTPROTO_ENABLED=true
# - TELEGRAM_API_ID=<your api id>
# - TELEGRAM_API_HASH=<your api hash>
# - TELEGRAM_SESSION_STRING=<session string>
# Our backend will automatically use MTProto stats if available
TELEGRAM_USE_MTPROTO_STATS = os.environ.get(
    "TELEGRAM_USE_MTPROTO_STATS", "true"
).lower() == "true"

# Django Admin Interface settings
X_FRAME_OPTIONS = "SAMEORIGIN"
SILENCED_SYSTEM_CHECKS = ["security.W019"]

