# Knowledge bases для Крепости (defense)

Зеркало атакующих баз Атакера — **со стороны защиты**.  
Атака: `Ataker-boop/knowledge/`. Защита: здесь.

## Читать и фильтровать сначала

👉 **[`SOURCES.md`](./SOURCES.md)** — живые ссылки:

| База | Зачем Крепости |
|------|----------------|
| **NIST CSF 2.0** | глубина защиты, Govern→Recover, мониторинг |
| **CNCF Security** | изоляция контейнеров/процессов, lifecycle |
| **Google SRE Book** | Monitoring, Alerting, Cascading Failures |
| **Azure AI / LLM security** | практики защиты ИИ-сервисов и API |
| **LangChain / LlamaIndex** | memory isolation, tools HITL, shared-memory injection |

Оператор отмечает ✅/⏸/❌ → потом карточки в `sources/`.  
Уже загружено: `sources/05-langchain-llamaindex.md` (канон в vault `Agents_Engineering/frameworks/`).

## Симметрия с Атакером (уже в Red Team KB)

| Атакер | Defense (сюда) |
|--------|----------------|
| OWASP LLM Top 10 | митигации по LLM0x |
| PortSwigger | hardening Injection/Access/Logic на API |
| MITRE ATT&CK / ATLAS | detections / mitigations |
| Exploit-DB | паттерны для L1 / регресса |

Атакующие ссылки: `Ataker-boop/knowledge/SOURCES.md`.

## Куда ляжет в код после фильтра

| Риск / тема | Куда в Крепости |
|-------------|-----------------|
| Prompt Injection | `krepost/security/pipeline.py` L1–L2 |
| Output / agency | L4, harness tools, UrlGuard |
| Monitoring / alerts | metrics, Netdata proposal, Telegram later |
| Cascading failures | rate limit, fail-closed, launchd health |
| Isolation | Air↔Studio, sandbox `:8010`, Tailscale |

## Оператор добавляет ещё ↓

- [ ] YYYY-MM-DD | название | URL | зачем _

**Канон Крепости:** этот каталог (`krepost/07-RESEARCH/knowledge-bases/`).  
**Отложено:** `krepost/07-RESEARCH/deferred/defense/`.  
**Планирование (если есть в ветке):** `docs/planning/CALENDAR.md`.

План harness §4 тоже принимает defense-строки:  
`Ataker-boop/design/2026-07-24-ataker-harness-optimization.md`
