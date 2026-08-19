from pathlib import Path
import os
import boto3
from django.contrib.messages import constants as messages
from celery.schedules import crontab
from datetime import timedelta
from dotenv import load_dotenv
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = str(os.getenv('SECRET_KEY'))

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True if os.getenv('DEBUG', 'False').lower() in ('true', '1', 't') else False

ALLOWED_HOSTS = [
    h.strip() for h in os.getenv('ALLOWED_HOSTS', '').split(',')
    if h.strip()
]

CSRF_TRUSTED_ORIGINS = [
    a.strip() for a in os.getenv('CSRF_TRUSTED_ORIGINS', '').split(',')
    if a.strip()
]

SESSION_ENGINE = 'django.contrib.sessions.backends.db'

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    "collectfasta",  # antes de staticfiles
    'storages',
    'rolepermissions',
    'django_celery_beat',
    'rest_framework',
    'rest_framework_simplejwt',   
    'apps.orders.apps.OrdersConfig',
    'apps.sims.apps.SimsConfig',
    'apps.dashboard.apps.DashboardConfig',
    'apps.users.apps.UsersConfig',
    'apps.send_email.apps.SendEmailConfig',
    'apps.voice_calls.apps.VoiceCallsConfig',
]

COLLECTFASTA_STRATEGY = "collectfasta.strategies.boto3.Boto3Strategy"

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'


# Database

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
#     }
# }


DATABASES = {
    'default': {
        'ENGINE': os.getenv('DB_ENGINE'),
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST'),
        'PORT': os.getenv('DB_PORT'),
        'CONN_MAX_AGE': 60,  # Reutiliza conexões por 60s (evita abrir/fechar a cada request)
    }
}

# Password validation

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
DATE_INPUT_FORMATS = ('%d/%m/%Y',)
USE_I18N = True
USE_TZ = False

DATE_FORMAT = '%d/%m/%Y'

DATA_UPLOAD_MAX_NUMBER_FILES = 1000

# Expirar sessão em 10h
SESSION_COOKIE_AGE = 36000


URL_PAINEL = str(os.getenv('URL_PAINEL'))
URL_CDN = 'https://'+str(os.getenv('URL_CDN'))


AWS_ACCESS_KEY_ID = str(os.getenv('AWS_ACCESS_KEY_ID'))
AWS_SECRET_ACCESS_KEY = str(os.getenv('AWS_SECRET_ACCESS_KEY'))
AWS_STORAGE_BUCKET_NAME = str(os.getenv('AWS_STORAGE_BUCKET_NAME'))
AWS_S3_CUSTOM_DOMAIN = str(os.getenv('AWS_S3_CUSTOM_DOMAIN'))
AWS_S3_OBJECT_PARAMETERS = {
    'CacheControl': 'max-age=86400',
}

STATIC_LOCATION = 'static'

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'core/static'),
]

STATIC_URL = f'{AWS_S3_CUSTOM_DOMAIN}/{STATIC_LOCATION}/'
MEDIA_LOCATION = 'media'
MEDIA_URL = f'{AWS_S3_CUSTOM_DOMAIN}/{MEDIA_LOCATION}/'

STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        "OPTIONS": {"location": MEDIA_LOCATION},
    },
    "staticfiles": {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        "OPTIONS": {"location": STATIC_LOCATION},
    },
}


# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

MESSAGE_TAGS = {
    messages.DEBUG: 'primary',
    messages.ERROR: 'danger',
    messages.SUCCESS: 'success',
    messages.INFO: 'info',
    messages.WARNING: 'warning',
}

ROLEPERMISSIONS_MODULE = 'core.roles'
KEYCLOAK_PERMISSIONS_METHOD = 'role'

# E-mail
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = str(os.getenv('EMAIL_HOST'))
EMAIL_PORT = 587
EMAIL_HOST_USER = str(os.getenv('EMAIL_HOST_USER'))
EMAIL_HOST_PASSWORD = str(os.getenv('EMAIL_HOST_PASSWORD'))
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False
DEFAULT_FROM_EMAIL = str(os.getenv('DEFAULT_FROM_EMAIL'))


