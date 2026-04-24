# Solucao Definitiva - Queda de Portainer + Django (AWS Lightsail)

Este runbook resolve a causa raiz quando Portainer e Django caem ao mesmo tempo: saturacao do mesmo host (CPU/RAM/I/O) e queda em cascata.

## Causa raiz

Quando Traefik, Portainer, Django, Celery e Redis rodam todos na mesma instancia pequena, qualquer pico das tasks pode travar o host inteiro. Quando isso ocorre, o painel e o site ficam indisponiveis juntos (timeout).

## Solucao definitiva (arquitetura)

1. Separar plano de controle do plano de aplicacao.
2. Limitar recursos de cada container no plano de aplicacao.
3. Aplicar watchdog de sistema (swap + restart policy + healthchecks).

## Topologia recomendada

- Instancia A (Control Plane): Traefik + Portainer
- Instancia B (App Plane): Django + Celery + Celery Beat + Redis

Se hoje voce tem apenas uma instancia, esta separacao e o passo que elimina o "apagao conjunto".

## Passo a passo de execucao

### 1) Preparar instancia B (App Plane)

- Suba uma nova Lightsail para app (minimo recomendado: 2 vCPU / 4 GB RAM).
- Aponte DNS do painel para Traefik da instancia A, e roteie para a instancia B via rede privada ou IP fixo.

### 2) Deploy com compose endurecido

No host da app:

```bash
cd /opt/sisacdc
git pull
cp .env.example .env  # se necessario

docker compose down
docker compose build --no-cache
docker compose up -d
```

### 3) Habilitar swap (essencial em Lightsail pequena)

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### 4) Ajustar kernel para evitar OOM agressivo

```bash
echo 'vm.swappiness=20' | sudo tee /etc/sysctl.d/99-sisacdc.conf
echo 'vm.vfs_cache_pressure=50' | sudo tee -a /etc/sysctl.d/99-sisacdc.conf
sudo sysctl --system
```

### 5) Aplicar politica operacional

- Sempre atualizar via `docker compose pull/build && up -d`.
- Nunca rodar build pesado em horario de pico.
- Manter Portainer e Traefik fora do host de tarefas.

## Comandos de verificacao

```bash
# Estado dos containers
docker compose ps

# Uso de recursos
docker stats --no-stream

# Ultimos OOM kills no host
dmesg -T | grep -i -E 'killed process|out of memory|oom'

# Verificar saude web (de dentro do host)
curl -I http://127.0.0.1:8000/health/ -H 'Host: painel.acasadochip.com'
```

## Sinais de que resolveu

- Portainer continua acessivel mesmo com pico de Celery.
- Django responde `/health/` continuamente.
- Nao ha novos eventos de OOM no `dmesg`.
- `docker stats` mostra Celery contido dentro dos limites.

## Rollback rapido

Se algo sair do esperado, volte para o ultimo commit estavel que voce ja validou e rode novo deploy da stack.

## Observacao importante

Este repositorio ja foi ajustado para:

- limites de CPU/RAM por container;
- startup mais seguro do Gunicorn;
- configuracao de Celery para reduzir backlog;
- timeout nas chamadas AT sem timeout;
- limites de memoria do Redis direto no compose.

A unica parte que depende de infraestrutura da AWS e a separacao das instancias (Control Plane x App Plane). Esse e o passo definitivo para parar queda conjunta.
