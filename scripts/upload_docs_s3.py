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
            s3.upload_file(
                str(file_path),
                AWS_STORAGE_BUCKET_NAME,
                s3_key,
                ExtraArgs={
                    'ContentType': content_type,
                    'CacheControl': 'max-age=3600',
                    # Sem ACL 'public-read' — acesso só via URLs pré-assinadas
                },
            )
            uploaded += 1
            print(f"[{uploaded}/{total}] {s3_key}")
        except ClientError as e:
            print(f"Erro ao enviar {s3_key}: {e}")
            sys.exit(1)

    print(f"\nConcluído: {uploaded} arquivos enviados para s3://{AWS_STORAGE_BUCKET_NAME}/{S3_PREFIX}/")


if __name__ == '__main__':
    upload_docs()
