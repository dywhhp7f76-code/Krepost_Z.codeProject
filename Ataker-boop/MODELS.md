# Attacker models — подготовка на Air (сначала готовка, потом бой)

Сюда **не** кладём боевые модели Крепости. Только dirty-zone.

> **Порядок:** скачать → положить на SSD → Load в LM Studio → выставить env →  
> проверить `/v1/models` → **только потом** песочница/smoke.  
> Бой по Studio `:8000` — отдельно и явно (`FORCE_STUDIO=1`), не сейчас.

## Две роли (канон подготовки)

| Роль | Кто | Модель | Quant | ~размер | HF |
|------|-----|--------|-------|---------|-----|
| **1. Творец (Planner)** | пишет стратегии / атаки / judge | **Dolphin3-Cyber-8B** | **Q4_K_M** | ~4.9 GB | [`RavichandranJ/Dolphin3-Cyber-8B-GGUF`](https://huggingface.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF) |
| **2. Исполнитель (Executor)** | «стреляет» payload'ами / лёгкий слот | **Llama-3.2-3B-Instruct-abliterated** | **Q4_K_M** | ~2.0 GB | [`QuantFactory/Llama-3.2-3B-Instruct-abliterated-GGUF`](https://huggingface.co/QuantFactory/Llama-3.2-3B-Instruct-abliterated-GGUF) |
| Sandbox guard | Layer 2 песочницы | Qwen3Guard-Gen-4B | Q4 | — | LM Studio; **не** uncensored |

### Файлы GGUF

```text
/Volumes/AtakerDirty/Ataker/models/
  Dolphin3.0-Llama3.1-8B-abliterated.Q4_K_M.gguf          # Planner / judge
  Llama-3.2-3B-Instruct-abliterated.Q4_K_M.gguf           # Executor
```

Ярлык: `~/Ataker-SSD/models/`.  
**Не** писать на том Time Machine «WD_BLACK Атакер» — только `AtakerDirty`.

> В спеке Planner-Executor: Executor **сейчас** = код (`MutationEngine` + HTTP hit).  
> Второй GGUF готовим **заранее**, чтобы слот был на диске, когда harness включит LLM-executor / второй endpoint. Пока бой не гоняем.

## Шаг A — скачать оба (Air)

```bash
# том AtakerDirty смонтирован
bash scripts/download_ataker_models_air.sh
# или по одному:
bash scripts/download_ataker_models_air.sh --planner
bash scripts/download_ataker_models_air.sh --executor
```

Алиас: `scripts/download_dolphin_air.sh` → только Planner (совместимость).

## Шаг B — Load в LM Studio (ещё не бой)

1. Load **оба** GGUF (или Planner сейчас, Executor в zoo на диске).
2. Local Server: `http://127.0.0.1:1234/v1` (один сервер; ids разные).
3. Запомнить ids из UI / `curl …/v1/models`.

```bash
# пример env (подставь свои id из LM Studio)
export ATAKER_LMSTUDIO_URL=http://127.0.0.1:1234/v1
export ATAKER_PLANNER_MODEL=<id Dolphin / Planner>
export ATAKER_EXECUTOR_MODEL=<id Llama-3.2-3B / Executor>
export ATAKER_JUDGE_URL=http://127.0.0.1:1234
export ATAKER_JUDGE_MODEL="${ATAKER_PLANNER_MODEL}"   # judge = Творец, пока так

curl -s "${ATAKER_LMSTUDIO_URL}/models" | head
# чеклист: оба id видны → готовка моделей OK
```

Можно положить в `~/Ataker-SSD/env.sh` и `source` его.

## Шаг C — готовность (чеклист, без ударов)

- [ ] Оба `.gguf` в `AtakerDirty/Ataker/models/`
- [ ] LM Studio отдаёт ids Planner (+ Executor, если загружен)
- [ ] `ATAKER_PLANNER_MODEL` / `ATAKER_JUDGE_MODEL` заданы
- [ ] Песочница ещё **не** обязана быть up — это следующий этап

## Шаг D — потом (не сейчас в этой задаче)

Только когда A–C зелёные:

```bash
./scripts/serve_sandbox_air.sh
JUDGE=1 LIMIT=5 ./scripts/smoke_ataker_judge_air.sh
```

Studio `:8000` — не трогать без явной команды.

## Запреты

- Uncensored **не** как sandbox guard.
- Не бить Studio без `FORCE_STUDIO=1`.
- Не писать модели на «WD_BLACK Атакер» (Time Machine).
