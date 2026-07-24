# Десерт — сложное на потом

> Unlock код: **не раньше 2026-09-12** (после учёбы + фильтра).  
> Это и есть то, что я «резал» из NOW: не выкинул — перенёс сюда с датами.

## Волна 1 (12–25 Sep 2026)

| ID | Что | Файлы (когда дойдём) | Deadline |
|----|-----|----------------------|----------|
| **C1** | LLM Planner (abliterated на Air) | `ataker/planner.py` | **2026-09-18** |
| **C2** | Multi-turn FITD/Crescendo skeleton | `ataker/strategies/multi_turn.py` | **2026-09-25** |

Почему десерт: без понятого stub + KB это будет «магия», а не harness.

## Волна 2 (26 Sep – 9 Oct 2026) — можно сдвинуть

| ID | Что | Файлы | Deadline |
|----|-----|-------|----------|
| **D1** | YAML/JSON strategy packs | `ataker/strategies/*.yaml` | **2026-10-02** |
| **D2a** | Chroma RAG поверх `knowledge/` | loader → Chroma | **2026-10-09** |
| **D2b** | AuthManager L2–L5 → Planner gate | wire auth | **2026-10-09** |

## Намеренно НЕ в десерт первой очереди

| Тема | Куда | Почему |
|------|------|--------|
| Форк PyRIT / garak runtime | `harness/no-mono-repo.md` | принцип H7 — паттерны, не mono |
| Inspect AI full runtime | `harness/inspect-ai-later.md` | eval-регресс после ASR-цикла |
| Переписать Крепость на LangGraph | ❌ не делаем | LC/LI = чеклист угроз, не миграция |

Указатели деталей: файлы в `docs/deferred/harness/`.
