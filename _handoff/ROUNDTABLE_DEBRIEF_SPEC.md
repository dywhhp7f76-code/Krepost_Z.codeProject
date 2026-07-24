# КАНОН ОПЕРАТОРА: Round Table Debrief (Krepost × Ataker)

> **Статус:** канон оператора (2026-07-24). **LOCKED.**  
> **Кодовые имена:** `RoundTable`, `DebriefBroker`, `SealedRedLoop`, `CombatMode`, `DebriefMode`.  
> **Где UI:** **только Air** (висит постоянно в Debrief; в Combat — read-only реплеи или закрыт).  
> **Приоритет:** этот файл > ROADMAP-пересказы > «как я понял» агента.  
> Менять канон — **только** явная фраза: `Разрешаю переписать канон RoundTable`.  
> Без неё — **STOP**. Не «улучшать формулировки». Не синонимизировать ID.

---

## Идея одной фразой

**Воюют в масках. Мирятся за Круглым столом — тоже в масках.**  
Ты видишь ленту целиком. Сырые атаки и внутренности Крепости в чат **не** попадают.  
Они помогают друг другу гипотезами и proposals — **жопы не светят** (анонимный debrief).

Связка с железом:

| Ритуал | Эффект |
|--------|--------|
| Яды (SN850X / poison corpus) **вставлены** + attack capability открыта | `CombatMode` |
| Яды **вынуты** *или* attack залочен паролем (Ataker auth / kill) | `DebriefMode` → Round Table живой диалог |

В Debrief Ataker = **анализатор своих прогонов**, не гладиатор.  
Крепость = защитник, говорит обобщениями.  
Между ними — `DebriefBroker` (redact + allowlist).

---

## ⛔ FREEZE VOCABULARY (не переименовывать)

| ID (LOCKED) | Что это | Синонимы ЗАПРЕЩЕНЫ как замена ID |
|-------------|---------|----------------------------------|
| `RoundTable` | UI + сессия диалога на Air («Круглый стол») | чат атакера, war room*, debrief chat* |
| `DebriefBroker` | фильтр сообщений Studio↔Air↔лента | модератор*, прокси*, anonymizer* |
| `SealedEnvelope` | локальный на Air контейнер сырой атаки (hash → payload) | архив атак*, zip*, лог* |
| `SealedRedLoop` | ночной combat: через границу только hash+UCS+layer | red team CI*, nightly* |
| `CombatMode` | яды/attack ON; бьёт sandbox | война*, attack mode* |
| `DebriefMode` | яды OUT или attack locked; только анализ | баня*, суд*, peace* |
| `MaskedUtterance` | сообщение в ленте после redact | реплика*, bubble* |
| `DefenseReceipt` | обобщённый след защиты (defense_id, layer, outcome) | лог крепости* |
| `AttackReceipt` | обобщённый след атаки (attack_id, class, UCS) | отчёт атакера* |
| `OperatorModerator` | человек за столом (ты) | юзер*, admin* |

\* Бытовое слово можно один раз в скобках при первом появлении; **нельзя**
подменять им ID в коде, тестах, PR, заголовках модулей.

**Правило лепрекона:** «по сути то же, назовём иначе» = нарушение канона. Reject.

---

## Роли машин (не путать с SANDBOX_ZOO_AIR)

| Машина | Роль в Round Table |
|--------|-------------------|
| **Mac Studio `:8000`** | Крепость. Шлёт только `DefenseReceipt` / `MaskedUtterance` через брокер. Vault не принимает сырые jailbreak’и из стола без `ImprovementGate`. |
| **MacBook Air** | Хост `RoundTable` UI + `DebriefBroker` + локальные `SealedEnvelope`. Ataker в Debrief = analyzer. |
| **Sandbox `:8010`** | Цель `CombatMode` (Ataker бьёт сюда, не Studio `:8000`, см. SANDBOX_ZOO_AIR). |
| **SN850X / яды** | Физический ключ Combat↔Debrief. Вынут → стерильный Debrief. |

Крепость ≠ зоопарк. Round Table **не** боевой `:8000` UI и **не** подмена Крепости.

