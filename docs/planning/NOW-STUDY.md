# NOW — что учить сейчас (фаза I, 45 дней)

> **Старт:** 2026-07-25 · **Потолок фазы I:** **2026-09-08** (+45 дней).  
> Цель = **понять**, не «внедрить всё». Раньше закрыл — раньше десерт.  
> Код десерта — фаза II (8 Sep → 23 Oct). Парковка: `docs/deferred/`.

## Порядок (не прыгай)

### 1. Атака (ориентир до 1 / 8 Aug)

| # | Материал | Где | Зачем сейчас |
|---|----------|-----|--------------|
| 1 | OWASP LLM Top 10 2025 PDF | `Ataker-boop/knowledge/SOURCES.md` §1 | словарь рисков |
| 2 | PortSwigger Web LLM attacks | §2 | сценарии против Крепости |
| 3 | MITRE ATLAS | §3 | AI TTPs |
| 4 | PortSwigger Logic + Access | §2 | мышление цепочкой (не все labs) |

Карточки: `knowledge/sources/01…03-*.md`.

### 2. Защита (ориентир до 15 Aug)

| # | Материал | Где | Зачем сейчас |
|---|----------|-----|--------------|
| 1 | NIST CSF 2.0 — Protect/Detect/Respond | `docs/security/knowledge-bases/SOURCES.md` | слои Крепости |
| 2 | SRE Monitoring + Cascading Failures | там же | асимметрия / не упасть под redteam |
| 3 | Azure AI security best practices (обзор) | там же | идеи L1–L4 / agency |

**Отложено:** CNCF/K8s deep, полный Azure network — `docs/deferred/defense/`.

### 3. Память и tools — для обоих (ориентир до 22 Aug)

| # | Материал | Где |
|---|----------|-----|
| 1 | LangChain going-to-production ⭐ | `vault/.../frameworks/langchain_memory_tools.md` |
| 2 | LC short/long memory + tools | тот же файл |
| 3 | LlamaIndex Memory + blocks + tools | `llamaindex_memory_tools.md` |
| 4 | Таблица attack vs defense | `frameworks/FOR_BOTH.md` |

### 4. То, что уже в коде (ориентир до 29 Aug)

```bash
./scripts/serve_sandbox_air.sh
DRY=1 ./scripts/ataker_harness.sh
```

Понять: `FeedbackEntry`, `PlannedAttack`, `StubPlanner`, `adversarial_loop`, `knowledge_loader`.  
Слои: `Ataker-boop/knowledge/layers/`, `defense_krepost.md`.

### 5. Фильтр (к **8 Sep**)

Все три `SOURCES.md` → ✅/⏸/❌; тонкие карточки только по ✅.

---

## Чеклист фазы I

- [ ] A1 OWASP + PS LLM + ATLAS
- [ ] A2 Logic + Access
- [ ] A3 NIST + SRE Monitoring/Cascading
- [ ] A4 LC/LI memory-tools
- [ ] A5 stub harness понятен
- [ ] B фильтр SOURCES к **2026-09-08**
- [ ] Десерт не начат, пока фаза I не закрыта (кроме досрочки)
