# Предложение 04: Мониторинг через Netdata

## Что

Real-time мониторинг инфраструктуры Крепости через Netdata -- открытую платформу наблюдения с посекундным сбором метрик, ML-детекцией аномалий на каждой метрике и обработкой данных на границе (edge-based processing).

Развёртывание на двух узлах:
- **Mac Studio** (основной inference-узел, vLLM/LocalAI, ChromaDB)
- **MacBook Air** (вспомогательный узел, агенты, Syncthing)

## Зачем

1. **ML anomaly detection per metric** -- Netdata обучает несколько unsupervised ML-моделей на каждой метрике прямо на узле. Аномалии (утечка памяти vLLM, рост latency пайплайна, деградация GPU) обнаруживаются автоматически без ручных порогов.
2. **Посекундная латентность (~1 с)** -- критично для детектирования атак на SecurityPipeline в реальном времени: всплеск RED-вердиктов, рост rate_limit отказов, перегрузка GuardClassifier.
3. **Alerting с маршрутизацией** -- уведомления через Telegram/Pushover при превышении порогов или обнаружении аномалии. Оператор получает alert за секунды, а не минуты.
4. **Edge-based обработка** -- данные не покидают периметр Крепости. Приватность метрик гарантирована архитектурой (без Netdata Cloud).
5. **Нулевая конфигурация** -- auto-discovery контейнеров Docker, системных ресурсов, процессов на macOS/Linux.
6. **Энергоэффективность** -- самый энергоэффективный инструмент мониторинга (исследование Амстердамского университета, 2023).

## Что добавляется

### 1. Docker-конфигурация для Mac Studio (основной узел)

```yaml
# docker-compose.netdata.yml
# Развёртывание Netdata для мониторинга инфраструктуры Крепости
# Mac Studio — Parent-узел (централизация метрик)

version: "3.8"

services:
  netdata-parent:
    image: netdata/netdata:stable
    container_name: krepost-netdata-parent
    hostname: krepost-mac-studio
    restart: unless-stopped
    ports:
      - "19999:19999"    # Dashboard (только localhost)
    cap_add:
      - SYS_PTRACE       # Мониторинг процессов
    security_opt:
      - apparmor=unconfined
    volumes:
      # Системные метрики хоста
      - /etc/passwd:/host/etc/passwd:ro
      - /etc/group:/host/etc/group:ro
      - /etc/localtime:/etc/localtime:ro
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
      # Персистентное хранилище метрик
      - netdata-config:/etc/netdata
      - netdata-lib:/var/lib/netdata
      - netdata-cache:/var/cache/netdata
      # Конфигурация алертов Крепости
      - ./netdata/health.d:/etc/netdata/health.d:ro
      - ./netdata/netdata.conf:/etc/netdata/netdata.conf:ro
    environment:
      # Отключение телеметрии
      - DO_NOT_TRACK=1
      - NETDATA_DISABLE_CLOUD=1
      # Parent-режим: принимает стримы от MacBook Air
      - NETDATA_STREAM_ENABLED=true
    networks:
      - krepost-net

  netdata-child:
    # Для MacBook Air: запускается отдельно, стримит на Parent
    # Здесь приведена конфигурация стриминга
    image: netdata/netdata:stable
    container_name: krepost-netdata-child
    hostname: krepost-macbook-air
    restart: unless-stopped
    cap_add:
      - SYS_PTRACE
    volumes:
      - /etc/passwd:/host/etc/passwd:ro
      - /etc/group:/host/etc/group:ro
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - ./netdata/stream.conf:/etc/netdata/stream.conf:ro
    environment:
      - DO_NOT_TRACK=1
      - NETDATA_DISABLE_CLOUD=1
    networks:
      - krepost-net

volumes:
  netdata-config:
  netdata-lib:
  netdata-cache:

networks:
  krepost-net:
    external: true
```

### 2. Конфигурация стриминга (stream.conf)

```ini
# stream.conf — MacBook Air → Mac Studio
[stream]
    enabled = yes
    destination = mac-studio.local:19999
    api key = KREPOST_STREAM_API_KEY_REPLACE_ME
    timeout seconds = 60
    send charts matching = *

# На Parent (Mac Studio) — разрешение приёма
[KREPOST_STREAM_API_KEY_REPLACE_ME]
    enabled = yes
    allow from = 192.168.0.0/16
    default history = 86400
    default memory mode = dbengine
```

### 3. Алерты для метрик Крепости (health.d/krepost.conf)

