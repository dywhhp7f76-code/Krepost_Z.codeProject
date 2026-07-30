# Индекс техник атак (живой)

Сводка. Детали — в `sources/` и отдельных карточках по `00-TEMPLATE.md`.

| technique | tier | category | owasp | mitre-ish | status |
|-----------|------|----------|-------|-----------|--------|
| _(добавляй строки)_ | | | | | |

Стартовый набор из арсенала кода (`ATTACK_TEMPLATES` + research В):

| technique | category | owasp | note |
|-----------|----------|-------|------|
| direct_ignore_instructions | direct_injection | LLM01:2025 | L1 templates |
| role_dan_aim | role_hijack | LLM01:2025 | low priority (В.11) |
| system_prompt_repeat | system_prompt_leak | LLM07:2025 | |
| fitd_multiturn | multi_turn | LLM01:2025 | Tier-S, human |
| crescendo_escalate | multi_turn | LLM01:2025 | session |
| social_prefix_innocent | social_engineering | LLM01:2025 | + mutation |
| rag_poison_seed | _(ingest)_ | LLM04:2025 | ROADMAP |
| tool_agency_abuse | _(agent)_ | LLM06:2025 | `/v1/agent` |
