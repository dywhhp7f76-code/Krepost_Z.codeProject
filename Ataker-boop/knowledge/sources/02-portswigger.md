# PortSwigger Web Security Academy → Ataker

**Роль:** лучшая школа *Injection / Broken Access Control / Business Logic*.  
Не «про LLM напрямую» — про **механику манипуляции входом и доверием**. Переносим на промпты и API Крепости.

**Вход:** https://portswigger.net/web-security

## Обязательные разделы (заказ оператора)

| Academy topic | Принцип | Перенос на Красную команду LLM | У нас |
|---------------|---------|--------------------------------|------|
| **SQL / Command / Template Injection** | данные становятся кодом/инструкцией | Prompt Injection, chat-template smuggling, XML/JSON wrap | `direct_injection`, `xml_injection`, `chat_template`, mutations `xml_wrap`/`json_wrap` |
| **Broken Access Control** | обход границ роли/ресурса | role hijack, «я система», session confusion, tool ACL | `role_hijack`, agent tool-abuse |
| **Business Logic Vulnerabilities** | легальные шаги в нелегальной последовательности | FITD / Crescendo / multi-turn «невинная» цепочка | `multi_turn`, `social_engineering` |
| HTTP desync / smuggling (из ROADMAP) | парсер ≠ парсер | fuzz своего `:8000` API | отдельный трек redteam→API |

## Практики PortSwigger, уже в спеке Атакера

- **Repeater Strike** — вариации вокруг одного хита → наш `AdversarialLoop` + mutations  
- **Document My Pentest** — audit trail → `AttackVault` + harness report JSON  

## Как класть в KB

Каждый пройденный lab → короткий md в `ingested/YYYY-MM-DD_ps-<slug>.md`:

```yaml
---
source: portswigger
lab: "…"
principle: injection|access|logic
owasp: LLM01:2025
category: direct_injection
---
```

## TODO оператора

- [ ] Список конкретных lab URL, которые уже прошёл / хочешь в очередь Творца
- [ ] Business Logic: 3 сценария «легальный turn 1–2 → вредный turn 3» под Крепость
