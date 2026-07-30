# База Атакера — арсенал для Ataker-Boop

Грязная зона (съёмный SSD / Air). Сырьё и нормализованные атаки **не коммитятся**.
Скрипт только воспроизводит сборку на машине оператора.

## Контракт

| Параметр | Значение |
|----------|----------|
| Корень | `$FORTRESS_DATA` (default `/fortress_data/attacker`) |
| Форматы | `.jsonl` / `.json` / `.parquet` / `.jsonl.gz` |
| Бюджет | ≤ 2.0 GB суммарно |
| Extras | ≤ 3 датасета, каждый ≤ 400 MB |
| Вне скоупа | Exploit-DB, крипта, выживание, пожары, полный `hh-rlhf` |
| Карантин | `_incoming/` → `normalized/attacks.jsonl` |

## Обязательные источники

1. `Anthropic/hh-rlhf` → только `red-team-attempts`
2. `allenai/real-toxicity-prompts` → `prompts.jsonl` (в нормализацию: toxicity ≥ 0.5)
3. `toxigen/toxigen-data` → annotated/train export (сэмпл, если >800 MB)

## Запуск

```bash
python3 -m venv /fortress_data/.venv
/fortress_data/.venv/bin/pip install datasets huggingface_hub pyarrow pandas
sudo mkdir -p /fortress_data/attacker && sudo chown "$USER" /fortress_data/attacker

export FORTRESS_DATA=/fortress_data/attacker
/fortress_data/.venv/bin/python Ataker-boop/scripts/build_attacker_base.py
```

Проверка:

```bash
python -c "assert open('/fortress_data/attacker/normalized/attacks.jsonl',encoding='utf-8').read().count('\\n')>0"
du -h /fortress_data/attacker
```

## Схема `normalized/attacks.jsonl`

```json
{
  "id": "<source>:<hash16>",
  "source": "anthropic_redteam|real_toxicity|toxigen|...",
  "category": "<AttackCategory>",
  "text": "...",
  "success_signal": null,
  "raw_meta": {"needs_review": true}
}
```

Категории = enum из `ataker/generator.py` (`AttackCategory`).

## Прогон 2026-07-29 (этот агент)

| Метрика | Значение |
|---------|----------|
| Строк | 74 995 |
| Диск | ~196 MB / 2048 MB |
| Extras | `deepset/prompt-injections`, `JasperLS/prompt-injections`, `TrustAIRLab/in-the-wild-jailbreak-prompts` |

По источникам: anthropic_redteam 38234 · real_toxicity 21649 · toxigen 8960 · in-the-wild jailbreaks 5490 · prompt-injections 662.

Манифест и REJECTED лежат рядом с данными: `$FORTRESS_DATA/manifest.json`, `$FORTRESS_DATA/REJECTED.md`.

## Импорт в Attack Vault

```bash
export FORTRESS_DATA=/fortress_data/attacker
PYTHONPATH=Ataker-boop python Ataker-boop/scripts/import_attacker_base.py \
  --vault Ataker-boop/vault_data/attacks.db \
  --limit 5000
```

Прогон из vault (после подключения живой модели на Studio/Air):

```python
from ataker import RedTeamLoop, AttackVault

vault = AttackVault("Ataker-boop/vault_data/attacks.db")
loop = RedTeamLoop(
    pipeline=pipeline,
    vault=vault,
    success_mode="content",          # Risk 3
    main_generate=main_async_fn,     # живая Main
    hard_cap=1000,                   # Risk 2
    cooldown_sec=30,                 # continuous
)
report = await loop.run_from_vault(max_attacks=200)
print(report.summary())
```

Дальше: ручной gate (`_incoming` → poison/clean) по `docs/architecture/training/TRAINING_SANDBOX.md`.
