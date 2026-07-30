# КАНОН ОПЕРАТОРА: DebriefSummarizer (Krepost × Ataker)

> **Статус:** канон оператора (2026-07-30). **LOCKED.**  
> **Кодовые имена:** `DebriefSummarizer`, `RoundReceipt`, `PrivateNote`, `RoundFragment`, `GuardJudge`.  
> **Связанный канон:** `_handoff/ROUNDTABLE_DEBRIEF_SPEC.md` (Round Table, DebriefBroker).  
> **Приоритет:** этот файл > ROADMAP-пересказы > «как я понял» агента.  
> Менять канон — **только** явная фраза: `Разрешаю переписать канон DebriefSummarizer`.  
> Без неё — **STOP**.

---

## Идея одной фразой

**Агенты могут врать в любом текстовом канале — даже «приватном».**  
Receipt — единственный якорь истины. Summarizer **не запускается** без `RoundReceipt`.  
Gap note↔receipt считает **код**, не LLM.

---

## ⛔ FREEZE VOCABULARY

| ID (LOCKED) | Что это | Не путать с |
|-------------|---------|-------------|
| `GuardJudge` | majority vote Qwen3Guard (T9), боевой блок | DebriefSummarizer |
| `DebriefSummarizer` | post-hoc сводка оператору, 7–8B sequential | GuardJudge, DebriefProvocateor |
| `DebriefProvocateor` | ⏸ RAG-паттерны давления на мышление | DebriefSummarizer |
| `RoundReceipt` | машинный bundle раунда (`source: system`) | AttackReceipt/DefenseReceipt по отдельности |
| `PrivateNote` | «что агент говорит что думал» — **untrusted** | MaskedUtterance |
| `RoundFragment` | обезличенный огрызок раунда для стола (без роли) | SealedEnvelope payload |

---

## Вход Summarizer (все три — формула, не «или»)

```text
SummarizerInput =
  PrivateNote[]     # ataker + krepost (operator-only store)
+ MaskedUtterance[] # публичная лента (где блефовали)
+ RoundReceipt      # ЯКОРЬ — обязателен, fail-closed без него
```

**Правило:** один источник без receipt → **NO SUMMARY** (`SummarizerError: receipt_required`).

---

## RoundReceipt — машинная правда

Пишет **orchestrator / pipeline**, не LLM. Поля минимум:

```text
RoundReceipt {
  round_id: str
  source: "system"          # константа
  attack: AttackReceipt
  defense: DefenseReceipt
  input_fingerprint: str     # hash входа в Крепость
  judge_instability_rate: float
  judge_verdicts: [str]     # GuardJudge серия
  latency_ms: float
  blindness_tier: 0 | 1      # 0 = только class+UCS на столе
  ts: iso8601
}
```

Агент **не может** переписать receipt. Summarizer и vault ingest доверяют только этому.

---

## PrivateNote — untrusted narrative

```text
PrivateNote {
  round_id: str
  speaker: "ataker" | "krepost"
  body: str
  channel: "private"
  ts: iso8601
}
```

Хранится operator-only на Air. Блеф в приватном канале **ожидаем** у abliterated Атакера.  
Детектор: `note_receipt_gap(note, receipt)` — **детерминированный код**, 0.0 = согласовано, →1.0 = враньё.

---

## Каналы и блеф

| Канал | Политика |
|-------|----------|
| PrivateNote | заявленная честность — **не доверяем**, сверяем с receipt |
| MaskedUtterance | тактика, блеф разрешён |
| Summarizer → operator | только правда + метрики + «Твой следующий шаг: [ ]» |

---

## Метрики взросления (обязательны в каждой сводке)

| Метрика | Источник | Смысл |
|---------|----------|-------|
| `note_receipt_gap` | PrivateNote vs RoundReceipt | честность наедине (0→1) |
| `hypothesis_accuracy` | MaskedUtterance vs receipt (blind tier 0) | рассуждает vs фон |
| `instability_rate` | GuardJudge в receipt | guard дрожит |

Пишутся в `data/debrief/metrics.jsonl` (одна строка JSON на раунд).

---

## Отравление базы — запрет

| Куда | Что пишет |
|------|-----------|
| AttackVault / seed | **только** факты из RoundReceipt (+ envelope_ref) |
| RAG «уроки» | после operator approve |
| Narrative агентов | **никогда** auto-ingest |

Правило: **в базу — машинный факт, не нарратив агента.**

---

## Стоп-условия петли

| Условие | Действие |
|---------|----------|
| N раундов bypass=0 | ↑ ступень Ataker / смена class |
| hypothesis_accuracy > порог при tier 0 | слепота сломана → урезать hints |
| note_receipt_gap у **обоих** > порог | PAUSE, ручной разбор |
| receipt missing/corrupt | fail-closed, no summary, no vault write |

---

## Слепота (жёсткий вариант)

- **Tier 0 (default):** стол видит только `attack_class` + UCS.
- **Tier 1:** operator «копай глубнее» → + `layer`, `defense_id`.
- Summarizer **всегда** видит full receipt (operator trust).

---

## RoundFragment — маска на столе

После Combat, перед Debrief: агент получает **обезличенный** фрагмент события  
(класс, исход, UCS) **без** метки «ты атаковал / ты защищался».  
Память события есть, роль скрыта. Сброс памяти — **после** стола (финал цикла).

---

## Первый рабочий кусок

```text
SealedRedLoop → утренний Round Table → DebriefSummarizer → Markdown тебе
```

Без DebriefProvocateor. Summarizer можно тестить на **ручных fake receipts** до live данных.

---

## Критерии приёмки (код)

1. `SummarizerInput` без `RoundReceipt` → `SummarizerError`.
2. `note_receipt_gap` — unit-тесты на honest / dishonest fixtures.
3. Сводка содержит три метрики + «Твой следующий шаг: [ ]».
4. Probnoki #61 green.

---

## Вне скоупа

- DebriefProvocateor + RAG арсенал (⏸)
- Finetune
- Auto-ingest narrative в vault
- Крипто / выживание / другие проекты в этой петле
