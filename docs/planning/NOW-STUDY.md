# NOW — что учить сейчас (до десерта)

> До **2026-08-28** цель = **понять**, не «внедрить всё».  
> Код десерта (LLM Planner, multi-turn, Chroma…) — после фазы B.  
> Парковка «потом»: `docs/deferred/`.

## Порядок (не прыгай)

### 1. Атака (до 31 Jul / 7 Aug)

| # | Материал | Где | Зачем сейчас |
|---|----------|-----|--------------|
| 1 | OWASP LLM Top 10 2025 PDF | `Ataker-boop/knowledge/SOURCES.md` §1 | словарь рисков |
| 2 | PortSwigger Web LLM attacks | §2 | сценарии против Крепости |
| 3 | MITRE ATLAS | §3 | AI TTPs |
| 4 | PortSwigger Logic + Access | §2 | мышление цепочкой (не все labs) |

Карточки уже есть: `knowledge/sources/01…03-*.md` — читай + правь, не плоди дубли.

### 2. Защита (до 14 Aug)

| # | Материал | Где | Зачем сейчас |
|---|----------|-----|--------------|
| 1 | NIST CSF 2.0 — Protect/Detect/Respond | `docs/security/knowledge-bases/SOURCES.md` | слои Крепости |
| 2 | SRE Monitoring + Cascading Failures | там же | асимметрия / не упасть под redteam |
| 3 | Azure AI security best practices (обзор) | там же | идеи L1–L4 / agency |

**Отложено в deferred:** полный CNCF/K8s deep-dive, полный Azure network hardening.

### 3. Память и tools — для обоих (до 21 Aug)

| # | Материал | Где |
|---|----------|-----|
| 1 | LangChain going-to-production ⭐ | `vault/.../frameworks/langchain_memory_tools.md` |
| 2 | LC short/long memory + tools | тот же файл |
| 3 | LlamaIndex Memory + blocks + tools | `llamaindex_memory_tools.md` |
| 4 | Таблица attack vs defense | `frameworks/FOR_BOTH.md` |

### 4. То, что уже в коде (до 28 Aug)

```bash
./scripts/serve_sandbox_air.sh
DRY=1 ./scripts/ataker_harness.sh
# или: PYTHONPATH=Ataker-boop python3 -m ataker.harness --dry-run
```

Понять руками: `FeedbackEntry` (без layer), `PlannedAttack`, `StubPlanner`, `adversarial_loop`, `knowledge_loader`.

Слои жертвы: `Ataker-boop/knowledge/layers/`, `defense_krepost.md`.

---

## Чеклист оператора (фаза A)

- [ ] A1 OWASP + PS LLM + ATLAS
- [ ] A2 Logic + Access
- [ ] A3 NIST + SRE Monitoring/Cascading
- [ ] A4 LC/LI memory-tools
- [ ] A5 stub harness dry-run понятен
- [ ] Ни один пункт десерта C/D не начат «потому что интересно»

## После учёбы → фильтр (фаза B)

Отметь в трёх `SOURCES.md`. Всё ⏸/❌ уезжает осознанно в `docs/deferred/` (уже разложено; фильтр только подтверждает).
