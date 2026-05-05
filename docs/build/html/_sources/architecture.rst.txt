Arquitetura
===========

Estrutura de Apps Django
-------------------------

O projeto segue o padrão de apps Django, com 6 apps sob o diretório ``apps/``:

.. code-block:: text

   sisacdc/
   ├── apps/
   │   ├── orders/         → Ciclo de vida dos pedidos
   │   ├── sims/           → Inventário e ativação de SIMs
   │   ├── users/          → Autenticação e controle de acesso
   │   ├── send_email/     → Notificações por e-mail
   │   ├── voice_calls/    → Planos de chamadas de voz
   │   └── dashboard/      → Análise e monitoramento
   ├── core/
   │   ├── settings.py     → Configurações globais
   │   ├── celery.py       → Configuração Celery
   │   ├── roles.py        → Definição de roles/permissões
   │   └── urls.py         → Roteamento principal
   └── templates/
       └── painel/         → Templates HTML

Diagrama de Dependências entre Apps
-------------------------------------

.. code-block:: text

   orders ──────────────► sims
      │                    │
      │                    ▼
      │              send_email
      │
      └──────────────► voice_calls
                          │
                          ▼
                      send_email

   dashboard ─── lê ──► orders, sims, voice_calls

Integração com Serviços Externos
----------------------------------

.. code-block:: text

   ┌─────────────────────────────────────────────────────────────┐
   │                      SISACDC                                 │
   │                                                             │
   │  ┌──────────┐   ┌──────────┐   ┌─────────────────────┐    │
   │  │  Django  │   │  Celery  │   │       Redis          │    │
   │  │  + DRF   │   │  Worker  │   │  (broker + cache)    │    │
   │  └────┬─────┘   └────┬─────┘   └─────────────────────┘    │
   │       │              │                                      │
   └───────┼──────────────┼──────────────────────────────────────┘
           │              │
     ┌─────┴──────────────┴──────────────────────────┐
     │              APIs Externas                     │
     ├────────────────────────────────────────────────┤
     │  WooCommerce API  → importação de pedidos       │
     │  TelCom API       → ativação SIM TC/TI          │
     │  T-Mobile API     → ativação SIM TM             │
     │  China Mobile API → ativação SIM CM             │
     │  MoviStar API     → ativação SIM MS             │
     │  AWS S3 / CF      → arquivos estáticos e mídia  │
     │  SMTP             → envio de e-mails            │
     └────────────────────────────────────────────────┘

Agenda Celery Beat
------------------

Todas as tarefas periódicas usam ``DatabaseScheduler`` — a agenda é persistida no banco de dados via ``django-celery-beat``.

+-------------------------------+----------------------------------+--------------------------------+
| Tarefa                        | Frequência                       | Função                         |
+===============================+==================================+================================+
| ``order_import``              | A cada 2 minutos                 | Importa pedidos do e-commerce  |
+-------------------------------+----------------------------------+--------------------------------+
| ``sims_in_orders``            | A cada 2 minutos                 | Atribui SIMs aos pedidos       |
+-------------------------------+----------------------------------+--------------------------------+
| ``simActivateTC``             | A cada 2 min (min. pares)        | Ativa SIMs TelCom              |
+-------------------------------+----------------------------------+--------------------------------+
| ``simActivateTI``             | A cada 2 min (min. pares)        | Ativa SIMs TelCom IMSI         |
+-------------------------------+----------------------------------+--------------------------------+
| ``simActivateTM``             | A cada 2 min (min. ímpares)      | Ativa SIMs T-Mobile            |
+-------------------------------+----------------------------------+--------------------------------+
| ``simActivateCM``             | A cada 2 min (a partir do min 4) | Ativa SIMs China Mobile        |
+-------------------------------+----------------------------------+--------------------------------+
| ``simDeactivateTC``           | Diariamente às 00:00             | Desativa SIMs TelCom expirados |
+-------------------------------+----------------------------------+--------------------------------+
| ``simDeactivateAll``          | Diariamente às 00:00             | Desativa todos SIMs expirados  |
+-------------------------------+----------------------------------+--------------------------------+

Cache de Tokens de API
----------------------

Para evitar chamadas de autenticação repetidas (rate-limiting), os tokens de API são armazenados no Redis com timeout de **540 segundos (9 minutos)**:

.. code-block:: python

   token = cache.get('api_tc_token')
   if not token:
       token = ApiTC._fetch_new_token()
       cache.set('api_tc_token', token, timeout=540)

Banco de Dados
--------------

- **Engine**: PostgreSQL (obrigatório — sem suporte a SQLite em produção)
- **Migrações**: localizadas em ``apps/*/migrations/``
- **Fuso horário**: ``America/Sao_Paulo`` — datas armazenadas como naive (``USE_TZ = False``)
