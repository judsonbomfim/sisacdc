#!/usr/bin/env python
"""
Script para fazer upload da documentação Sphinx gerada para o AWS S3.

Uso:
    python scripts/upload_docs_s3.py

Requer as variáveis de ambiente do .env configuradas:
    AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_STORAGE_BUCKET_NAME
"""

import os
import sys
import mimetypes
from pathlib import Path

# Adicionar raiz do projeto ao path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Carregar .env
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / '.env')
except ImportError:
    pass

import boto3
from botocore.exceptions import ClientError

DOCS_BUILD_DIR = BASE_DIR / 'docs' / 'build' / 'html'
S3_PREFIX = 'docs'  # pasta dentro do bucket: s3://bucket/docs/

AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME')


def upload_docs():
    if not DOCS_BUILD_DIR.exists():
        print(f"Erro: pasta {DOCS_BUILD_DIR} não encontrada. Rode 'make html' primeiro.")
        sys.exit(1)

    s3 = boto3.client(
        's3',
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    )

    files = list(DOCS_BUILD_DIR.rglob('*'))
    total = len([f for f in files if f.is_file()])
    uploaded = 0

    for file_path in files:
        if not file_path.is_file():
            continue

        relative = file_path.relative_to(DOCS_BUILD_DIR)
        s3_key = f"{S3_PREFIX}/{relative.as_posix()}"

        content_type, _ = mimetypes.guess_type(str(file_path))
        content_type = content_type or 'application/octet-stream'

        try:
            # Assets estáticos (_static/, _sources/) são públicos via CloudFront
            is_static = relative.parts[0] in ('_static', '_sources')
            extra_args = {
                'ContentType': content_type,
                'CacheControl': 'public, max-age=86400' if is_static else 'no-cache',
            }
            s3.upload_file(
                str(file_path),
                AWS_STORAGE_BUCKET_NAME,
                s3_key,
                ExtraArgs=extra_args,
            )
            uploaded += 1
            print(f"[{uploaded}/{total}] {s3_key}")
        except ClientError as e:
            print(f"Erro ao enviar {s3_key}: {e}")
            sys.exit(1)

    print(f"\nConcluído: {uploaded} arquivos enviados para s3://{AWS_STORAGE_BUCKET_NAME}/{S3_PREFIX}/")

    # Limpar cache Redis para forçar recarga dos novos arquivos
    try:
        import django
        from django.conf import settings as django_settings
        if not django_settings.configured:
            django_settings.configure(
                CACHES={'default': {'BACKEND': 'django.core.cache.backends.redis.RedisCache', 'LOCATION': os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')}},
                SECRET_KEY='x',
            )
        from django.core.cache import cache
        keys_deleted = 0
        # Deletar apenas as chaves de docs (prefixo docs_file_)
        if hasattr(cache, 'delete_pattern'):
            keys_deleted = cache.delete_pattern('docs_file_*')
        else:
            cache.clear()
        print(f"Cache Redis limpo ({keys_deleted} chaves removidas).")
    except Exception as e:
        print(f"Aviso: não foi possível limpar o cache Redis: {e}")


if __name__ == '__main__':
    upload_docs()