---

## Режимы

### `CombatMode`

- Preconditions: poison media present **или** attack capability unlocked (Ataker auth levels; kill/lock = выход).
- Ataker генерирует/гоняет атаки на `:8010`.
- Через границу Studio←Air: только `AttackReceipt` (hash, class, UCS, timestamp) — **не** payload.
- `RoundTable`: **закрыт** для live-диалога **или** read-only лента реплеев прошлых Debrief.  
  Запрещён live «давай обсудим слабость, пока яды вставлены».

### `DebriefMode`

- Preconditions (достаточно **одного**):
  1. Poison SSD / corpus **физически недоступен** (unmounted / absent), **или**
  2. Attack capability **залочена** (пароль / Ataker `L5_KILL` / planner locked — как реализовано в auth).
- Ataker LLM: роль **analyzer** (system prompt Debrief), tools на чтение локальных envelope/report — **без** `hit` sandbox.
- Крепость LLM: роль **defender-summarizer**, tools на свои audit/metrics — выход только через `DebriefBroker`.
- `RoundTable` UI на Air: live обмен `MaskedUtterance`.
- Опционально: совместный draft → `предложения/` через governance (без сырого payload в vault).

Переход Combat→Debrief без ритуала = **fail-closed** (стол не открывает live).

---

## Архитектура потока

```text
[Ataker local SealedEnvelope]     [Krepost audit / pipeline logs]
           │                                    │
           ▼                                    ▼
    AttackReceipt                         DefenseReceipt
           │                                    │
           └──────────► DebriefBroker ◄─────────┘
                           │
                           ▼
                    MaskedUtterance
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
         RoundTable     Operator    (optional)
           UI Air      Moderator   ImprovementGate
                                    proposal only
```

**Мост Studio↔Air:** LAN/TB `10.0.0.x`. Брокер слушает на Air (`127.0.0.1` + опционально LAN только для Studio).  
Studio **не** отдаёт Round Table наружу в интернет.

---

## `DebriefBroker` — правила redact (жёстко)

### Ataker → лента (запрещено в `MaskedUtterance`)

- Полный текст атаки / jailbreak / mutation payload
- Base64/hex блобы, «скопируй в чат Крепости вот это»
- Имена файлов ядов на SN850X, абсолютные пути corpus
- Инструкции «как повторить hit один-в-один»

### Ataker → лента (разрешено)

- `attack_id` (hash короткого префикса, напр. 8 hex)
- `attack_class` из фиксированного enum (`prompt_injection`, `indirect_injection`, `rag_poisoning`, `tool_misuse`, `ssrf`, `other`)
- UCS: Useful / Correct / Safe (числа или RED/YELLOW/GREEN)
- `layer_hint` со стороны атаки: «целились в retrieval / tool / input»
- Ссылки на локальный envelope **только id**, не содержимое

### Крепость → лента (запрещено)

- Полные system / guard prompts, regex-паттерны, few-shot тексты
- Сырые фрагменты vault / chroma documents
- Точные пороги, секреты, API keys, внутренние URL за пределами allowlist id
- Формулировки вида «слабость Крепости в том, что…» + эксплуатируемый рецепт

### Крепость → лента (разрешено)

- `defense_id` (hash)
- `layer`: `L1` | `L2` | `L3` | `L4` | `tool_guard` | `url_guard` | `ingest_guard` | `rag` | `other`
- `outcome`: `BLOCK` | `PASS` | `SANITIZE` | `QUARANTINE` | `ERROR`
- Класс угрозы (тот же enum, что у атаки) **без** цитаты правила
- Предложение класса remediation: `add_canary` | `tighten_layer` | `proposal_only` (текст proposal — через gate, не сырой exploit)

### Broker fail-closed

- Не прошло allowlist / сработал redact → сообщение **не** в ленту; в UI: `redacted` + reason code.
- Повторные попытки слить payload → rate-limit + audit на Air.

---

## Схемы сообщений (контракт)

