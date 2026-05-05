Configuração e Execução
=======================

Pré-requisitos
--------------

- Python 3.11+
- PostgreSQL 14+
- Redis 7.x
- Docker e Docker Compose (recomendado)

Variáveis de Ambiente
---------------------

Copie o arquivo de exemplo e preencha com suas credenciais:

.. code-block:: bash

   cp .env.example .env

Variáveis obrigatórias em ``.env``:

.. code-block:: ini

   # Django
   SECRET_KEY=sua-chave-secreta
   DEBUG=False
   ALLOWED_HOSTS=localhost,meudominio.com

   # Banco de dados PostgreSQL
   DB_NAME=sisacdc
   DB_USER=usuario
   DB_PASSWORD=senha
   DB_HOST=localhost
   DB_PORT=5432

   # Redis (broker Celery + cache)
   CELERY_BROKER_URL=redis://localhost:6379/0

   # WooCommerce (API Store)
   url_site=https://meusite.com
   consumer_key=ck_xxxxx
   consumer_secret=cs_xxxxx

   # AWS S3
   AWS_ACCESS_KEY_ID=xxxxx
   AWS_SECRET_ACCESS_KEY=xxxxx
   AWS_STORAGE_BUCKET_NAME=meu-bucket
   AWS_S3_CUSTOM_DOMAIN=cdn.meusite.com

   # E-mail SMTP
   EMAIL_HOST=smtp.gmail.com
   EMAIL_PORT=587
   EMAIL_HOST_USER=email@dominio.com
   EMAIL_HOST_PASSWORD=senha

   # APIs de Operadoras
   APITC_USERNAME=usuario_telcom
   APITC_PASSWORD=senha_telcom
   APITC_HTTPCONN=api.telcom.com

Execução via Docker (Recomendado)
----------------------------------

.. code-block:: bash

   docker-compose up

O ``docker-compose.yml`` sobe os serviços:

- **web**: Django + Gunicorn
- **worker**: Celery Worker
- **beat**: Celery Beat (agendador)
- **redis**: Redis 7.x (broker + cache)

Execução Manual (Desenvolvimento)
-----------------------------------

.. code-block:: bash

   # 1. Ativar ambiente virtual
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt

   # 2. Aplicar migrações
   python manage.py migrate

   # 3. Criar superusuário
   python manage.py createsuperuser

   # 4. Iniciar servidor de desenvolvimento
   python manage.py runserver

   # 5. Em terminais separados:
   redis-server
   celery -A core worker -B --loglevel=info

Comandos Úteis
--------------

.. code-block:: bash

   # Aplicar migrações
   python manage.py migrate

   # Gerar novas migrações após alterar models
   python manage.py makemigrations

   # Shell interativo Django
   python manage.py shell

   # Executar testes
   python manage.py test

   # Limpar cache Redis (emergência)
   python manage.py shell -c "from django.core.cache import cache; cache.clear()"

   # Verificar tarefas Celery na fila
   redis-cli KEYS "*celery*"
