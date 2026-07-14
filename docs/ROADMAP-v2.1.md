--- 
tags: [крепость, роадмэп, архитектура, мониторинг]
date: 2026-07-15
version: 2.2
status: active
replaces: roadmap-v2.1
hardware:
  mac_studio: M4 Max 64GB 1TB
  macbook_air: M5 32GB 1TB
  fast_ssd: WD SN850X 2TB TB5 enclosure (80Gbps)
  archive_hdd: 4TB accelerated
  dock: UGREEN Revodok Max TB5 13-in-1
  tb_cables: 6x TB4 40Gbps
  status: delivered 2026-07-15
models:
  main: Qwen3.6-35B-A3B (MoE, Q4)
  guard: Qwen3Guard-Gen-4B
  attacker: uncensored local (candidate dolphin3-cyber-8b)
  embedder: BGE-M3 / nomic-embed-text-v1.5
  reader: OCC-RAG-1.7B (planned)
  image_gen: FLUX.1 [schnell] + [dev]
next_review: 2026-08-01
---

# 🗺️ КРЕПОСТЬ — РОАДМЭП v2.2

## Архитектура (зафиксирована)
- ОСНОВНОЙ ИИ (Mac Studio M4 Max 64ГБ) — Qwen3.6-35B-A3B, конституция, RAG.
- ЗАЩИТА — Qwen3Guard-Gen-4B на Studio (и smoke на Air).
- АТАКУЮЩИЙ (MacBook Air M5 32ГБ, грязная зона) — uncensored LLM для Ataker-boop.
- ОБЛАКО — недоверенный помощник, ответ через Карантин (quarantine:true).
- СОВЕТ — по кнопке, не на каждый запрос. «Учитель» удалён.
- Threat model A (наружу не смотрит).

## Железо (2026-07-15 — приехало)

| Компонент | Спека |
|-----------|-------|
| Mac Studio | M4 Max, 64 GB, 1 TB |
| MacBook Air | M5, 32 GB, 1 TB |
| SN850X | 2 TB, TB5 корпус ~80 Gbps |
| HDD | 4 TB, ускоренный |
| Док | UGREEN Revodok Max TB5 13-in-1 |
| Кабели | 6× TB 40 Gbps |

Подробнее: [01-04-HARDWARE.md](architecture/01-04-HARDWARE.md)

---

## ФАЗА 0 — ЗАКРЫТА (код без Mac)

Большая часть Фазы 0 выполнена в коде (pipeline v2.2, Т1–Т12, Extended). Железо ждали — **теперь на месте**.

---

## ФАЗА 1 — СБОРКА (СЕЙЧАС) ⬅

### 1.0 День-1 на Studio
- `ollama pull` или LM Studio: `qwen3.6-35b-a3b`, `qwen3guard-gen-4b`
- Smoke e2e через `build_openai_orchestrator` / `build_ollama_orchestrator`
- Замер latency main + guard; guard timeout ≥120s на Air CPU

### 1.0b Air — атакующий
- Выбрать финальный uncensored attacker (канд. `dolphin3-cyber-8b`)
- SN850X: seed-корпус, adversarial JSONL, физическая изоляция

### 1.1 main.py — соединить 9 модулей
Пайплайн: User → Охранник → Карантин → [Router+RAG+LLM] → Пост-процессор → User.
Общий EmbeddingProvider, подписка on_event на monitor, запуск watchers.

### 1.2 Новый app.py
Старые устарели. Под новые модули.

### 1.3 Llama Guard / Qwen-Guard слой 2
Заменить MockSafetyClassifier на реальный. Починить формат запроса (баг 5).

### 1.4 Инфраструктура
config.py, models.py, __init__.py, .env.example, requirements.txt, backup.sh.
backup.sh: рабочее (SN580) и бэкап (HDD) — РАЗНЫЕ диски.

### 1.5 Периферия и диски
- UGREEN Revodok Max TB5 — док подключён, 6× TB4 40Gbps
- SN850X 2TB на TB5 — adversarial / train data
- HDD 4TB — archive + backup (разные диски от рабочего SSD!)
- Мышь ⏳ в пути

### 1.6 KVEraser integration
Обучаемое удаление harmful spans из KV-cache.
Latency +24% vs +1760% (full recompute).
Критично для гигиены памяти RAG-агента.

### 1.7 Modern Hopfield Memory
Episodic memory через content-addressable storage.
Lifelong learning без дообучения модели.
Интеграция с label_conflicts resolution.

### 1.8 Мониторинг и алерты
Telegram Bot + Pushover для iPhone/iPad.
Критические алерты: prompt injection, Guard crash.
Еженедельные отчёты: Email.

---

## ФАЗА 2 — ПОСЛЕ СБОРКИ

### 2.1 Атакующий + attack_vault (на Air)
Переиспользовать document_ingestion (2й экземпляр) + adversarial_pipeline читает из vault.
Отдельный Chroma-индекс. Старые jailbreak-промпты из архива → сюда как боеприпасы.
Защита НЕ видит vault атак заранее.

### 2.2 Red Team Loop (обучение защиты)
Атака → спарринг → провалы → изолированная база → дообучение (твой gate) →
safety-обвязка (прогон adversarial → откат если ASR вырос) → повтор.

### 2.3 self_improvement / PER
Самый опасный модуль. Последним. Ручной gate. Барьер обучения от заражения —
закрывается ЗДЕСЬ (до этого обучение физически не запускается).

### 2.4 Tool Chains
С санитизацией web-результатов (injection-канал).

---

## БЭКЛОГ (когда ядро работает)
- Knowledge Gap Detector (почти готов: rag_score<порога=дыра) — высокий приоритет.
- Silent Watcher (из monitoring+triggers).
- Local Data Miner, Personal Task Extractor, GraphRAG, Prompt Refiner.
- Cloud Fallback (опц., через карантин).
- Совет (5 агентов, по кнопке).
- Служебные промпты → prompts/tools/ (для агентов-инструментов, НЕ основного ИИ).
- KVEraser + Source Citations: автоинвалидация при удалении источников
- Retriever Protocol: формализация адаптеров (ChromaDB/FAISS)
- LedgerAgent: structured state для debugging
- DGX Spark (128GB unified memory): цель на 2027, $3000
- NVMe RAID 0 (2x4TB): цель на конец 2026, ~$600

---

## МЕТРИКИ УСПЕХА

### Безопасность
- Held-out Poison Recall: >80%
- False Positive Rate: <5%
- F-beta (β=2): >0.85

### Производительность
- Latency P95 (cache hit): <50ms
- Latency P95 (full pipeline): <5000ms
- Cache Hit Rate: >70%

### Надёжность
- Uptime: >99%
- Graceful shutdown: 100% случаев
- Unit Test Coverage: >90%

---

## ПОРЯДОК БЛИЖАЙШИХ ШАГОВ
1. Выбор модели (0.1) — разблокирует остальное.
2. security.py v1.1 (0.4) — починить дыру (баг 4).
3. Промпт основного ИИ (0.2) + защитный (0.3).
4. Структура датасета (0.5).
→ дальше ЖДЁМ Mac → Фаза 1 (сборка).