```yaml
# health.d/krepost.conf — алерты для SecurityPipeline и SMART_CACHE

# ─── CPU ────────────────────────────────────────────────────────────
 alarm: krepost_cpu_high
    on: system.cpu
lookup: average -5m percentage
 units: %
 every: 10s
  warn: $this > 75
  crit: $this > 90
 delay: down 5m
  info: Загрузка CPU выше нормы — возможна перегрузка inference

# ─── RAM ────────────────────────────────────────────────────────────
 alarm: krepost_ram_usage
    on: system.ram
lookup: average -1m percentage
 units: %
 every: 10s
  warn: $this > 80
  crit: $this > 95
  info: Потребление RAM — контроль утечек vLLM/ChromaDB

# ─── Docker-контейнеры ──────────────────────────────────────────────
 alarm: krepost_container_restart
    on: docker_container.health_status
lookup: sum -5m
 units: restarts
 every: 30s
  warn: $this > 2
  crit: $this > 5
  info: Перезапуск контейнера Крепости — возможный crash loop

# ─── Disk I/O (ChromaDB, кэш) ──────────────────────────────────────
 alarm: krepost_disk_io_high
    on: disk.io
lookup: average -2m unaligned of read write
 units: KiB/s
 every: 10s
  warn: $this > 50000
  crit: $this > 100000
  info: Высокий disk I/O — проверить операции ChromaDB/SMART_CACHE

# ─── Сетевая активность (аномалии) ──────────────────────────────────
 alarm: krepost_network_anomaly
    on: net.net
lookup: average -1m
 units: kilobits/s
 every: 10s
  warn: $this > 100000
  info: Аномальный сетевой трафик — возможная утечка данных

# ─── GPU Utilization (если доступен) ────────────────────────────────
 alarm: krepost_gpu_utilization
    on: nvidia_smi.gpu_utilization
lookup: average -2m
 units: %
 every: 30s
  warn: $this > 90
  info: GPU загружен >90%% — инференс может деградировать
```

### 4. Интеграция с Telegram/Pushover

```ini
# health_alarm_notify.conf

# Telegram
SEND_TELEGRAM="YES"
TELEGRAM_BOT_TOKEN="REPLACE_WITH_BOT_TOKEN"
TELEGRAM_CHAT_ID="REPLACE_WITH_CHAT_ID"
DEFAULT_RECIPIENT_TELEGRAM="REPLACE_WITH_CHAT_ID"

# Pushover (резервный канал)
SEND_PUSHOVER="YES"
PUSHOVER_APP_TOKEN="REPLACE_WITH_APP_TOKEN"
DEFAULT_RECIPIENT_PUSHOVER="REPLACE_WITH_USER_KEY"
```

### 5. Пользовательские метрики Крепости (statsd)

Добавить в SecurityPipeline отправку метрик через StatsD:

```python
# krepost/security/metrics_exporter.py (эскиз)
import socket
import time

class NetdataStatsD:
    """Экспорт метрик SecurityPipeline в Netdata через StatsD."""

    def __init__(self, host: str = "localhost", port: int = 8125):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._addr = (host, port)

    def _send(self, metric: str, value: float, type_: str = "g"):
        msg = f"krepost.{metric}:{value}|{type_}"
        self._sock.sendto(msg.encode(), self._addr)

    def report_verdict(self, verdict: str, latency_ms: float):
        """Отправить вердикт и латентность в Netdata."""
        self._send(f"pipeline.verdict.{verdict.lower()}", 1, "c")
        self._send("pipeline.latency_ms", latency_ms, "ms")

    def report_cache_stats(self, layer: str, hits: int, misses: int):
        """Отправить статистику SMART_CACHE."""
        self._send(f"cache.{layer}.hits", hits)
        self._send(f"cache.{layer}.misses", misses)
        total = hits + misses
        if total > 0:
            self._send(f"cache.{layer}.hit_rate", hits / total * 100)

    def report_rate_limit(self, session_id: str, rejected: bool):
        """Отправить событие rate limiter."""
        self._send("rate_limiter.total", 1, "c")
        if rejected:
            self._send("rate_limiter.rejected", 1, "c")
```

## Зависимости

| Зависимость | Версия | Назначение |
|---|---|---|
| Docker + Docker Compose | >= 24.0 | Запуск контейнеров Netdata |
| Сеть между узлами | LAN / Tailscale | Стриминг метрик MacBook Air -> Mac Studio |
| Порт 19999 | TCP | Dashboard + API Netdata |
| Порт 8125 | UDP | StatsD для кастомных метрик |
| Telegram Bot API | -- | Канал уведомлений (требуется создание бота) |

## Риски

| Риск | Уровень | Митигация |
|---|---|---|
| Потребление ресурсов ~5% CPU, ~150MB RAM | Низкий | Netdata оптимизирован; можно отключить ML/алерты для снижения до <1% CPU и ~100MB RAM |
| Расширение поверхности атаки (порт 19999) | Средний | Биндить только на localhost/LAN; firewall правила; basic auth |
| Docker socket read-only доступ | Низкий | Только чтение; контейнер без привилегий записи |
| Шум от false-positive алертов | Средний | Настроить delay/hysteresis; ML anomaly detection снижает ложные срабатывания |
| Дисковое пространство для метрик | Низкий | ~0.5 байт/сэмпл; 3-tier хранилище с автоматической агрегацией |

## Этапы внедрения

1. Развернуть Netdata на Mac Studio (Parent) через docker-compose
2. Настроить stream.conf и развернуть Child на MacBook Air
3. Добавить алерты для Крепости (health.d/krepost.conf)
4. Подключить Telegram-уведомления
5. Интегрировать StatsD-экспортёр в SecurityPipeline и SMART_CACHE
6. Мониторинг 7 дней -> корректировка порогов на основе baseline

## Статус: ⏳ Ожидает одобрения
