# Attacker model drop-in (Air / SSD)

Сюда **не** кладём боевые модели Крепости. Только dirty-zone attacker.

## Куда класть GGUF

На томе `AtakerDirty`:

```text
/Volumes/AtakerDirty/Ataker/models/
  <name>.gguf
```

Ярлык: `~/Ataker-SSD/models/`.

## После того как модель найдена

1. Скопировать `.gguf` в `models/`.
2. В LM Studio на Air: Load → указать этот файл (или symlink).
3. В shell:

```bash
source ~/Ataker-SSD/env.sh
export ATAKER_JUDGE_URL=http://127.0.0.1:1234   # LM Studio OpenAI API
export ATAKER_JUDGE_MODEL=<id из LM Studio>
```

4. Прогон с судьёй:

```bash
JUDGE=1 LIMIT=33 ./scripts/ataker_sandbox_air.sh
# или
python scripts/ataker_hit_http.py --url http://127.0.0.1:8010 \
  --seed Ataker-boop/seed_attacks.local.jsonl --limit 33 --judge
```

## Кандидаты (оператор выбирает)

- **Llama-3.1-8B-Instruct-abliterated** Q5_K_L (~5.64 GB) — основной атакер и judge.
- **Llama-3.2-3B-Instruct-abliterated** Q4_K_M (~2.09 GB) — второй слот (executor).
- Не грузить uncensored как guard песочницы — только attacker/judge.

## Запреты

- Не бить Studio `:8000` без `FORCE_STUDIO=1`.
- Не писать на том Time Machine «WD_BLACK Атакер» — только `AtakerDirty`.
