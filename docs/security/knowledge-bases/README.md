# Knowledge bases для Крепости (defense)

Зеркало атакующих баз Атакера — **со стороны защиты**.  
Атака: `Ataker-boop/knowledge/`. Защита: здесь.

Оператор (2026-07-24): «нашел такие же пиздатые базы для крепости» — **допиши URL ниже**.

## Канон (стартовый, симметрия с Атакером)

| База | Зачем Крепости | URL / заметка |
|------|----------------|---------------|
| **OWASP LLM/GenAI Top 10** | чеклист митигаций по каждому LLM0x | https://genai.owasp.org/llm-top-10/ |
| **PortSwigger Academy** | как чинить Injection / Access / Logic на API и output path | https://portswigger.net/web-security |
| **MITRE ATT&CK** (defense) | detections / mitigations по тактикам | https://attack.mitre.org/ |
| **Exploit-DB** (defense read) | сигнатуры / паттерны для L1 и тестов регресса | https://www.exploit-db.com/ |

## Куда класть митигации в коде/доках

| Риск | Куда в Крепости |
|------|-----------------|
| Prompt Injection | `krepost/security/pipeline.py` L1–L2, guard prompts |
| Output handling | L4 / ToolOutputGuard |
| Data poisoning | ingest guards, quarantine, RELAI |
| Excessive agency | harness tools + UrlGuard |
| Embedding weaknesses | MemoryRouter / cosine thresholds |

## Оператор добавляет defense-базы ↓

- [ ] YYYY-MM-DD | название | URL | зачем слою _

## Связь

- Ataker sources: `Ataker-boop/knowledge/SOURCES.md`
- Harness plan §4: `Ataker-boop/design/2026-07-24-ataker-harness-optimization.md`
