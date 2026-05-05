App: Orders — Pedidos
=====================

Responsável pelo ciclo de vida completo dos pedidos importados do e-commerce.

.. contents:: Conteúdo
   :local:
   :depth: 2

Visão Geral
-----------

O app ``orders`` gerencia:

1. **Importação** de pedidos via API WooCommerce (tarefa periódica).
2. **Rastreamento de status** — pedidos transitam por até 25 estados.
3. **Sincronização bidirecional** com a loja (atualiza status e metadados do item).
4. **Notas internas** associadas a cada pedido.

Ciclo de Status
---------------

.. code-block:: text

   PR (Processando)
      │
      ├──► AS (Atribuir SIM) ──► AA (Agd. Ativação) ──► AT (Ativado) ──► EE (Enviar E-mail) ──► CN (Concluído)
      │                                                    │
      │                                                    └──► DE (Desativado) ──► ED (Erro Desativação)
      │
      ├──► AE (Agd. Envio) ──► ES (Em Separação) ──► RT (Retirada) / MB (Motoboy) / AG (Agência)
      │
      ├──► PV (Plano de Voz)
      │
      ├──► EA (Erro Ativação) ──► RP (Reprocessar) ──► AS ...
      │
      └──► CC (Cancelado) / RE (Reembolsar) ──► RB (Reembolsado) / RC (Reembolso Parcial)

Models
------

.. automodule:: apps.orders.models
   :members:
   :undoc-members:
   :show-inheritance:

Classes de Integração
---------------------

.. automodule:: apps.orders.classes
   :members:
   :undoc-members:
   :show-inheritance:

Tarefas Celery
--------------

.. automodule:: apps.orders.tasks
   :members:
   :undoc-members:

Views
-----

.. automodule:: apps.orders.views
   :members:
   :undoc-members:
