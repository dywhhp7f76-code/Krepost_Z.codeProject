# КАНОН ОПЕРАТОРА: Hierarchical Domain-Specialist RAG (Krepost)

> **Статус:** канон оператора (2026-07-18). **LOCKED.**  
> **Индустриальное имя класса:** Hierarchical / Multi-Agent Domain-Specialist RAG.  
> **Кодовое имя в Крепости:** `HierarchicalDomainRAG` (Phase 4).  
> **Приоритет:** этот файл > ROADMAP-пересказы > «как я понял» любого агента.  
> Phase 3 (`MEMORY_ROUTER_SPEC`) = фундамент доменов, **не** закрытие Phase 4.  
> Менять канон / переименовывать роли / «упрощать смысл» — **только** явная фраза
> оператора: `Разрешаю переписать канон HierarchicalDomainRAG`.  
> Без этой фразы — **STOP**. Не «улучшать формулировки». Не «синонимизировать».

---

## ⛔ FREEZE VOCABULARY (не переименовывать)

Эти **английские идентификаторы** — API-контракт. В коде, тестах, PR, ROADMAP
использовать **только их**. Бытовые слова (дорожник, доска, этаж, библиотека)
**запрещены** в новых доках и коммит-сообщениях — они уже один раз породили
пересказ «как понял модель».

| ID (LOCKED) | Что это | Синонимы ЗАПРЕЩЕНЫ как замена ID |
|-------------|---------|----------------------------------|
| `Supervisor` | main LLM: SearchBrief, grade loop, ответ юзеру | голова, оркестратор*, мозг, master |
| `SearchBrief` | JSON/dataclass: anchors + domains + round | доска, план, задание, query plan* |
| `DomainScout` | лёгкий агент **одного** `domain_id` | дорожник, хранитель*, worker*, retriever* |
| `ContextReader` | ≤2 OCC-style extractors | читатель, summarizer*, dossier agent* |
| `EvidenceGrader` | relevant / partial / irrelevant | редактор, судья*, filter* |
| `HybridRetriever` | vector + BM25 + rerank **внутри domain** | курьер*, memory_search (без domain) |
| `HierarchicalDomainRAG` | имя всей Phase 4 системы | агенты-хранители*, MemoryRouter (это Phase 3) |

\* Слово можно упомянуть в скобках один раз при первом появлении; **нельзя**
подменять им ID в заголовках модулей, class names, «мы сделали хранителей».

**Правило лепрекона:** если агент пишет «по сути это то же самое, что X, назовём
иначе / упростим» — это **нарушение канона**, не рефакторинг. Reject.

**Правило проверки PR:** в diff Phase 4 обязаны встречаться строки
`DomainScout`, `SearchBrief`, `ContextReader`, `EvidenceGrader`.  
Если их нет, а есть только `retrieve` / `MemoryRouter` — Phase 4 **не сделана**.

---

## Системное имя и поток

```
UserQuery
  → Supervisor (main LLM)          # пишет SearchBrief
  → DomainScout[] (лёгкие агенты)  # по 1 на domain/юрисдикцию vault
  → ContextReader[] (≈2)           # OCC-style extract / dossier
  → EvidenceGrader                 # «инфа к вопросу?»
  → Supervisor                     # accept | refine SearchBrief | answer
       ↑______________reject/refine loop (max N)_____________|
```

Пользователю отвечает **только Supervisor**. Scout/Reader наружу не говорят.

---

## Компоненты (имена для кода)

| Компонент | Предлагаемый модуль | Должен | Запрещено |
|-----------|---------------------|--------|-----------|
| **Supervisor** | `krepost/orchestration/` + main backend | SearchBrief, оценка evidence, финальный ответ, лимит loop | сам ходить по всей Chroma |
| **SearchBrief** | dataclass / JSON artifact | список query-якорей + target domains (1..K) | путать с ответом юзеру |
| **DomainScout** | `krepost/memory/domain_scout.py` | hybrid retrieve **только** в своём `domain`; вернуть paths/chunk ids | финальный ответ; чужие domains |
| **ContextReader** | `krepost/memory/occ_reader.py` (пул ≤2) | выжимка/досье по путям Scout | ответ пользователю |
| **EvidenceGrader** | `krepost/memory/evidence_grader.py` | relevant / partial / irrelevant к вопросу | замена Supervisor |
| **HybridRetriever** | расширение `MemoryStore` | vector + BM25 + rerank внутри domain | один global flat search «на всё» |
| **DomainRouter** | уже есть Phase 3 | первичный shortlist domains | выдавать за DomainScout |

Сложный вопрос → тот же каркас + ToolAgent (`/v1/agent`), но `memory_search`
должен уважать domains / SearchBrief, не плоский поиск по всей базе.

---

## Контракт данных (минимум)

```text
SearchBrief:
  query_anchors: list[str]
  domains: list[domain_id]   # 1..K
  round: int                 # 0..max_rounds-1

ScoutHit:
  domain_id, doc_id, paths[], scores{}, chunk_ids[]

ReaderDossier:
  domain_id, summary_or_extract, citations[], confidence

GradeVerdict:
  status: relevant | partial | irrelevant
  missing_anchors: list[str]   # что дописать в SearchBrief
```

---

## Обязательные кирпичи до «Phase 4 done»

1. HybridRetriever: vector + BM25 + reranker (уже было в архдоках, в боевом коде нет).
2. Phase 3: живой `metadata.domain` (не вечный flat fallback).
3. DomainScout × N (лёгкие; не N×35B).
4. ContextReader pool ≈ 2 (OCC-RAG / малый SLM).
5. EvidenceGrader.
6. Supervisor loop с `max_rounds` (рекомендуется 1–2).
7. Один голос наружу = Supervisor.

---

## Anti-patterns (не засчитывать как реализацию)

1. Один глобальный `retrieve()` без DomainScout.
2. «Phase 3 MemoryRouter = Phase 4 готово».
3. Supervisor сам query'ит всю коллекцию вместо Scout.
4. DomainScout отвечает пользователю своим текстом.
5. Нет ContextReader — сырой dump чанков в Supervisor.
6. Нет EvidenceGrader / loop (или бесконечный loop).
7. Grader = только `min_relevance` float без «подходит ли к вопросу».
8. Один LLM-call «выбери документы из всего vault» вместо Scout[].

PR с anti-pattern → отклонять: `anti-pattern HierarchicalDomainRAG`.

---

## Связь

| Док | Роль |
|-----|------|
| `MEMORY_ROUTER_SPEC.md` | Phase 3 foundation (domain filter + router) |
| `ROADMAP.md` Phase 4 | ссылка на этот канон |
| `MEMORY_TOPOLOGY.md` | Studio = дом vault/Chroma |
| OccReader | кандидат ContextReader |
| `/v1/agent` | сложный режим, не замена DomainScout |

---

## One-liner для агентов (копипаста, не пересказывать)

```
HierarchicalDomainRAG: Supervisor→SearchBrief→DomainScout[]→ContextReader[]→EvidenceGrader→Supervisor(loop).
IDs LOCKED. No rename. No "essentially the same as flat retrieve". Phase3≠Phase4.
Need operator: «Разрешаю переписать канон HierarchicalDomainRAG» to change this file.
```
