Agenda Celery Beat
==================

Todas as tarefas periódicas são gerenciadas pelo ``django-celery-beat`` com ``DatabaseScheduler``.
A agenda **canônica** vive em ``CELERY_BEAT_SCHEDULE`` em ``core/settings.py``.
No startup do serviço ``celery_beat``, o comando ``sync_celery_beat`` faz upsert dessas
entradas no banco e **remove PeriodicTask órfãs** (nomes que não estão no settings).

Operação anti-duplicata
-----------------------

1. **Alterar a agenda** = editar ``CELERY_BEAT_SCHEDULE`` no código e redeployar
   (ou reiniciar o container ``celery_beat``). Não criar PeriodicTask novas no Admin.
2. **Admin**: use apenas para enable/disable pontual de uma task já existente.
   Criar tasks manuais com outro nome gera disparos duplicados e serão apagadas
   no próximo ``sync_celery_beat``.
3. **Um único beat**: o compose fixa ``deploy.replicas: 1`` e
   ``container_name: celery_beat``. Nunca escale o serviço beat.
4. **Locks Redis**: as tasks periódicas usam ``core.celery_locks.periodic_task_lock``
   (chave ``celery:lock:<nome>``). Se a run anterior ainda estiver em andamento,
   a nova é ignorada com log ``Task ... skipped: lock held``.
   Chamadas pontuais com ``id`` definido não usam o lock.

Sincronizar manualmente::

   python manage.py sync_celery_beat

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
   * - ``task__2_min_simActivateSM``
     - ``simActivateSM``
     - A cada 2 min (min. pares)
     - Ativa SIMs Orange / AT&T
   * - ``task__2_min_simAgdOperator``
     - ``simAgdOperator``
     - A cada 2 min (min. pares)
     - Consulta status AT&T/Orange
   * - ``task__2_min_activate_VC``
     - ``voiceActivate``
     - A cada 2 min (min. pares)
     - Ativa planos de voz
   * - ``task__deactivate_TC``
     - ``simDeactivateTC``
     - Diariamente 00:00
     - Desativa SIMs TelCom expirados
   * - ``task__deactivate_all``
     - ``simDeactivateAll``
     - Diariamente 00:00
     - Desativa todos os SIMs expirados
   * - ``task__deactivate_VC``
     - ``voiceDesactivate``
     - Diariamente 00:00
     - Desativa planos de voz expirados

Limites de Tempo
----------------

Tarefas de ativação em massa possuem limites para evitar travamento de workers:

.. code-block:: python

   @shared_task(time_limit=110, soft_time_limit=100)
   @periodic_task_lock(timeout=140)
   def simActivateTC(id=None):
       ...

+---------------------------+---------------------+-------------------+----------+
| Tarefa                    | ``soft_time_limit`` | ``time_limit``    | lock TTL |
+===========================+=====================+===================+==========+
| ``orders_auto``           | 100s                | 110s              | 140s     |
+---------------------------+---------------------+-------------------+----------+
| ``simActivateTC``         | 100s                | 110s              | 140s     |
+---------------------------+---------------------+-------------------+----------+
| ``simActivateTI``         | 100s                | 110s              | 140s     |
+---------------------------+---------------------+-------------------+----------+
| ``simActivateTM``         | 100s                | 110s              | 140s     |
+---------------------------+---------------------+-------------------+----------+
| ``simActivateCM``         | 100s                | 110s              | 140s     |
+---------------------------+---------------------+-------------------+----------+
| ``simActivateSM``         | 100s                | 110s              | 140s     |
+---------------------------+---------------------+-------------------+----------+
| ``simAgdOperator``        | 100s                | 110s              | 140s     |
+---------------------------+---------------------+-------------------+----------+
| ``voiceActivate``         | 100s                | 110s              | 140s     |
+---------------------------+---------------------+-------------------+----------+
| ``simDeactivateTC``       | 270s                | 300s              | 330s     |
+---------------------------+---------------------+-------------------+----------+
| ``simDeactivateAll``      | 270s                | 300s              | 330s     |
+---------------------------+---------------------+-------------------+----------+
| ``voiceDesactivate``      | 270s                | 300s              | 330s     |
+---------------------------+---------------------+-------------------+----------+

Verificar Tarefas em Execução
------------------------------

.. code-block:: bash

   # Garantir um único beat
   docker ps | grep celery_beat

   # Verificar fila de tarefas
   redis-cli KEYS "*celery*"
   redis-cli LRANGE celery 0 10

   # Logs de worker em tempo real
   celery -A core worker --loglevel=debug

   # Verificar tarefas agendadas no banco (deve bater com CELERY_BEAT_SCHEDULE)
   python manage.py shell -c "
   from django_celery_beat.models import PeriodicTask
   for t in PeriodicTask.objects.all().order_by('name'):
       print(t.name, t.task, t.enabled)
   "
