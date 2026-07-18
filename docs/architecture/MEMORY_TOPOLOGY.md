# Топология памяти Крепости (две машины)

> Где физически живёт память, кто и как к ней ходит. Дополняет
> [_handoff/MEMORY_ROUTER_SPEC.md](../../_handoff/MEMORY_ROUTER_SPEC.md)
> (логика маршрутизации) и ROADMAP «🧠 memory».

## TL;DR

Вся долговременная память Крепости (vault + векторная БД) физически живёт на
**Mac Studio**. MacBook Air — клиент/атакующий, своей боевой памяти не держит,
а ходит к памяти Studio по прямому Thunderbolt-каналу через HTTP API Крепости.

## Две машины, две роли

| Машина | Роль | Что держит |
|--------|------|------------|
| **Mac Studio** (M4 Max, 64GB) | Дом базы знаний + сервер | vault (Obsidian), persistent ChromaDB, MemoryStore, LM Studio (main+guard), боевой HTTP API |
| **MacBook Air** (M5, 32GB) | Клиент / атакующий (adversarial) | Копию репозитория (код), но НЕ боевую память; Ataker-boop гоняет атаки против API Studio |

Принцип физической изоляции (см. `docs/architecture/01-02-PHYSICAL-ISOLATION.md`):
ценные данные и модель — на одной машине, атакующий/эксперименты — на другой.

## Где что лежит на Studio

```
~/ZCodeProject/Krepost_Z.codeProject/
├── vault/                     # база знаний Obsidian (дом долговременной памяти)
│   ├── 00-System/ … 99-Templates/
│   └── ...
├── data/
│   ├── chroma/                # persistent ChromaDB (эмбеддинги vault), metric=cosine
│   ├── trust_registry.db      # SQLite доверенных запросов
│   └── memory/                # (план) episodic-память ELMUR: JSONL+NPY
├── krepost/                   # код (в т.ч. старые архdoки 01-ARCHITECTURE и т.п.)
└── serve_lmstudio.py          # боевой API-сервер
```

- **vault физически на Studio.** Это единственный «дом» знаний. MacBook может
  держать пустую зеркальную структуру папок для оффлайн-редактирования, но
  источник истины и индекс — на Studio.
- **ChromaDB физически на Studio** (`data/chroma`, PersistentClient). Эмбеддер
  BGE-M3 тоже крутится на Studio (рядом с базой, чтобы не гонять векторы по сети).

## Кто и как ходит к памяти

```
MacBook Air (клиент)                     Mac Studio (дом памяти)
┌──────────────────┐   Thunderbolt      ┌──────────────────────────────┐
│  curl / клиент   │   10.0.0.x         │  Krepost HTTP API :8000       │
│  Ataker-boop     │ ─────────────────▶ │   └─ Orchestrator.handle()    │
└──────────────────┘   HTTP :8000       │       ├─ Security (L1–L4)     │
                                        │       ├─ MemoryStore.retrieve │
                                        │       │    └─ BGE-M3 + Chroma  │
                                        │       └─ LM Studio (main+guard)│
                                        └──────────────────────────────┘
```

1. Клиент на MacBook шлёт запрос на `http://10.0.0.1:8000/v1/query` по
   Thunderbolt-мосту (сеть `10.0.0.x`, см. диагностику Thunderbolt Bridge).
2. На Studio запрос проходит security-слои, затем **MemoryStore** достаёт
   релевантные куски из локальной ChromaDB (эмбеддинг запроса — BGE-M3 на Studio).
3. Контекст подмешивается в промпт основной модели (тоже на Studio, в LM Studio).
4. Ответ уходит обратно на MacBook. **Векторы и заметки Studio не покидают** —
   по сети идут только текст запроса и текст ответа.

## Почему так

- **Память рядом с моделью и эмбеддером** — нет сетевых прыжков на каждый чанк,
  retrieval near-zero по латентности (Thunderbolt + локальный Chroma).
- **MacBook как атакующий** не должен иметь доступа к сырой базе — он бьёт по
  тому же API, что и легитимный клиент, и видит только то, что API отдаёт после
  всех фильтров. Отравлять базу он может лишь через ingest-guard (что и тестируем).
- **Один дом памяти** упрощает бэкап и governance: снял `vault/` + `data/chroma`
  с Studio — забрал всю долговременную память.

## Связь с будущими фазами

- **Phase 3 (MemoryRouter):** доменные индексы — это подпапки `vault/`, все на
  Studio; роутер/reranker тоже на Studio (лёгкие), основная модель — последняя.
- **Phase 4 (`HierarchicalDomainRAG`):** DomainScout[] + ContextReader[] +
  EvidenceGrader под Supervisor — канон
  [`_handoff/HIERARCHICAL_DOMAIN_RAG_SPEC.md`](../../_handoff/HIERARCHICAL_DOMAIN_RAG_SPEC.md).
  На Studio; MacBook — клиент. Не путать с Phase 3 (DomainRouter only).
