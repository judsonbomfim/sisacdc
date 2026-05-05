App: Sims — Cartões SIM
=======================

Gerencia o inventário de SIMs físicos e eSIMs e a integração com as APIs das operadoras para ativação e desativação.

.. contents:: Conteúdo
   :local:
   :depth: 2

Visão Geral
-----------

O app ``sims`` é responsável por:

1. **Inventário**: cadastro de SIMs físicos e eSIMs por operadora.
2. **Atribuição**: seleção do SIM disponível adequado para cada pedido.
3. **Ativação**: chamadas às APIs das operadoras para ativar SIMs.
4. **Desativação**: desativação automática (daily task) de SIMs com data expirada.
5. **QR Code**: geração e extração de QR codes para eSIMs.

Fluxo de Ativação
-----------------

.. code-block:: text

   Orders (status=AA) ──► simActivate*() [Celery]
                               │
                       ┌───────┴────────┐
                       │ Chamar API     │
                       │ da operadora   │
                       └───────┬────────┘
                               │
                    ┌──────────┴───────────┐
                    │ Sucesso              │ Falha
                    ▼                      ▼
             status = AT           status = EA
             (Ativado)         (Erro Ativação)
                    │
                    ▼
             status = EE
          (Enviar E-mail)

Cache de Tokens
---------------

Tokens de autenticação das APIs são cacheados no Redis por **540 segundos**:

.. code-block:: python

   # Exemplo: ApiTC
   token = cache.get('api_tc_token')
   if not token:
       token = _fetch_from_api()
       cache.set('api_tc_token', token, timeout=540)

Chaves de cache:

- ``api_tc_token`` — TelCom
- ``api_ti_token`` — TelCom IMSI
- ``api_cm_token`` — China Mobile
- ``api_tm_token`` — T-Mobile

Models
------

.. automodule:: apps.sims.models
   :members:
   :undoc-members:
   :show-inheritance:

Classes de Integração com Operadoras
--------------------------------------

.. automodule:: apps.sims.classes
   :members:
   :undoc-members:
   :show-inheritance:

Tarefas Celery
--------------

.. automodule:: apps.sims.tasks
   :members:
   :undoc-members:

Views
-----

.. automodule:: apps.sims.views
   :members:
   :undoc-members:

Serializers (API REST)
----------------------

.. automodule:: apps.sims.serializers
   :members:
   :undoc-members:
   :show-inheritance:
