# Десерт — сложное на потом

> Unlock код: **с 2026-09-08** (конец фазы I: учёба+фильтр), или раньше если фаза I закрыта досрочно.  
> Жёсткий потолок фазы II: **2026-10-23** (= 8 Sep + 45 дней).

Старт календаря: **2026-07-25**. Формула: +45 → ① · +45 → ②. См. `docs/planning/CALENDAR.md`.

## Волна внутри фазы II (8 Sep → 23 Oct)

| ID | Что | Файлы (когда дойдём) | Deadline |
|----|-----|----------------------|----------|
| **C1** | LLM Planner (abliterated на Air) | `ataker/planner.py` | **2026-09-22** |
| **C2** | Multi-turn FITD/Crescendo skeleton | `ataker/strategies/multi_turn.py` | **2026-10-06** |
| **D1** | YAML/JSON strategy packs | `ataker/strategies/*.yaml` | **2026-10-14** |
| **D2a** | Chroma RAG поверх `knowledge/` | loader → Chroma | **2026-10-23** |
| **D2b** | AuthManager L2–L5 → Planner gate | wire auth | **2026-10-23** |

Почему десерт: без понятого stub + KB это будет «магия», а не harness.

## Намеренно НЕ в десерт первой очереди

| Тема | Куда | Почему |
|------|------|--------|
| Форк PyRIT / garak runtime | `harness/no-mono-repo.md` | принцип H7 — паттерны, не mono |
| Inspect AI full runtime | `harness/inspect-ai-later.md` | eval-регресс после ASR-цикла |
| Переписать Крепость на LangGraph | ❌ не делаем | LC/LI = чеклист угроз, не миграция |

Указатели деталей: файлы в `docs/deferred/harness/`.