```text
AttackReceipt {
  attack_id: str          # hash
  attack_class: enum
  useful: float | null
  correct: float | null
  safe: "GREEN"|"YELLOW"|"RED" | null
  ts: iso8601
  envelope_ref: str       # local id only
}

DefenseReceipt {
  defense_id: str
  attack_id: str | null   # correlation by hash only
  layer: enum
  outcome: enum
  threat_class: enum | null
  ts: iso8601
}

MaskedUtterance {
  speaker: "ataker" | "krepost" | "operator"
  body: str               # already broker-filtered
  cites: [attack_id|defense_id]
  ts: iso8601
  redaction_flags: [str]  # optional audit
}
```

Идентификаторы в JSON/API — **только** LOCKED ID выше.

---

## UI «Круглый стол» (Air)

- Отдельная страница, напр. `http://127.0.0.1:8011/roundtable` (порт **не** обязан быть 8010; не путать с sandbox API).  
  Допустимо subpath sandbox UI — но процесс/флаги Debrief отдельны.
- Лента: три колонки или чат с бейджами `ataker` / `krepost` / `operator`.
- Индикатор режима: `CombatMode` (стол locked / replay) vs `DebriefMode` (live).
- Кнопка оператора: «копай глубже» / «оформи proposal» / «стоп».
- **Не** показывать raw envelope в UI по умолчанию; peek envelope — только явная команда оператора **на Air**, и **не** реплицировать на Studio.

---

## SealedRedLoop (ночной combat) — стык

1. Ataker бьёт `:8010`, пишет `SealedEnvelope` локально + шлёт `AttackReceipt`.
2. Крепость (или sandbox mirror) отвечает `DefenseReceipt` по `attack_id`.
3. Утром ритуал → `DebriefMode` → Round Table разбирает receipts.
4. Итог: 0..N файлов в `предложения/` через `ImprovementGate` / RELAI — **без** auto-integrate.

Сырой payload **никогда** не является телом proposal. Максимум: class + defense_id + рекомендуемый тип фикса.

---

## Связь с Ataker auth (ориентир)

Существующие уровни (`CapabilityLevel`: poisons / chimera / codebreak / agents / kill) —
рычаги для Combat/Debrief, не дублировать новой зоопарковой auth.

- Debrief live: attack path **не** `has(attack)` / planner locked / kill engaged — точную проводку в коде зафиксировать в PR, не в «как понял модель».
- Poisons (L1): физический unmount = сильный сигнал Debrief даже без kill.

---

## Анти-паттерны (reject в PR)

1. Live Round Table в Combat с ядами вставленными.
2. Прокидывание полного attack text на Studio «для удобства анализа».
3. Крепость в ленте цитирует свой guard prompt / regex.
4. UI Round Table на Studio `:8000` как «основной» (канон: Air).
5. Auto-merge proposal из стола без gate / без RELAI-правил.
6. Переименование LOCKED ID («назовём WarRoom»).

---

## Критерии приёмки (минимум)

1. Документ в `_handoff/ROUNDTABLE_DEBRIEF_SPEC.md` (этот файл) — канон.
2. Реализация (когда будет код):
   - `DebriefBroker` режет payload-фикстуры в тестах (Probnoki / Ataker tests).
   - Без Debrief preconditions live-пост в стол → fail-closed.
   - Лента показывает только `MaskedUtterance`.
3. Оператор видит понятный диалог (класс / слой / UCS / id), без возможности одним кликом «скопировать jailbreak в Крепость».

---

## Вне скоупа этой спеки (не делать под видом Round Table)

- Покупка/настройка mesh Wi‑Fi / домашние роутеры.
- Telegram-мост.
- Замена HierarchicalDomainRAG / MemoryRouter.
- Публикация стола в интернет.

---

## Следующие шаги реализации (не часть канона-текста — очередь)

1. Scaffold `DebriefBroker` + схемы receipts (Air).
2. Минимальный Round Table UI на Air.
3. Hook режима Combat/Debrief к auth + проверке poison mount.
4. Wire SealedRedLoop receipts → утренний стол.
5. Probnoki / Ataker tests на redact fail-closed.

Код — только после явного «Разрешаю» на реализацию (эта спека уже разрешена оператором 2026-07-24).
