# Attacker model drop-in (Air / SSD)

Сюда **не** кладём боевые модели Крепости. Только dirty-zone attacker / judge.

## Канон (выбор оператора)

| Роль | Модель | Quant | Размер | HF |
|------|--------|-------|--------|-----|
| **Attacker / judge** | **Dolphin3-Cyber-8B** (Llama3.1-8B abliterated) | **Q4_K_M** | ~4.9 GB | [`RavichandranJ/Dolphin3-Cyber-8B-GGUF`](https://huggingface.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF) |
| Executor (опц. 2-й слот) | Llama-3.2-3B-Instruct-abliterated | Q4_K_M | ~2.1 GB | по необходимости |
| Sandbox guard | Qwen3Guard-Gen-4B | Q4 | — | LM Studio; **не** uncensored |

Файл GGUF: `Dolphin3.0-Llama3.1-8B-abliterated.Q4_K_M.gguf`

## Куда класть

```text
/Volumes/AtakerDirty/Ataker/models/
  Dolphin3.0-Llama3.1-8B-abliterated.Q4_K_M.gguf
```

Ярлык: `~/Ataker-SSD/models/`.

**Не** писать на том Time Machine «WD_BLACK Атакер» — только `AtakerDirty`.

## Скачать (Air)

```bash
# из корня репо, том смонтирован
bash scripts/download_dolphin_air.sh
```

Или LM Studio → Discover → `RavichandranJ/Dolphin3-Cyber-8B-GGUF` → **Q4_K_M** → скопировать/symlink в `models/`.

## Load + env

1. LM Studio на Air: Load GGUF → Local Server `http://127.0.0.1:1234/v1`.
2. Запомнить `id` модели в UI.

```bash
source ~/Ataker-SSD/env.sh   # если есть
export ATAKER_JUDGE_URL=http://127.0.0.1:1234
export ATAKER_JUDGE_MODEL=<id из LM Studio>   # часто содержит dolphin / Dolphin3
curl -s http://127.0.0.1:1234/v1/models | head
```

## Прогон с судьёй

```bash
./scripts/serve_sandbox_air.sh                    # терм. 1 → :8010
JUDGE=1 LIMIT=5 ./scripts/smoke_ataker_judge_air.sh   # терм. 2
# или:
JUDGE=1 LIMIT=5 ./scripts/ataker_sandbox_air.sh
```

Отчёт: `data/ataker_sandbox/` или `$SSD/reports`. Studio `:8000` не трогать без `FORCE_STUDIO=1`.

## Запреты

- Не грузить uncensored как **guard** песочницы — только attacker/judge.
- Не бить Studio `:8000` без `FORCE_STUDIO=1`.
- Не писать модели на Time Machine «WD_BLACK Атакер».
