SISACDC — Documentação do Sistema
==================================

**SISACDC** é um sistema de gerenciamento de pedidos internacionais de telecomunicações desenvolvido com Django 5.0.
Gerencia a ativação de cartões SIM físicos e eSIMs junto a múltiplas operadoras internacionais, pedidos de planos de voz e notificações por e-mail.

.. toctree::
   :maxdepth: 2
   :caption: Visão Geral

   overview
   architecture
   setup

.. toctree::
   :maxdepth: 3
   :caption: Módulos do Sistema

   modules/orders
   modules/sims
   modules/voice_calls
   modules/send_email
   modules/dashboard
   modules/users
   modules/core

.. toctree::
   :maxdepth: 2
   :caption: Referência

   reference/status_codes
   reference/roles
   reference/celery_schedule

Índices e tabelas
=================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
