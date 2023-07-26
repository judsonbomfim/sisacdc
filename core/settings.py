from pathlib import Path
import os
from django.contrib.messages import constants
from woocommerce import API
from dotenv import load_dotenv
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = str(os.getenv('SECRET_KEY'))

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'apps.orders.apps.OrdersConfig',
    'apps.sims.apps.SimsConfig',
    'apps.dashboard.apps.DashboardConfig',
    'storages',
]

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
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql_psycopg2',
#         'NAME': 'mydjango',
#         'USER': 'mydjangouser',
#         'PASSWORD': 'QeScczGvKcJE',
#         'HOST': 'localhost',
#         'PORT': '',
#     }
# }

DATABASES = {
    "default": {
        "ENGINE": str(os.getenv('DB_ENGINE')),
        "NAME": str(os.getenv('DB_NAME')),
        "USER": str(os.getenv('DB_USER')),
        "PASSWORD": str(os.getenv('DB_PASSWORD')),
        "HOST": str(os.getenv('DB_HOST')),
        "PORT": str(os.getenv('DB_PORT')),
    }
}


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
DATE_INPUT_FORMATS = ('%d-%m-%Y')
USE_I18N = True
USE_L10N = True
USE_TZ = True


# Moving static assets to DigitalOcean Spaces as per:
# https://www.digitalocean.com/community/tutorials/how-to-set-up-object-storage-with-django
AWS_ACCESS_KEY_ID = str(os.getenv('AWS_ACCESS_KEY_ID'))
AWS_SECRET_ACCESS_KEY = str(os.getenv('AWS_SECRET_ACCESS_KEY'))
AWS_STORAGE_BUCKET_NAME = str(os.getenv('AWS_STORAGE_BUCKET_NAME'))
AWS_S3_ENDPOINT_URL = 'https://nyc3.digitaloceanspaces.com'
AWS_S3_CUSTOM_DOMAIN = 'sisacdc-teste.nyc3.cdn.digitaloceanspaces.com'
AWS_S3_OBJECT_PARAMETERS = {
    'CacheControl': 'max-age=86400',
}
AWS_LOCATION = 'static'
AWS_LOCATION_M = 'media'
AWS_DEFAULT_ACL = 'public-read'

STATICFILES_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'core/static')
]

STATIC_URL = '{}/{}/'.format(AWS_S3_CUSTOM_DOMAIN, AWS_LOCATION)
STATIC_ROOT = os.path.join(BASE_DIR, 'static')


MEDIA_URL = '{}/{}/'.format(AWS_S3_CUSTOM_DOMAIN, AWS_LOCATION_M)
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')


# Default primary key field type
# https://docs.djangoproject.com/en/4.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

MESSAGE_TAGS = {
    constants.DEBUG: 'primary',
    constants.ERROR: 'danger',
    constants.SUCCESS: 'success',
    constants.INFO: 'info',
    constants.WARNING: 'warning',
}