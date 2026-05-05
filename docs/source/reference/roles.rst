Roles e Permissões
===================

O sistema usa ``django-role-permissions`` para controle de acesso baseado em roles (RBAC).

Roles Disponíveis
-----------------

Atendente
^^^^^^^^^

Acesso operacional básico para atendimento de pedidos.

.. list-table:: Permissões — Atendente
   :header-rows: 1
   :widths: 40 60

   * - Permissão
     - Descrição
   * - ``view_orders``
     - Visualizar lista e detalhe de pedidos
   * - ``edit_orders``
     - Editar status e informações de pedidos
   * - ``send_esims_but``
     - Botão de reenvio de e-mail de eSIM
   * - ``view_voice``
     - Visualizar planos de voz
   * - ``actions_voice``
     - Executar ações nos planos de voz

Gerente
^^^^^^^

Acesso completo ao sistema, incluindo configuração e importação.

.. list-table:: Permissões — Gerente
   :header-rows: 1
   :widths: 40 60

   * - Permissão
     - Descrição
   * - ``view_statistics``
     - Ver estatísticas e dashboard completo
   * - ``view_orders``
     - Visualizar pedidos
   * - ``edit_orders``
     - Editar pedidos
   * - ``import_orders``
     - Acionar importação manual de pedidos
   * - ``view_sims``
     - Visualizar inventário de SIMs
   * - ``add_sims``
     - Adicionar SIMs físicos ao inventário
   * - ``add_esims``
     - Adicionar eSIMs ao inventário
   * - ``edit_sims``
     - Editar SIMs cadastrados
   * - ``add_ord_sims``
     - Atribuir SIM manualmente a um pedido
   * - ``send_esims``
     - Enviar eSIM por e-mail
   * - ``send_esims_but``
     - Botão de reenvio de e-mail de eSIM
   * - ``list_activations``
     - Ver lista completa de ativações
   * - ``export_activations``
     - Exportar relatório de ativações
   * - ``view_voice``
     - Visualizar planos de voz
   * - ``edit_voice``
     - Editar planos de voz
   * - ``import_voice``
     - Importar números de voz
   * - ``actions_voice``
     - Executar ações nos planos de voz
   * - ``list_number``
     - Listar números de voz disponíveis

Como Usar nas Views
--------------------

.. code-block:: python

   from rolepermissions.decorators import has_permission_decorator

   @login_required(login_url='/login/')
   @has_permission_decorator('view_orders')
   def orders_list(request):
       ...

Como Atribuir Role a um Usuário
--------------------------------

.. code-block:: python

   from rolepermissions.roles import assign_role
   from django.contrib.auth.models import User

   user = User.objects.get(username='joao')
   assign_role(user, 'gerente')     # Gerente
   assign_role(user, 'atendente')   # Atendente
