# Krepost v3 — AI Security Pipeline

**Krepost** (Крепость) — 4-слойная система безопасности для локальных AI/LLM-систем.

Версия pipeline: **v2.2** | Версия cache: **v2.1** | Тесты: **`pytest tests/ Probnoki/` (787)**  
Бой: Mac Studio `serve_lmstudio` `:8000` (LM Studio main+guard). См. `ROADMAP.md`.

> 📌 Изначальный замысел проекта (зачем всё это и какой баланс между
> свободой модели и контролем системы) зафиксирован в
> [ARCHITECTURE_VISION.md](./ARCHITECTURE_VISION.md).

---

## Архитектура

4-слойный security pipeline:

```
User → [Layer 1: Regex] → [Layer 2: Guard] → [Layer 3: FewShot] → LLM → [Layer 4: OutputFilter] → User
```

| Слой | Компонент | Описание |
|------|-----------|----------|
| 1 | **RegexFilter** | Нормализация Unicode, base64-decode, homoglyph detection, XML/CDATA, chat template injection |
| 2 | **GuardClassifier** | Семантический анализ через Qwen3Guard-Gen-4B, fail-closed, circuit breaker |
| 3 | **FewShotMatcher** | Cosine similarity через ChromaDB + BGE-M3, LRU cache, fail-closed |
| 4 | **OutputFilter** | PII masking (email, карты, ключи, IP, телефоны), leakage detection, Presidio (опц.) |

Принцип: **fail-closed** на каждом слое. Все sync-вызовы через `asyncio.to_thread`.

---

## Компоненты

### Security Pipeline v2.2
- 4 слоя защиты (Regex, Guard, FewShot, OutputFilter)
- Trust Registry (fast-path для доверенных запросов, SQLite)
- Unicode Normalization v2.2 (homoglyphs, zero-width, NFKC, BOM, BiDi)
- Rate limiting (token bucket), Circuit Breaker
- Audit hash и trace hash для каждого запроса

### Smart Cache v2.1
Трехслойный кэш:
- **L1 QueryEmbeddingCache** — exact match по SHA-256 хешу, O(1) lookup
- **L2 RAGResultsCache** — semantic match по cosine similarity (threshold 0.92)
- **L3 LLMResponseCache** — exact match по (query + context + model + prompt_version)

Безопасность кэша: L2/L3 сохраняют только запросы с verdict=GREEN. Anomaly detection (cache flood, high miss rate).

### Trust Registry
SQLite-based registry доверенных запросов. Нормализованные хеши, revoke support.

### Unicode Normalization
Единый модуль канонизации: homoglyph mapping (кириллица, греческий, цифры), zero-width removal, NFKC, casefold.

---

## Целевое оборудование

- **Mac Studio M4 Max 64GB** — основная модель (Qwen3.6-35B-A3B MoE) + guard
- **MacBook Air M5 32GB** — атакующий (uncensored LLM, Ataker-boop)
- **WD SN850X 2TB TB5** — быстрый съёмный SSD (adversarial data)
- **UGREEN Revodok Max TB5** — док-станция

## Модели

| Роль | Модель |
|------|--------|
| Основная | Qwen3.6-35B-A3B (MoE, Q4) |
| Guard | Qwen3Guard-Gen-4B |
| Embedder | BGE-M3 / nomic-embed-text |
| Attacker | uncensored local (dolphin3-cyber-8b candidate) |

---

## Быстрый старт

```bash
# Установка
pip install -e .

# С поддержкой Presidio (PII detection)
pip install -e ".[presidio]"

# Dev-зависимости
pip install -e ".[dev]"

# Запуск тестов
pytest
```

### HTTP API (demo)

```bash
pip install -e ".[api]"
python -m krepost.api.server          # http://127.0.0.1:8000

curl -s localhost:8000/health
curl -s localhost:8000/v1/query \
  -H 'content-type: application/json' \
  -d '{"text":"напиши python код","session_id":"s1"}'
```

Обвязка поверх `Orchestrator`: `POST /v1/query` прогоняет запрос через
security → router → LLM → security и возвращает вердикт + ответ.
⚠️ Демо-сборка (`krepost.api.server`) использует dev-guard, пропускающий
всё — для прода нужен реальный Qwen3Guard и локальная LLM вместо EchoBackend.

### Боевой стек: LM Studio (Mac Studio)

Бой: `serve_lmstudio.py` / LaunchAgent — main **Qwen3.6-35B-A3B**, guard
**Qwen3Guard-Gen-4B**. В LM Studio подними локальный сервер (`:1234`), затем:

```bash
pip install -e ".[api]"
python serve_lmstudio.py              # http://127.0.0.1:8000
```

```python
from krepost.orchestration.factory import build_openai_orchestrator
from krepost.api.app import create_app

orch = build_openai_orchestrator(
    main_model="qwen/qwen3.6-35b-a3b",        # LM Studio id основной модели
    base_url="http://127.0.0.1:1234/v1",
    guard_model="qwen3guard-gen-4b",
)
app = create_app(orch)
```

`build_openai_agent(tools=[...])` — агентный режим. HTTP через stdlib;
`OpenAIGuardClient` адаптирует ответ под `GuardClassifier`.

### Альтернатива: Ollama

```bash
pip install -e ".[api,ollama]"

ollama serve &
ollama pull qwen3.6:35b-a3b           # main — Qwen3.6-35B-A3B (не 27b dense)
ollama pull qwen3guard-gen:4b         # guard (Layer 2)
```

```python
from krepost.orchestration.factory import build_ollama_orchestrator
from krepost.api.app import create_app

orch = build_ollama_orchestrator(main_model="qwen3.6:35b-a3b")
app = create_app(orch)
```

Для агентного режима — `build_ollama_agent(tools=[...])` (`ToolAgent`):
tool-результаты → `ToolOutputGuard`, fetch → `UrlGuard`. Layer 3 (few-shot):
передай `embedder` (BGE-M3) и `chroma_collection` в фабрику.

Никакой привязки к движку — «архитектура важнее модели».

---

## Структура проекта

```
Krepost-V3/
├── krepost/
│   ├── security/                # Pipeline v2.2, normalize, trust registry
│   ├── cache/
│   │   └── SMART_CACHE.py       # Smart Cache v2.1
│   ├── orchestration/           # factory, backends, agent
│   └── api/                     # FastAPI обвязка
├── tests/                       # unit/integration
├── Probnoki/                    # пробники / end-to-end checks
├── docs/                        # Документация
├── Ataker-boop/                 # атакующий (грязная зона)
├── pyproject.toml               # packages: krepost* (один корень)
└── README.md
```

Один namespace `krepost` из корня репо (`pip install -e .`). Дубликата
`src/krepost/` больше нет.

---

## Статус / Roadmap

См. актуальный [`ROADMAP.md`](./ROADMAP.md). Кратко: Studio на LM Studio
(35B-A3B + guard), Air — Ataker / dirty zone.

---

## Тесты

**787** тестов (`tests/` + `Probnoki/`, `pytest --collect-only`):

```bash
pytest tests/ Probnoki/ -v
```

Покрытие: SecurityContext, SecurityReceipt, RegexFilter (base64, homoglyphs, XML, CDATA, zero-width), GuardClassifier (parse, fail-closed), CircuitBreaker, RateLimiter, PIIMasker (email, карты Luhn, JWT, ключи, IP), OutputFilter, SecurityPipeline (integration), Unicode Normalization, Trust Registry, Smart Cache, orchestration/API, пробники.
