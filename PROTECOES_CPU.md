# 🛡️ Proteções Contra Sobrecarga de CPU

## ✅ Implementado

### 1. **Timeout em Conexões HTTP** (CRÍTICO)
- ✅ Adicionado `timeout=10` segundos em **todas as 19 conexões HTTP**
- ✅ Evita tasks travadas esperando APIs externas
- **Problema resolvido:** Se API externa cair, task não fica pendurada para sempre

**Arquivos alterados:**
- `apps/sims/classes.py` - 8 conexões corrigidas
- `apps/sims/tasks.py` - 4 conexões corrigidas  
- `apps/voice_calls/tasks.py` - 2 conexões corrigidas

### 2. **Limite de Processamento por Execução**
- ✅ Máximo de **50 pedidos** processados por vez em `sims_in_orders()`
- ✅ Evita sobrecarga quando há acúmulo de pedidos
- ✅ Log de alerta quando há mais de 50 pendentes

**Antes:**
```python
orders = Orders.objects.filter(order_status='AS')  # Todos!
```

**Depois:**
```python
orders = Orders.objects.filter(order_status='AS')[:50]  # Max 50
```

### 3. **Task Timeout no Celery**
- ✅ `time_limit=300` (5 min) - Task é killada se passar disso
- ✅ `soft_time_limit=240` (4 min) - Aviso antes de matar

**Aplicado em:**
- `sims_in_orders()` - Tarefa de processamento principal

### 4. **Sistema de Logs Completo**
- ✅ 4 arquivos de log separados (django, celery, api, performance)
- ✅ Rotação automática (10MB cada)
- ✅ Logs de alerta para tasks > 30s

## 📊 Como os Logs Vão Ajudar a Identificar o Problema

### Cenário 1: Acúmulo de Pedidos Pendentes
**Sintoma:** Logs mostrarão:
```
[WARNING] ATENÇÃO: 350 pedidos pendentes, processando apenas 50 por vez
```

**Causa provável:** Alguma operadora com API fora ou muitos pedidos sem SIM disponível

**Como verificar:**
```bash
docker exec celery tail -50 /djangoweb/logs/celery.log | grep "ATENÇÃO"
```

### Cenário 2: API Externa Travada
**Sintoma:** Logs mostrarão:
```
[ERROR] [API TC] Erro ao buscar ICCID 89123456: timed out
```

**Causa provável:** API da operadora está lenta ou fora do ar

**Como verificar:**
```bash
docker exec celery tail -100 /djangoweb/logs/api_calls.log | grep "Erro"
```

### Cenário 3: Task Muito Lenta
**Sintoma:** Logs mostrarão:
```
[WARNING] [LENTO] Ativação de SIMs TC demorou 45.32s - Task ID: abc123
```

**Causa provável:** Muitos SIMs para ativar de uma vez ou API lenta

**Como verificar:**
```bash
docker exec celery tail -100 /djangoweb/logs/performance.log | grep "LENTO"
```

### Cenário 4: Task Killada por Timeout
**Sintoma:** Logs mostrarão:
```
[ERROR] Task exceeded time limit (300s) and was terminated
```

**Causa provável:** Loop infinito ou processamento muito pesado

## 🔍 Monitoramento Recomendado

### Durante os próximos dias, monitore:

```bash
# 1. Ver quantidade de pedidos pendentes
docker exec celery tail -f /djangoweb/logs/celery.log | grep "pendentes"

# 2. Ver erros de timeout
docker exec celery tail -f /djangoweb/logs/api_calls.log | grep "timeout\|Erro"

# 3. Ver tasks lentas
docker exec celery tail -f /djangoweb/logs/performance.log

# 4. Ver uso de CPU em tempo real
docker stats celery celery_beat djangoweb --no-stream
```

### Quando ocorrer o próximo pico de CPU:

```bash
# Capturar logs imediatamente
docker exec celery tail -200 /djangoweb/logs/celery.log > pico_celery.log
docker exec celery tail -200 /djangoweb/logs/api_calls.log > pico_api.log
docker exec celery tail -200 /djangoweb/logs/performance.log > pico_performance.log

# Ver tarefas ativas naquele momento
docker exec celery celery -A core inspect active > pico_tasks.txt
```

## 🎯 Análise Pós-Pico

Após coletar os logs durante um pico, procure por:

1. **Mensagem de "ATENÇÃO"** → Acúmulo de pedidos
2. **Múltiplos "timeout"** → API externa com problema
3. **Tasks com > 100s** → Processamento muito pesado
4. **Mesmo pedido/SIM repetido** → Loop de retry

## 📈 Métricas para Observar

| Métrica | Normal | Atenção | Crítico |
|---------|--------|---------|---------|
| Pedidos pendentes | < 20 | 20-50 | > 50 |
| Tempo de task | < 10s | 10-30s | > 30s |
| Erros de timeout | 0-2/hora | 3-10/hora | > 10/hora |
| Tasks ativas | < 5 | 5-8 | > 8 |

## ⚙️ Otimizações Futuras (Se Necessário)

Se após essas proteções o problema persistir, considere:

### Opção 1: Reduzir Concorrência
```yaml
# docker-compose.yml
command: celery -A core worker --concurrency=4  # era 8
```

### Opção 2: Aumentar Intervalo das Tasks
```python
# core/settings.py
'schedule': crontab(minute='*/5'),  # era */2
```

### Opção 3: Adicionar Fila Prioritária
```python
# Processar pedidos VIP primeiro
orders_vip = Orders.objects.filter(order_status='AS', priority='high')[:20]
orders_normal = Orders.objects.filter(order_status='AS', priority='normal')[:30]
```

## 📝 Checklist Aplicado

- [x] Timeout de 10s em todas as 19 conexões HTTP
- [x] Limite de 50 pedidos por execução
- [x] Task timeout de 5 minutos
- [x] Logs detalhados em 4 arquivos separados
- [x] Log de alerta para pedidos acumulados
- [x] Log de erro para falhas de API
- [x] Log de warning para tasks lentas

## 🚀 Próximo Passo

**Aplicar em produção e monitorar por 3-5 dias:**

```bash
# 1. Commit das mudanças
git add .
git commit -m "feat: adicionar proteções contra sobrecarga de CPU"

# 2. Deploy
docker-compose down
docker-compose build
docker-compose up -d

# 3. Verificar logs
docker-compose logs -f celery | tee logs_monitoria.txt
```

Os logs vão revelar exatamente o que causa o pico de CPU quando ele acontecer novamente.
