Visão Geral do Sistema
======================

O **SISACDC** é uma aplicação Django 5.0 para gerenciar o ciclo de vida completo de pedidos internacionais de telecomunicações — desde a importação do e-commerce (WooCommerce) até a ativação junto às operadoras internacionais.

Funcionalidades Principais
--------------------------

- **Importação automática de pedidos** via API WooCommerce (tarefa Celery periódica).
- **Ativação de cartões SIM físicos e eSIMs** em 5 operadoras: TelCom, Telcom IMSI, T-Mobile, China Mobile e MoviStar.
- **Gerenciamento de planos de voz** (chamadas internacionais).
- **Notificações por e-mail** automáticas para clientes após ativação.
- **Dashboard** com estatísticas de ativações, pedidos pendentes e status operadoras.

Stack Tecnológico
-----------------

+----------------------+-------------------------------------------+
| Componente           | Tecnologia                                |
+======================+===========================================+
| Backend              | Django 5.0 + Django REST Framework        |
+----------------------+-------------------------------------------+
| Processamento Async  | Celery + Celery Beat + Redis              |
+----------------------+-------------------------------------------+
| Banco de Dados       | PostgreSQL                                |
+----------------------+-------------------------------------------+
| Armazenamento        | AWS S3 + CloudFront (CDN)                 |
+----------------------+-------------------------------------------+
| Autenticação         | JWT (simplejwt) + Roles (role-permissions)|
+----------------------+-------------------------------------------+
| Admin                | Django Admin + Jazzmin                    |
+----------------------+-------------------------------------------+
| Cache / Broker       | Redis 7.x                                 |
+----------------------+-------------------------------------------+

Fluxo Geral do Sistema
-----------------------

.. code-block:: text

   ┌──────────────────────────────────────────────────────────────┐
   │                    E-COMMERCE (WooCommerce)                   │
   └───────────────────────────┬──────────────────────────────────┘
                               │ API REST (wc/v3)
                               ▼
   ┌──────────────────────────────────────────────────────────────┐
   │              order_import()  [Celery, 2 min]                  │
   │  • Busca pedidos com status "processing"                      │
   │  • Valida e persiste em Orders DB                             │
   │  • Define tipo de SIM e produto                               │
   └───────────────────────────┬──────────────────────────────────┘
                               │
               ┌───────────────┴───────────────┐
               ▼                               ▼
   ┌───────────────────────┐     ┌─────────────────────────┐
   │  sims_in_orders()      │     │  number_in_voice()       │
   │  Atribuir SIM (AS→AA)  │     │  Atribuir número de voz  │
   └───────────┬───────────┘     └────────────┬────────────┘
               │                              │
               ▼                              ▼
   ┌─────────────────────────────────────────────────────────────┐
   │   simActivateTC / simActivateTI / simActivateCM /            │
   │   simActivateTM / simActivateMS  [Celery, a cada 2-4 min]   │
   │   • Chama API da operadora correspondente                    │
   │   • Atualiza status para AT (Ativado)                        │
   └──────────────────────────┬──────────────────────────────────┘
                              │
                              ▼
   ┌─────────────────────────────────────────────────────────────┐
   │  send_email_sims()  [Celery, após ativação]                  │
   │  • Envia e-mail HTML para o cliente                          │
   │  • Inclui QR Code do eSIM quando aplicável                   │
   └─────────────────────────────────────────────────────────────┘

Operadoras Suportadas
---------------------

+---------------+---------+----------------------------------------------+
| Operadora     | Código  | Produtos Suportados                          |
+===============+=========+==============================================+
| TelCom        | TC      | EUA/CAN/MEX, América do Sul, Israel, etc.    |
+---------------+---------+----------------------------------------------+
| Telcom IMSI   | TI      | Planos variados (IMSI alternativo)           |
+---------------+---------+----------------------------------------------+
| T-Mobile      | TM      | EUA Ilimitado (SIM Físico)                   |
+---------------+---------+----------------------------------------------+
| China Mobile  | CM      | Global, EUA/CAN/MEX (reutilização)           |
+---------------+---------+----------------------------------------------+
| MoviStar      | MS      | Planos regionais                             |
+---------------+---------+----------------------------------------------+
| Orange        | OR      | Europa                                       |
+---------------+---------+----------------------------------------------+
