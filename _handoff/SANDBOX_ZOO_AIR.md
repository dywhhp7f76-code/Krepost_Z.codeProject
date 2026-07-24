# Песочница / зоопарк моделей на Air (договорённость 2026-07-18)

> Зафиксировано перед сном оператора. Не путать с боевым Studio.
>
> **ЖЁСТКО (оператор 2026-07-18 вечер):** слово **«Крепость»** = только Studio
> `:8000` + её модели + её vault/chroma. Это **не** зоопарк и **не** Air `:8010`.
> Проверять / чинить / смоучить «Крепость» — на Studio. Air-зоопарк — отдельно,
> только когда оператор явно сказал «зоопарк» / «песочница Air».

## Роли машин

| Машина | Роль |
|--------|------|
| **Mac Studio** | **Крепость** `:8000`, vault + chroma + main/guard. **Не** зоопарк. |
| **MacBook Air (SSD)** | Зоопарк GGUF + Ataker + песочница API `:8010` — **не** Крепость. |

## Идея оператора

Зоопарк моделей на SSD Air + Ataker на `:8010`. Это песочница под смену GGUF,
**не** проверка Крепости. Боевой Studio зоопарком не портить и не подменять.

## Как (консенсус из чата)

1. Крепость-песочница на Air: порт **`8010`**, host **`127.0.0.1`** only.
2. Отдельные пути (не sync с Studio `data/`):
   - `KREPOST_CHROMA_DIR=data/chroma_sandbox`
   - `KREPOST_EPISODIC_DIR=data/memory_sandbox`
   - `KREPOST_VAULT=vault_sandbox` (пустой / маленькая копия)
3. LM Studio на Air → `KREPOST_LMSTUDIO_URL=http://127.0.0.1:1234/v1`
4. Смена ИИ: новая GGUF в LM Studio → новый `KREPOST_MAIN_MODEL` → рестарт uvicorn.
5. **Ataker** бьёт `http://127.0.0.1:8010`, **не** `10.0.0.1:8000`.
6. Guard в песочнице — нормальный маленький; uncensored только как main для тестов.
7. Скрипт `scripts/serve_sandbox_air.sh` — **есть**.

```bash
# из корня Krepost_Z.codeProject, LM Studio уже на :1234
chmod +x scripts/serve_sandbox_air.sh
./scripts/serve_sandbox_air.sh

# смена ИИ в зоопарке:
KREPOST_MAIN_MODEL=some-gguf-id ./scripts/serve_sandbox_air.sh
```

Health: `curl -s http://127.0.0.1:8010/health`  
Ataker base URL: `http://127.0.0.1:8010`

## Боевой стек Studio (на момент фиксации) — не ломать зоопарком

- API `:8000`, launchd `com.hervam.krepost.serve`
- MemoryRouter + hybrid + episodic + agent
- `metadata.domain` backfill на 49 чанков сделан
- Канон Phase 4: `_handoff/HIERARCHICAL_DOMAIN_RAG_SPEC.md` (LOCKED IDs)

## Ataker на песочнице

```bash
./scripts/serve_sandbox_air.sh          # терминал 1
./scripts/ataker_sandbox_air.sh         # терминал 2 → :8010
# отчёт: data/ataker_sandbox/report_*.json
# Studio :8000 скрипт отвергает без FORCE_STUDIO=1
```

## Round Table (Air)

Канон: `_handoff/ROUNDTABLE_DEBRIEF_SPEC.md`. UI **не** Studio `:8000`.

```bash
./scripts/serve_roundtable_air.sh
# http://127.0.0.1:8011/roundtable
# default DebriefMode (ROUNDTABLE_ATTACK_LOCKED=1)
```

## Следующее

1. ~~`scripts/serve_sandbox_air.sh`~~ ✅
2. ~~DomainScout / ContextReader / EvidenceGrader scaffold~~ ✅ (Probnoki #56)
3. ~~Wire HierarchicalDomainRAG в `serve_lmstudio`~~ ✅
4. ~~Ataker → localhost:8010~~ ✅ (`scripts/ataker_sandbox_air.sh`)
5. ~~Supervisor-LLM пишет SearchBrief~~ ✅
6. ~~HierarchicalTrace в /v1/query metadata~~ ✅ (Probnoki #57)
7. ~~ContextReader + OccReader pool~~ ✅
8. Live smoke Air: sandbox + ataker + ingest vault_sandbox
9. ~~Round Table scaffold~~ ✅ (`serve_roundtable_air.sh`, Probnoki #60)
10. Wire LLM speakers + SealedRedLoop nightly → receipts
