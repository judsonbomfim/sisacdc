import os
import sys
from unittest.mock import MagicMock

# Adicionar raiz do projeto ao path
sys.path.insert(0, os.path.abspath('../..'))

# ─────────────────────────────────────────────
# Mock de módulos com dependências externas
# (deve vir ANTES de qualquer import do projeto)
# ─────────────────────────────────────────────
MOCK_MODULES = [
    'cv2', 'numpy',
    'pandas',
    'qrcode', 'qrcode.constants',
    'woocommerce',
    'celery', 'celery.schedules',
    'django_celery_beat', 'django_celery_beat.schedulers',
    'rolepermissions', 'rolepermissions.roles', 'rolepermissions.decorators',
    'boto3',
    'storages', 'storages.backends', 'storages.backends.s3boto3',
    'redis',
    'PIL', 'PIL.Image',
]
for mod_name in MOCK_MODULES:
    sys.modules[mod_name] = MagicMock()

# ─────────────────────────────────────────────
# Variáveis de ambiente (não são Django settings)
# necessárias para classes que usam os.getenv()
# ─────────────────────────────────────────────
_env_vars = {
    'url_site': 'https://example.com',
    'consumer_key': 'dummy',
    'consumer_secret': 'dummy',
}
for k, v in _env_vars.items():
    os.environ.setdefault(k, v)

# ─────────────────────────────────────────────
# Configurar Django com SQLite em memória
# Usando settings.configure() para evitar conflito
# com módulos mockados no INSTALLED_APPS real
# ─────────────────────────────────────────────
import django
from django.conf import settings

if not settings.configured:
    settings.configure(
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': ':memory:',
            }
        },
        INSTALLED_APPS=[
            'django.contrib.contenttypes',
            'django.contrib.auth',
            'django.contrib.sessions',
            'rest_framework',
            'apps.orders.apps.OrdersConfig',
            'apps.sims.apps.SimsConfig',
            'apps.users.apps.UsersConfig',
            'apps.send_email.apps.SendEmailConfig',
            'apps.voice_calls.apps.VoiceCallsConfig',
            'apps.dashboard.apps.DashboardConfig',
        ],
        SECRET_KEY='sphinx-doc-build-only-not-real-secret-key-for-docs',
        USE_TZ=False,
        DEFAULT_AUTO_FIELD='django.db.models.AutoField',
        CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}},
        STATIC_URL='/static/',
        MEDIA_URL='/media/',
        TIME_ZONE='America/Sao_Paulo',
        LANGUAGE_CODE='pt-br',
        # AWS S3
        AWS_ACCESS_KEY_ID='dummy',
        AWS_SECRET_ACCESS_KEY='dummy',
        AWS_STORAGE_BUCKET_NAME='dummy',
        AWS_S3_CUSTOM_DOMAIN='dummy.cloudfront.net',
        URL_CDN='dummy.cloudfront.net',
        # APIs de operadoras
        APITC_USERNAME='dummy',
        APITC_PASSWORD='dummy',
        APITC_HTTPCONN='dummy',
        APICM_KEY='dummy',
        APICM_SECRET='dummy',
        APICM_URL='dummy',
        APITM_TOKEN='dummy',
        APITM_URL='dummy',
        APISM_TOKEN='dummy',
        APISM_URL='dummy',
        APIVC_KEY='dummy',
        APIVC_URL='dummy',
        # eSIM links
        LINK_ESIM_ANDROID='https://dummy',
        LINK_ESIM_IOS='https://dummy',
        # JWT e REST Framework
        SIMPLE_JWT={
            'ACCESS_TOKEN_LIFETIME': None,
            'REFRESH_TOKEN_LIFETIME': None,
            'AUTH_HEADER_TYPES': ('Bearer',),
        },
        REST_FRAMEWORK={},
        CELERY_BROKER_URL='redis://localhost:6379/0',
        TEMPLATES=[{
            'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'DIRS': [],
            'APP_DIRS': False,
            'OPTIONS': {'context_processors': []},
        }],
    )

try:
    django.setup()
except Exception as e:
    print(f"[conf.py] django.setup() warning: {e}")


# ─────────────────────────────────────────────
# Informações do projeto
# ─────────────────────────────────────────────
project = 'SISACDC'
copyright = '2025, SISACDC'
author = 'SISACDC'
release = '1.0'

# ─────────────────────────────────────────────
# Extensões Sphinx
# ─────────────────────────────────────────────
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'sphinx.ext.todo',
    'sphinx.ext.intersphinx',
    'sphinx.ext.autosummary',
]

# Autodoc: mostrar membros por padrão
autodoc_default_options = {
    'members': True,
    'undoc-members': True,
    'show-inheritance': True,
    'special-members': '__str__, __repr__',
}

# Napoleon: suporte a Google/NumPy style docstrings
napoleon_google_docstring = True
napoleon_numpy_docstring = True

# Todo
todo_include_todos = True

# Intersphinx: link para docs do Django e Python
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'django': ('https://docs.djangoproject.com/en/5.0/', 'https://docs.djangoproject.com/en/5.0/_objects/'),
}

# Templates e estáticos
templates_path = ['_templates']
exclude_patterns = []

# ─────────────────────────────────────────────
# HTML: tema Read The Docs
# ─────────────────────────────────────────────
html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
html_theme_options = {
    'navigation_depth': 4,
    'collapse_navigation': False,
    'sticky_navigation': True,
    'includehidden': True,
    'titles_only': False,
}

# Idioma
language = 'pt_BR'
