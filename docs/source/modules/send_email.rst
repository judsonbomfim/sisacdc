App: Send Email — Notificações por E-mail
==========================================

Envia notificações HTML por e-mail aos clientes após ativação ou desativação de SIM/Voz.

.. contents:: Conteúdo
   :local:
   :depth: 2

Visão Geral
-----------

O envio é **assíncrono** via Celery — a tarefa é enfileirada e não bloqueia o processamento principal.

Fluxo de envio:

.. code-block:: text

   Order (status=EE) ──► send_email_sims() [Celery]
                               │
                       ┌───────┴────────┐
                       │  Renderizar    │
                       │  template HTML │
                       └───────┬────────┘
                               │
                       ┌───────┴────────┐
                       │  Enviar via    │
                       │  SMTP          │
                       └───────┬────────┘
                               │
                       Order status = CN (Concluído)

Templates
---------

Localizados em ``templates/painel/emails/``:

- ``email_ativacao.html`` — e-mail padrão de ativação de SIM
- ``email_desativacao.html`` — e-mail de desativação

Tarefas Celery
--------------

.. automodule:: apps.send_email.tasks
   :members:
   :undoc-members:

Views
-----

.. automodule:: apps.send_email.views
   :members:
   :undoc-members:
