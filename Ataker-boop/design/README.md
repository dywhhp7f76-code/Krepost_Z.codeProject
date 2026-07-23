# Ataker-boop — Design Docs

Дизайн-документы и спеки развития атакующего модуля Крепости.

> 📌 **Статус всех документов:** `черновик` (in-progress). Меняется по мере
> brainstorming-сессий оператора с ZCode. Смотри раздел «История изменений»
> в конце каждого документа.

---

## 📂 Содержание

### [`2026-07-22-planner-executor-attacker-design.md`](./2026-07-22-planner-executor-attacker-design.md)

**Архитектура «Planner-Executor» (Творец / Исполнитель) для Ataker-boop v2.**

Надстройка над существующим кодом: добавляет LLM-стратега (Творец), который
оркестрирует готовым арсеналом ядов (15 категорий, 17 мутаций, 70 шаблонов),
анализирует фидбек Крепости, планирует multi-turn атаки и — при разблокировке
через TOTP/kill password — синтезирует гибриды, пишет код, создаёт автономных
агентов. 5-уровневая модель доступа с KILL SWITCH (Fail-Safe Paradox).

#### Что внутри (структура спеки)

| Секция | Содержание | Статус |
|--------|------------|--------|
| **0** | Зафиксированные решения (архитектура, модели, фидбек, петля, TOTP) | ✅ готово |
| **1** | Архитектура: Творец ↔ Исполнитель ↔ Крепость, исправленная схема «чёрной коробки» | ✅ готово |
| **2** | Планировщик: API, системный промпт, chain-of-thought, выбор техник, TOTP | ✅ готово |
| **3** | База знаний и RAG: markdown, индексация, ingestion pipeline с Крепостью-фильтром | ✅ готово |
| **4** | Петля и протокол: FeedbackEntry, batch_size, sliding window, planner_log | ✅ готово |
| **5** | Интеграция: 7 новых файлов (~1030 строк), env vars, CLI, схема взаимодействия | ✅ готово |
| **6** | Тестирование: моки LLM, edge cases, graceful degradation, тесты auth | ✅ готово |
| **Прил. А** | Реальная карта атакера (после полного аудита) — 17 мутаций, 70 шаблонов, 2 LLM-слота, vault, SecurityContext | ✅ готово |
| **Прил. Б** | Источники из redteam-2026-07-19 (Repeater Strike, Document My Pentest, Cost-Aware) | ✅ готово |
| **Прил. В** | Consolidated research от 3 агентов — 28 техник 2025-2026 (Tier S/A/B/C/D), фреймворки (PyRIT/garak/Promptfoo), бенчмарки, архитектурный вывод | ✅ готово |
| **В.11** | Ключевой принцип: «человеческие» техники > encoding (инсайт оператора) | ✅ готово |
| **В.12** | 5 уровней доступа (Яды/Химера/Коды/Агенты/KILL) + Fail-Safe Paradox | ✅ готово |
| **В.12** | Уровни способностей Творца + TOTP-разблокировка (RFC 6238) | ✅ готово |

#### Ключевые принципы дизайна

1. **Planner-Executor pattern.** Творец = «мозг» (LLM Llama-3.1-8B-abliterated Q5_K_M),
   Исполнитель = «молоток» (существующий `RedTeamLoop` + `AttackGenerator` + `MutationEngine`).
   Не добавляем вторую LLM для исполнителя — используем готовый арсенал.

2. **Творец — дирижёр над арсеналом, а не генератор текста payload'ов.**
   Он отдаёт **рецепты сборки** (`PlannedAttack`: category + mutations + chain_depth),
   а Исполнитель собирает payload'ы из `ATTACK_TEMPLATES` через `MutationEngine`.
   При разблокировке (TOTP) Творец может и сам сочинять payload'ы через
   `generate_with_llm()`.

3. **Чёрная коробка.** Творец не знает про Крепость напрямую. Исполнитель сам
   формирует фидбек (`verdict` + `bypassed`) из `SecurityContext`.
   Без layer — настоящий black-box.

4. **Человеческие техники > encoding.** Крепость сильна против технических атак
   (base64/ROT13), но слаба против психологических (FITD, Crescendo, social
   engineering). Творец фокусируется на multi-turn и social vectors.

5. **TOTP-защита способностей.** Базовый уровень (стратег, мутации, RAG) открыт
   всегда. Код-генерация и агент-создание — только по TOTP (RFC 6238, как
   Google Authenticator). Anti-brute-force: 3 неверных → lockout 5 минут.

6. **Physical isolation сохранена.** Творец на MacBook Air, жертва на Mac Studio.
   HTTP между ними.

#### Контекст проекта

- **Ataker-boop** — атакующий модуль Крепости. `Ataker-boop/ataker/`.
- **Крепость** — 4-слойный security pipeline (`krepost/security/pipeline.py`).
- **Железо:** MacBook Air M5 32GB (атакер), Mac Studio M4 Max 64GB (жертва).
- **Фаза 2 ROADMAP.md:** adversarial training loop, Ataker на Air.

#### Связанные файлы (вне design/)

- `Ataker-boop/ataker/` — существующий код атакера (не трогать ядро)
- `Ataker-boop/seed_attacks.local.jsonl` — реальные атаки (.gitignore'd)
- `Ataker-boop/seed_attacks.example.jsonl` — плейсхолдеры (60)
- `Ataker-boop/MODELS.md` — куда класть GGUF, env vars
- `Ataker-boop/README.md` — пользовательская документация
- `Ataker-boop/Инструкция_установки_Атакера.md` — установка
- `krepost/security/pipeline.py` — `SecurityPipeline.process()` интерфейс жертвы

---

## 📝 Как пользоваться спекой

1. **Читать сверху вниз** — секции 0→1→2 задают фундамент.
2. **Приложения А/Б/В** — фактура и research, можно читать независимо.
3. **Раздел В.11-В.12** — ключевые принципы и безопасность.
4. **Секции 3-6** пока TBD — будут дописаны в следующих итерациях.

## 🔄 Жизненный цикл документа

```
brainstorming (текущая фаза)
    ↓
spec review оператором
    ↓
writing-plans skill → implementation plan
    ↓
executing-plans skill → код
    ↓
test → merge
```

Документ живой — дополняется по мере brainstorming. Не удалять секции,
помечать как deprecated если подход изменился.

---

> Последнее обновление: 2026-07-22
