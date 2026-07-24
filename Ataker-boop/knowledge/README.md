# Ataker knowledge — база для Творца / Red Team

Markdown, который оператор и агент пополняют вручную.  
Позже индексируется в Chroma (шаг 9 плана harness). **Сейчас = файлы + каталог.**

## Как добавлять

1. Новый вектор / техника → файл в нужной папке (см. дерево) или строка в `SOURCES.md`.
2. Frontmatter по шаблону в `00-TEMPLATE.md`.
3. В плане harness §4 «Твой вход» — одна строка, что добавил.
4. **Не класть** боевые эксплойты с Exploit-DB целиком — только разбор структуры / ссылка / маппинг на наш арсенал (см. `sources/04-exploit-db.md`).

## Дерево

```
knowledge/
├── README.md                 ← ты здесь
├── SOURCES.md                ← канон внешних баз (OWASP / PortSwigger / MITRE / Exploit-DB)
├── 00-TEMPLATE.md
├── sources/                  ← выжимки + маппинг на AttackCategory / слои Крепости
│   ├── 01-owasp-llm-top10.md
│   ├── 02-portswigger.md
│   ├── 03-mitre-attack.md
│   └── 04-exploit-db.md
├── attack_techniques.md      ← живой индекс техник
├── defense_krepost.md        ← как устроена жертва (для Творца = чёрный ящик + слабости)
├── case_studies.md
├── layers/                   ← слабости L1–L4
└── ingested/                 ← сюда кидаешь сырьё из чатов/статей
```

## Зеркало для Крепости (defense)

Атакующие базы здесь. **Защитные** (митации, паттерны, детекторы) — в  
`docs/security/knowledge-bases/` и кратко в `defense_krepost.md`.  
Оператор сказал, что нашёл такие же сильные базы для Крепости — складывай ссылки туда + §4 плана.

## Связь с кодом

| Поле frontmatter | Куда в harness |
|------------------|----------------|
| `category` | `AttackCategory` / `PlannedAttack.template_category` |
| `mutations` | имена из `MutationEngine` |
| `owasp` / `mitre` | теги в отчёте / `technique_ref` |
| `krepost_layer` | гипотеза оператора (в Planner **не** как утечка layer из HTTP) |
