# Предложение 09: LocalAI v4.4.0 как основа распределённого инференса

**Дата:** 2026-06-25
**Этап Крепости:** Foundation
**Приоритет:** Высокий
**Статус:** Ожидает рассмотрения

---

## Проблема

Крепость требует суверенного (полностью локального) инференса LLM без зависимости от облачных API. Текущие ограничения:

- Один GPU-узел не вмещает крупные модели (70B+)
- Нет отказоустойчивости: падение единственного узла останавливает систему
- Нет маршрутизации запросов с учётом prefix-cache
- Нет PII-фильтрации на уровне инференс-слоя
- Данные не должны покидать контролируемый периметр (152-ФЗ)

## Решение: LocalAI v4.4.0 Distributed

LocalAI v4.4.0 предоставляет распределённый инференс (Distributed v4) с prefix-cache-aware маршрутизацией, встроенной Knowledge Base с цитированием источников (RAG source citations), и поддержкой гетерогенного оборудования.

**Источник:** [LocalAI v4.4.0 Release](https://github.com/mudler/LocalAI/releases/tag/v4.4.0)

---

## Ключевые компоненты

### 1. Distributed v4 с prefix-cache-aware маршрутизацией

- Запросы с общим prefix (системный промпт, retrieved контекст) направляются на узел, где этот prefix уже закэширован
- Экономия до 60-80% вычислений при повторных запросах с одинаковым префиксом
- Автоматический failover при падении узла
- Балансировка нагрузки между воркерами

### 2. NATS JWT Auth + TLS/mTLS

Аутентификация и шифрование между узлами кластера:

```
+-------------------+       mTLS        +-------------------+
|   Координатор     |<=================>|   Воркер 1        |
|   (NATS Server)   |    JWT tokens     |   (GPU: NVIDIA)   |
|                   |<=================>|                   |
|   - JWT issuer    |       mTLS        +-------------------+
|   - TLS terminator|<=================>+-------------------+
|   - Route table   |    JWT tokens     |   Воркер 2        |
+-------------------+                   |   (GPU: AMD)      |
                                        +-------------------+
                                        +-------------------+
                          mTLS          |   Воркер 3        |
                    <=================>|   (CPU: Intel)     |
                         JWT tokens     +-------------------+
```

- Каждый воркер аутентифицируется JWT-токеном с ограниченным сроком жизни
- Все коммуникации зашифрованы mTLS (взаимная аутентификация)
- Отзыв токена немедленно отключает воркер от кластера
- Совместимость с концепцией Sovereign Execution Brokers (предложение 07)

### 3. Worker Registration Token Enforcement

- Новый воркер не может присоединиться к кластеру без registration token
- Токен выдаётся администратором, имеет ограниченный срок действия
- Привязка к hardware fingerprint (опционально)
- Audit log всех регистраций/отключений

### 4. PII Detection/Redaction Middleware

Промежуточный слой между пользователем и моделью:

```
Запрос --> [PII Detector] --> [Redactor] --> LLM --> [PII Check] --> Ответ
              |                                          |
              v                                          v
         Аудит-лог                                  Аудит-лог
```

- Интеграция с Layer 4 (Output Filter) Security Pipeline Крепости
- Обнаружение: email, телефоны, ИНН, паспортные данные, адреса
- Маскирование до отправки в модель
- Проверка ответа на утечку PII перед выдачей пользователю
- Совместимость с 152-ФЗ

### 5. DS4 Layer-Split Inference (Model Sharding)

Распределение слоёв модели по нескольким GPU/узлам:

```
Модель 70B (140 слоёв):

Воркер 1 (NVIDIA A100 80GB):   Слои 0-46    [embedding + attention layers]
Воркер 2 (NVIDIA A100 80GB):   Слои 47-93   [attention layers]
Воркер 3 (NVIDIA A100 80GB):   Слои 94-140  [attention layers + head]

Pipeline parallelism: batch N обрабатывается на воркере 2,
пока batch N+1 на воркере 1, batch N-1 на воркере 3
```

- Модели, не помещающиеся в одну GPU, разбиваются по слоям
- Pipeline parallelism для увеличения пропускной способности
- Поддержка гетерогенного оборудования (разные GPU на разных узлах)
- Автоматическое определение оптимального разбиения

### 6. Поддержка гетерогенного оборудования

| Платформа | Backend | Формат модели |
|---|---|---|
| NVIDIA (CUDA) | llama.cpp, vLLM | GGUF, GPTQ, AWQ |
| AMD (ROCm) | llama.cpp | GGUF |
| Intel (CPU/XPU) | llama.cpp, OpenVINO | GGUF, OpenVINO IR |
| Apple (Metal) | llama.cpp | GGUF |

---

## Docker Compose: эскиз развёртывания

```yaml
# docker-compose.yml -- LocalAI v4.4.0 Distributed для Крепости
# ВНИМАНИЕ: это эскиз, не production-конфигурация

version: "3.9"

x-common-env: &common-env
  LOCALAI_LOG_LEVEL: info
  NATS_URL: nats://nats-server:4222
  NATS_TLS_CERT: /certs/node.crt
  NATS_TLS_KEY: /certs/node.key
  NATS_TLS_CA: /certs/ca.crt

services:
  # ── NATS Server (координация кластера) ──
  nats-server:
    image: nats:2.11-alpine
    ports:
      - "4222:4222"   # client
      - "8222:8222"   # monitoring
    volumes:
      - ./certs:/certs:ro
      - ./nats-config:/config:ro
    command: >
      --config /config/nats-server.conf
      --tls
      --tlscert /certs/nats.crt
      --tlskey /certs/nats.key
      --tlscacert /certs/ca.crt
      --tlsverify
    networks:
      - krepost-net
    restart: unless-stopped

  # ── LocalAI Координатор ──
  localai-coordinator:
    image: localai/localai:v4.4.0-cublas-cuda12
    ports:
      - "8080:8080"   # API
    environment:
      <<: *common-env
      LOCALAI_ROLE: coordinator
      LOCALAI_DISTRIBUTED: "true"
      LOCALAI_PREFIX_CACHE: "true"
      LOCALAI_WORKER_REGISTRATION_TOKEN: "${WORKER_REG_TOKEN}"
      LOCALAI_JWT_SECRET: "${JWT_SECRET}"
      LOCALAI_PII_MIDDLEWARE: "true"
      LOCALAI_PII_PATTERNS: "/config/pii-patterns-ru.yaml"
    volumes:
      - ./models:/models
      - ./certs:/certs:ro
      - ./config:/config:ro
    networks:
      - krepost-net
    restart: unless-stopped
    depends_on:
      - nats-server

  # ── Воркер 1: NVIDIA GPU ──
  worker-nvidia:
    image: localai/localai:v4.4.0-cublas-cuda12
    environment:
      <<: *common-env
      LOCALAI_ROLE: worker
      LOCALAI_WORKER_NAME: "nvidia-worker-01"
      LOCALAI_REGISTRATION_TOKEN: "${WORKER_REG_TOKEN}"
      LOCALAI_LAYER_SPLIT: "0-46"
    volumes:
      - ./models:/models:ro
      - ./certs:/certs:ro
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    networks:
      - krepost-net
    restart: unless-stopped
    depends_on:
      - localai-coordinator

  # ── Воркер 2: AMD GPU ──
  worker-amd:
    image: localai/localai:v4.4.0-hipblas
    environment:
      <<: *common-env
      LOCALAI_ROLE: worker
      LOCALAI_WORKER_NAME: "amd-worker-01"
      LOCALAI_REGISTRATION_TOKEN: "${WORKER_REG_TOKEN}"
      LOCALAI_LAYER_SPLIT: "47-93"
    volumes:
      - ./models:/models:ro
      - ./certs:/certs:ro
    devices:
      - /dev/kfd
      - /dev/dri
    networks:
      - krepost-net
    restart: unless-stopped
    depends_on:
      - localai-coordinator

  # ── Воркер 3: Intel CPU (для лёгких моделей / OCC-RAG) ──
  worker-intel:
    image: localai/localai:v4.4.0-intel
    environment:
      <<: *common-env
      LOCALAI_ROLE: worker
      LOCALAI_WORKER_NAME: "intel-worker-01"
      LOCALAI_REGISTRATION_TOKEN: "${WORKER_REG_TOKEN}"
      LOCALAI_DEDICATED_MODELS: "occ-rag-1.7b,bge-m3"
    volumes:
      - ./models:/models:ro
      - ./certs:/certs:ro
    networks:
      - krepost-net
    restart: unless-stopped
    depends_on:
      - localai-coordinator

  # ── PII Middleware (отдельный сервис) ──
  pii-middleware:
    image: krepost/pii-filter:latest
    build:
      context: ./pii-filter
    environment:
      UPSTREAM_URL: http://localai-coordinator:8080
      PII_PATTERNS: "/config/pii-patterns-ru.yaml"
      AUDIT_LOG: "/logs/pii-audit.jsonl"
    ports:
      - "8081:8081"   # API через PII-фильтр
    volumes:
      - ./config:/config:ro
      - ./logs:/logs
    networks:
      - krepost-net
    restart: unless-stopped
    depends_on:
      - localai-coordinator

networks:
  krepost-net:
    driver: bridge
    ipam:
      config:
        - subnet: 172.28.0.0/16
```

---

## Конфигурация безопасности

### NATS Server (nats-server.conf)

```
# nats-server.conf для Крепости

authorization {
  # JWT-аутентификация
  token: $NATS_AUTH_TOKEN
}

tls {
  cert_file: /certs/nats.crt
  key_file: /certs/nats.key
  ca_file: /certs/ca.crt
  verify: true              # mTLS: требуем клиентский сертификат
  timeout: 5
}

# Ограничения
max_connections: 20
max_payload: 8MB
max_pending: 64MB

# Мониторинг
http_port: 8222

# Логирование
log_file: /logs/nats.log
trace: false
debug: false
```

### PII-паттерны для русскоязычных данных (pii-patterns-ru.yaml)

```yaml
# pii-patterns-ru.yaml
version: "1.0"
locale: "ru_RU"

patterns:
  # Персональные данные (152-ФЗ)
  - name: "phone_ru"
    regex: '(\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}'
    action: mask
    replacement: "[ТЕЛЕФОН]"

  - name: "email"
    regex: '[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}'
    action: mask
    replacement: "[EMAIL]"

  - name: "inn_individual"
    regex: '\b\d{12}\b'
    context_required: ["ИНН", "инн", "INN"]
    action: mask
    replacement: "[ИНН]"

  - name: "inn_legal"
    regex: '\b\d{10}\b'
    context_required: ["ИНН", "инн", "INN"]
    action: mask
    replacement: "[ИНН]"

  - name: "passport_ru"
    regex: '\b\d{2}\s?\d{2}\s?\d{6}\b'
    context_required: ["паспорт", "серия", "номер"]
    action: mask
    replacement: "[ПАСПОРТ]"

  - name: "snils"
    regex: '\b\d{3}[\s\-]?\d{3}[\s\-]?\d{3}\s?\d{2}\b'
    context_required: ["СНИЛС", "снилс"]
    action: mask
    replacement: "[СНИЛС]"

  - name: "card_number"
    regex: '\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b'
    action: mask
    replacement: "[КАРТА]"
```

---

## Интеграция с существующими компонентами Крепости

| Компонент Крепости | Интеграция с LocalAI |
|---|---|
| Security Pipeline (pipeline.py) | PII Middleware дополняет Layer 4 (Output Filter) |
| SmartCache (SMART_CACHE.py) | Prefix-cache LocalAI работает на уровне ниже SmartCache; L1 QueryEmbeddingCache может использовать выделенный Intel-воркер для BGE-M3 |
| ChromaDB / Knowledge Base | RAG source citations из LocalAI 4.4.0 -- блок `Sources:` в ответах |
| TrustRegistry | Регистрация воркеров через TrustRegistry + JWT |
| Sovereign Execution Brokers (предл. 07) | JWT/mTLS-модель LocalAI совместима с SEB certificate-bound контролем |

---

## Сценарии развёртывания

### Минимальный (1 узел, разработка)

```
1x GPU (NVIDIA/AMD) -- координатор + воркер в одном контейнере
Модели: OCC-RAG 1.7B (GGUF) + Qwen3Guard-Gen-4B
RAM: 32 GB, VRAM: 16+ GB
```

### Средний (3 узла, пилот)

```
1x координатор (CPU)
2x воркер GPU (NVIDIA) -- layer-split для 70B модели
1x воркер CPU (Intel) -- embedding + лёгкие модели
Модели: Qwen-70B (sharded) + OCC-RAG 1.7B + BGE-M3
RAM: 64 GB/узел, VRAM: 80 GB/GPU
```

### Полный (5+ узлов, продакшн)

```
1x координатор (CPU, HA-pair)
3x воркер GPU -- основные модели
2x воркер CPU -- embedding, guard, OCC-RAG
1x NATS-кластер (3 узла, quorum)
Модели: несколько моделей разного размера, hot-swap
```

---

## Этапы интеграции

### Фаза 1: Единичный узел (1 неделя)
- Развёртывание LocalAI v4.4.0 в Docker
- Загрузка и тестирование OCC-RAG 1.7B GGUF
- Подключение к SmartCache через API
- Базовая настройка PII-фильтрации

### Фаза 2: Кластер (2 недели)
- Настройка NATS с JWT + mTLS
- Добавление второго воркера
- Тестирование prefix-cache-aware маршрутизации
- Тестирование layer-split для крупной модели

### Фаза 3: Безопасность (1 неделя)
- Полная конфигурация PII middleware с русскоязычными паттернами
- Интеграция с Security Pipeline (Layer 4)
- Audit logging всех операций
- Тестирование отзыва токенов и failover

### Фаза 4: Продакшн (2 недели)
- HA-конфигурация координатора
- Мониторинг (Netdata, предложение 04)
- Нагрузочное тестирование
- Документация runbook

---

## Риски и митигация

| Риск | Митигация |
|---|---|
| Латентность при layer-split (inter-node communication) | Высокоскоростная сеть (25Gbps+), batch pipeline parallelism |
| Компрометация JWT-токена воркера | Короткий TTL (1 час), автоматическая ротация, мониторинг |
| Несовместимость моделей с GGUF | Предварительное тестирование, fallback на vLLM backend |
| Потеря данных при падении координатора | NATS JetStream для персистентности, HA-pair координаторов |

---

## Связанные предложения

- **04 (Netdata Monitoring)** -- мониторинг GPU/CPU утилизации воркеров
- **05 (TokenPilot)** -- управление контекстом до отправки в LocalAI
- **07 (Sovereign Execution Brokers)** -- certificate-bound контроль мутаций

---

**Решение владельца:** _______________
**Дата решения:** _______________
**Комментарии:** _______________