# LOGGING
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {name} {module} {funcName}: {message}',
            'style': '{',
        },
        'simple': {
            'format': '[{levelname}] {asctime}: {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
            'stream': 'ext://sys.stdout',
        },
        'file_django': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs/django.log'),
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'file_celery': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs/celery.log'),
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'file_api': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs/api_calls.log'),
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'file_performance': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs/performance.log'),
            'maxBytes': 10485760,  # 10MB
            'backupCount': 3,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file_django'],
            'level': 'INFO',
            'propagate': False,
        },
        'celery': {
            'handlers': ['console', 'file_celery'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps.sims.tasks': {
            'handlers': ['console', 'file_celery', 'file_performance'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps.orders.tasks': {
            'handlers': ['console', 'file_celery', 'file_performance'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps.voice_calls.tasks': {
            'handlers': ['console', 'file_celery', 'file_performance'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps.sims.classes': {
            'handlers': ['console', 'file_api'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps.sims.views': {
            'handlers': ['console', 'file_django'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps.sims.views.views': {
            'handlers': ['console', 'file_django'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps.orders.classes': {
            'handlers': ['console', 'file_api'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}


# CELERY

CELERY_BROKER_URL = str(os.getenv('CELERY_BROKER_URL'))
CELERY_RESULT_BACKEND = str(os.getenv('CELERY_RESULT_BACKEND'))

CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
CELERY_BEAT_SYNC_EVERY = None

CELERY_TIMEZONE = TIME_ZONE

CELERY_BEAT_SCHEDULE = {
    'task__2_min_orders_auto': {
        'task': 'apps.orders.tasks.orders_auto',
        'schedule': crontab(minute='*/2'),
    },
    'task__2_min_activate_TC': {
        'task': 'apps.sims.tasks.simActivateTC',
        'schedule': crontab(minute='2-59/2'),
    },
    'task__2_min_activate_TM': {
        'task': 'apps.sims.tasks.simActivateTM',
        'schedule': crontab(minute='3-59/2'),
    },
    'task__deactivate_TC': {
        'task': 'apps.sims.tasks.simDeactivateTC',
        'schedule': crontab( hour=00, minute=00),
    },
    'task__deactivate_all': {
        'task': 'apps.sims.tasks.simDeactivateAll',
        'schedule': crontab( hour=00, minute=00),
    },
    'task__2_min_activate_CM': {
        'task': 'apps.sims.tasks.simActivateCM',
        'schedule': crontab(minute='4-59/2'),
    },
    'task__2_min_activate_CMHK': {
        'task': 'apps.sims.tasks.simActivateCMHK',
        'schedule': crontab(minute='3-59/2'),
    },
    'task__2_min_simActivateSM': {
        'task': 'apps.sims.tasks.simActivateSM',
        'schedule': crontab(minute='2-59/2'),
    }, # Orange e AT&T
    'task__2_min_simAgdOperator': {
        'task': 'apps.sims.tasks.simAgdOperator',
        'schedule': crontab(minute='2-59/2'),
    },
    'task__2_min_activate_VC': {
        'task': 'apps.voice_calls.tasks.voiceActivate',
        'schedule': crontab(minute='2-59/2'),
    },
    'task__deactivate_VC': {
        'task': 'apps.voice_calls.tasks.voiceDesactivate',
        'schedule': crontab( hour=00, minute=00),
    },
}


REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',  # Requer autenticação por padrão
    ),
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),  # Tempo de validade do token de acesso
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),    # Tempo de validade do token de refresh
    'AUTH_HEADER_TYPES': ('Bearer',),
}


# API TELCON
APITC_USERNAME = str(os.getenv('APITC_USERNAME'))
APITC_PASSWORD = str(os.getenv('APITC_PASSWORD'))
APITC_HTTPCONN = str(os.getenv('APITC_HTTPCONN'))

# API CM
APICM_KEY = str(os.getenv('APICM_KEY'))
APICM_SECRET = str(os.getenv('APICM_SECRET'))
APICM_URL = str(os.getenv('APICM_URL'))

# API CMHK
APICMHK_KEY = str(os.getenv('APICMHK_KEY'))
APICMHK_SECRET = str(os.getenv('APICMHK_SECRET'))
APICMHK_URL = str(os.getenv('APICMHK_URL'))

# API TM
APITM_TOKEN = str(os.getenv('APITM_TOKEN'))
APITM_URL = str(os.getenv('APITM_URL'))

# API MS
APISM_TOKEN = str(os.getenv('APISM_TOKEN'))
APISM_URL = str(os.getenv('APISM_URL'))

# API VOICE CALLS
APIVC_KEY = str(os.getenv('APIVC_KEY'))
APIVC_URL = str(os.getenv('APIVC_URL'))

LINK_ESIM_ANDROID = str(os.getenv('LINK_ESIM_ANDROID'))
LINK_ESIM_IOS = str(os.getenv('LINK_ESIM_IOS'))

