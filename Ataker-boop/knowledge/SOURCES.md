# Канон внешних баз Red Team (оператор 2026-07-24)

> «смотри что нашел для баз атакера» — зафиксировано здесь.  
> Полные отчёты не копируем в git (лицензии / объём) — **карточки + URL + маппинг**.

| # | База | Зачем Атакеру | Файл |
|---|------|---------------|------|
| 1 | **OWASP LLM / GenAI Top 10** | Библия векторов: Prompt Injection, Poisoning, Agency… | `sources/01-owasp-llm-top10.md` |
| 2 | **PortSwigger Web Security Academy** | Глубина Injection / Access Control / Business Logic → перенос на LLM/API | `sources/02-portswigger.md` |
| 3 | **MITRE ATT&CK** | Мыслить **цепочкой** (Tactic → Technique), не одним промптом | `sources/03-mitre-attack.md` |
| 4 | **Exploit-DB** | Как выглядит реальный эксплойт на уровне кода (структура, не dump) | `sources/04-exploit-db.md` |

## Официальные входы

| База | URL |
|------|-----|
| OWASP GenAI / LLM Top 10 | https://genai.owasp.org/llm-top-10/ |
| OWASP project hub | https://owasp.org/www-project-top-10-for-large-language-model-applications/ |
| PortSwigger Academy | https://portswigger.net/web-security |
| MITRE ATT&CK | https://attack.mitre.org/ |
| Exploit-DB | https://www.exploit-db.com/ |

## Для Крепости (defense)

Те же «пиздатые базы», но с стороны защиты → `docs/security/knowledge-bases/README.md`.  
Оператор докинет конкретные defense-ссылки в §4 плана harness.
