Agenda Celery Beat
==================

Todas as tarefas periódicas são gerenciadas pelo ``django-celery-beat`` com ``DatabaseScheduler``.
A agenda é persistida no banco de dados e pode ser gerenciada via Django Admin (``/admin/``) ou programaticamente.

Tarefas Registradas
-------------------

.. list-table::
   :header-rows: 1
   :widths: 30 20 25 25

   * - Chave (settings)
     - Tarefa
     - Frequência
     - Observação
   * - ``task__2_min_orders_auto``
     - ``orders_auto``
     - A cada 2 min
     - Importa pedidos + atribui SIMs
   * - ``task__2_min_activate_TC``
     - ``simActivateTC``
     - A cada 2 min (min. pares)
     - Ativa SIMs TelCom
   * - ``task__2_min_activate_TI``
     - ``simActivateTI``
     - A cada 2 min (min. pares)
     - Ativa SIMs TelCom IMSI
   * - ``task__2_min_activate_TM``
     - ``simActivateTM``
     - A cada 2 min (min. ímpares)
     - Ativa SIMs T-Mobile
   * - ``task__2_min_activate_CM``
     - ``simActivateCM``
     - A cada 2 min (min. ≥ 4)
     - Ativa SIMs China Mobile
   * - ``task__deactivate_TC``
     - ``simDeactivateTC``
     - Diariamente 00:00
     - Desativa SIMs TelCom expirados
   * - ``task__deactivate_all``
     - ``simDeactivateAll``
     - Diariamente 00:00
     - Desativa todos os SIMs expirados

Limites de Tempo
----------------

Tarefas de ativação em massa possuem limites para evitar travamento de workers:

.. code-block:: python

   @shared_task(time_limit=300, soft_time_limit=240)
   def simActivateTC():
       ...

+---------------------------+---------------------+-------------------+
| Tarefa                    | ``soft_time_limit`` | ``time_limit``    |
+===========================+=====================+===================+
| ``order_import``          | 100s                | 110s              |
+---------------------------+---------------------+-------------------+
| ``sims_in_orders``        | 240s                | 300s              |
+---------------------------+---------------------+-------------------+
| ``simActivateTC``         | 240s                | 300s              |
+---------------------------+---------------------+-------------------+
| ``simActivateTI``         | 240s                | 300s              |
+---------------------------+---------------------+-------------------+
| ``simActivateTM``         | 240s                | 300s              |
+---------------------------+---------------------+-------------------+
| ``simActivateCM``         | 240s                | 300s              |
+---------------------------+---------------------+-------------------+

Verificar Tarefas em Execução
------------------------------

.. code-block:: bash

   # Verificar fila de tarefas
   redis-cli KEYS "*celery*"
   redis-cli LRANGE celery 0 10

   # Logs de worker em tempo real
   celery -A core worker --loglevel=debug

   # Verificar tarefas agendadas no banco
   python manage.py shell -c "
   from django_celery_beat.models import PeriodicTask
   for t in PeriodicTask.objects.all():
       print(t.name, t.enabled)
   "
