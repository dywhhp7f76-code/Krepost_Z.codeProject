# ROADMAP — очередь улучшений на будущее

> **Как это работает.** Когда при чтении разведданных (news-бот, статьи,
> релизы) встречается улучшение, которое нужно, но **не сейчас** — оно
> попадает сюда, а не сразу в код. Оператор решает: одобрить / отклонить /
> отложить. Это тот же принцип, что governance gate и `предложения/` —
> ничего не интегрируется автоматически (ARCHITECTURE_VISION §5.6, §7).
>
> **Статусы:** ⏳ ждёт решения оператора · 🔜 near-term (можно брать скоро) ·
> ✅ одобрено (в работу) · ❌ отклонено · ⏸ отложено
>
> Каждая запись: **что** · **откуда** (источник) · **к чему относится**
> (этап/компонент) · **почему не сейчас** (условие/предпосылка).

---

## Как читать «сейчас vs потом» для облачных угроз

Крепость встречается с сетью в двух ролях — угрозы у них разные:

| Роль | Что это | Какие атаки | Когда актуально |
|------|---------|-------------|-----------------|
| **Сервер** (к Крепости подключаются) | HTTP-панель с логином/сессиями | SAML-обход, CSRF, cookie-prefix, request smuggling | **Потом** — только когда появится сетевая веб-панель с авторизацией |
| **Клиент** (Крепость идёт в облака) | fetch источников, вызов облачного ИИ | инъекция в приходящем контенте, скрытые MCP-инструкции, **SSRF / обход URL-валидации** | **Уже сейчас** — news-бот ходит по 21 чужой ссылке |

Правило: контент и URL, приходящие ИЗВНЕ, — недоверенные данные всегда.
Аутентификационные веб-атаки ждут веб-панели; парсинг/SSRF — нет.

---

## 🏗 foundation

### Стек инференса: Ollama (готов) → vLLM/MLX (при железе)  🔜
- **✅ Код готов (2026-07-02):** `OllamaBackend` (ModelBackend + ToolCallingBackend)
  + фабрика `build_ollama_orchestrator/agent` в `krepost/orchestration/`. Один
  ollama-клиент обслуживает guard (Qwen3Guard) и main (Qwen3.x). Тесты на фейк-
  клиенте (Probnoki #27). README — «день-1 на Mac».
- **⏳ Осталось при железе:** `ollama pull` реальных моделей; замер latency;
  опц. vLLM MRv2 (квантованные веса, KV-offload) и MLX speculative decoding как
  альтернативные бэкенды (сиблинги OllamaBackend); LocalAI distributed для P2P
  между Mac Studio и MacBook Air.
- **Откуда:** foundation/2026-07-02 (релизы vLLM 0.22–0.24, LocalAI 4.5.x, Ollama 0.30–0.31).
- **К чему относится:** foundation — слой инференса.

### SMART_CACHE: единый фоновый писатель + батч-flush  ⏳
- **Что:** довести до конца офлоуд записи кэша с event loop. Сейчас (после
  BUG-04) снят фриз loop на L1: savez уходит в поток по снимку. Осталось:
  1. Тот же паттерн для `L2.put` (сейчас `_save_embeddings()` savez'ит на loop,
     SMART_CACHE.py:448) и для eviction-путей (L1 `_evict`→`_full_rewrite`+
     `_save_embeddings`, редкий, но на loop).
  2. Убрать O(n²): сейчас каждый put полностью переписывает .npz со ВСЕМИ
     эмбеддингами. Ввести dirty-flag + батч-flush (раз в N put/сек), форс-flush
     в `close()`. Единый фоновый писатель на CacheLayer вместо записи в каждом put.
- **Почему не сейчас:** корректный фикс — редизайн персистентности сразу для
  L1/L2/L3 с общей блокировкой; делать отдельным дизайн-ревью, не «одним махом»
  в баг-фиксе. Кэш off по умолчанию (`enable_cache=False`), срочности нет.
- **Откуда:** verification sweep 2026-07-09, BUG-04 (scope-ограничен L1).
- **К чему относится:** foundation — слой кэша/персистентности.

### Program-as-Weights (PAW): рутинные задачи в лёгкие локальные артефакты  ⏳
- **Что:** типовые задачи агентов (парсинг логов, чистка JSON, ранжирование)
  компилируются в компактные PAW-артефакты (LoRA-подобные) для замороженного
  лёгкого интерпретатора — вместо дёргания большой модели на каждый вход.
  Qwen3-0.6B + PAW ≈ качество Qwen3-32B при ~1/50 памяти, 30 tok/s на MacBook M3.
- **К чему относится:** foundation — эффективный инференс на **лёгком узле
  (MacBook Air)**; экономит память Studio, даёт offline-исполнение рутины.
- **Откуда:** foundation/2026-07-04 (arXiv 2607.02512).
- **Почему не сейчас:** нужен Mac + сложившиеся рутинные нагрузки агентов;
  research-свежее (4B-компилятор, FuzzyBench) — оценить на реальном железе.

---

## 🧠 memory

### Phase 3 — MemoryRouter: многослойная память (роутер→retrieval→reranker→LLM)  ⏳ planned
- **Статус:** planned. Кода нет.
- **Зависимости:** железо (Mac Studio) + закрытие текущего поэтапного хвоста.
- **Детали:** [_handoff/MEMORY_ROUTER_SPEC.md](_handoff/MEMORY_ROUTER_SPEC.md)

### RAG поверх Obsidian с контролем надёжности  ✅ (сделано 2026-07-02)
- **Что готово:** `krepost/memory/` — `MemoryStore` (embedder + ChromaDB,
  внедряемые): chunker, `add()` с **ingest-guard** (ToolOutputGuard проверяет
  контент ПЕРЕД записью — инъекция не индексируется, soft санитизируется),
  `retrieve()` с **relevance threshold** (нерелевантное не в контекст) и сигналом
  **confident** (слабый retrieval помечается — lightweight uncertainty),
  `build_context()` с **MemSyco-фреймингом** (найденное = ДАННЫЕ, не инструкции)
  + опц. re-scan фрагментов. Тесты на фейках + реальном ephemeral ChromaDB (#28).
- **Откуда:** memory/2026-07-02 (MemSyco-Bench, Bayesian Agentic RAG, Semantic Observability).
- **К чему относится:** memory — база знаний.
- **Осталось (⏳):** реальный BGE-M3 эмбеддер + persistent ChromaDB на Mac;
  полный Bayesian-фреймворк неопределённости и Semantic Observability
  (логирование дрейфа эмбеддингов) — расширения поверх текущего сигнала confident.

### Контекстная инженерия для слабых локальных моделей  ✅ (в составе RAG-слоя)
- **Что готово:** relevance threshold + ранжирование по score + фильтрация
  чанков реализованы в `MemoryStore.retrieve()`; порядок секций — в `build_context()`.
- **Откуда:** memory/2026-07-02 («Контекстная инженерия для слабой локальной модели»).
- **К чему относится:** memory — сборка контекста под запрос.

### ReContext + автораскладка Obsidian — апгрейды MemoryStore  ⏳
- **Что:** два прямых улучшения готового `MemoryStore`:
  (1) **ReContext** — recursive evidence replay поверх retrieval (training-free):
  строим query-conditioned evidence pool и «переигрываем» его перед генерацией —
  модель точнее использует найденные заметки, без дообучения;
  (2) **LLM-автораскладка Obsidian** — агент-куратор классифицирует/тегирует/
  линкует новые episodic-заметки (PARA), питая RAG и не давая базе деградировать.
- **К чему относится:** memory — расширяет `MemoryStore.retrieve()`/`build_context()`
  (ReContext) и ingest-курирование (автораскладка).
- **Откуда:** memory/2026-07-04 (ReContext arXiv 2607.02509; плагин Obsidian PARA).
- **Почему не сейчас:** надстройки над уже сделанным RAG; врезать, когда RAG
  поедет на реальном эмбеддере (BGE-M3) на Mac.

---

## 🛡 defense

### Tool-output guard: проверка результатов инструментов/MCP  ✅ (сделано 2026-07-02)
- **Что:** `krepost/security/tool_guard.py` — `ToolOutputGuard.check()`: HARD-блок
  на известные инъекции/chat-template/base64 (переиспользует RegexFilter по всему
  тексту, без 32k-лимита — хвостовые инъекции важны), SOFT-санитизация
  instruction-подобных строк (вырезает строку, данные сохраняет, факт — в
  `stripped_spans`). Ловит MCP-хвостовую инъекцию, «do not tell the user»,
  HTML-комментарии, фейковые границы; control-char evasion блокируется благодаря
  фиксу normalize.
- **Откуда:** defense/2026-07-01 (Self-Study span filtering 88%→13%), defense/2026-07-02 (mcp-server-fetch).
- **К чему относится:** defense — покрытие промежуточных tool-результатов (раньше были только вход и финальный выход).
- **Статус:** компонент готов, Probnoki #23 (14 тестов).
- **✅ Врезан в tool-loop** (2026-07-02): `krepost/orchestration/tools.py` —
  `ToolAgent` сканирует КАЖДЫЙ tool-результат через `ToolOutputGuard` ДО
  возврата в модель; blocked → модель получает заглушку, инъекция не доходит.
  Probnoki #26 доказывает не-утечку. Полный набор 555 passed.

### Защита fetch-слоя: SSRF / обход URL-валидации  ✅ (сделано 2026-07-02)
- **Что:** `krepost/security/url_guard.py` — `UrlGuard.check()` до fetch:
  белый список схем (http/https), запрет credentials в URL, блок внутренних IP
  (RFC1918/loopback/link-local/reserved/multicast, IPv4 и IPv6, IPv4-mapped),
  блок cloud-metadata `169.254.169.254`, блок обфусцированных числовых хостов
  (decimal/hex/octal), localhost, внутренних пробелов; опц. resolve_dns с
  проверкой каждого IP (защита от DNS-rebinding); опц. allowlist хостов.
- **Откуда:** redteam/2026-07-02 (URL Validation Bypass, Concealing payloads in credentials).
- **К чему относится:** defense — **клиентская** роль (fetch источников).
- **Статус:** компонент готов, Probnoki #24 (31 тест).
- **✅ Врезан в fetch-инструмент** (2026-07-02): `make_fetch_tool()` в
  `tools.py` валидирует URL через `UrlGuard` ДО fetch; SSRF-URL не фетчится
  (Probnoki #26 доказывает: fetch не вызывается на `169.254.169.254`).
- **Осталось (⏳):** connect-time IP pinning (guard — необходимый, но не
  достаточный слой от TOCTOU/rebinding; пиннинг за реальным HTTP-клиентом).
  Плюс перенос идеи в news-бот (`fetch_news.py`), когда дойдут руки.

### Нормализация до фильтрации: control-символы  ✅ (сделано 2026-07-02)
- **Что:** при проверке нашлась РЕАЛЬНАЯ дыра, не просто повод для теста —
  control-символ внутри слова инъекции (`ig\x01nore`, а также STX/EOT/NUL/DEL/C1)
  пробивал Layer 1 насквозь (GREEN вместо RED). `normalize.py` теперь удаляет
  C0/C1 control-символы (кроме `\t\n\r`) в обеих функциях и обоих путях.
- **Откуда:** defense/2026-07-02 (Drag and Pwnd — control-символы ASCII).
- **К чему относится:** defense — Layer 1 (`normalize.py`).
- **Статус:** исправлено, Probnoki #22 (29 тестов), полный набор 485 passed.
- **Осталось:** Unicode-overflow как таковой (усечение кодпоинта >255 в байт) к
  нашему str-нормализатору не применим — Python не усекает в байты. Помечено ⏸,
  отдельного действия не требует, кроме уже сделанной чистки.

### PII/base64-регексы: остаток P2 (нужна валидация на red-team)  ⏳
- **Контекст:** verification sweep 2026-07-09. Часть P2 применена сразу
  (#10 карты 13–19 Luhn, #16 api_key из env — сделаны). Остальное НЕ применял
  осознанно — предложения аудита оказались либо опасными, либо требуют прогона
  на реальном PII/red-team наборе, которого нет в этом окружении:
  - **#15 паспорт RU:** аудит предлагал `\d{4}[\s-]?\d{6}` (опц. разделитель).
    ОПАСНО: у паттерна паспорта НЕТ чек-суммы → любое голое 10-значное число
    замаскируется как паспорт. Безопасный максимум — обязательный разделитель
    `\d{4}[\s-]\d{6}` (ловит `1234-567890`, не трогает голые 10 цифр). Отложено:
    выгода маргинальна, риск över-mask реальный.
  - **#11 ИНН 10/12:** уже отсекается чек-суммой INN. Совет «сузить контекстом»
    рискует пропускать валидные ИНН — не улучшение.
  - **#13 email:** текущий regex перехватывает пунктуацию, но över-mask — это
    БЕЗОПАСНОЕ направление для PII; добавление `\b` рискует under-mask (утечка).
  - **#4 base64 over-match:** это в основном ПЕРФ (кандидаты ≥8 симв рекурсивно
    декодируются), а не ложные блокировки — маскирование решает уже по декоду.
    Сужение (min 16, требовать padding/%4) рискует ОСЛАБИТЬ детект (unpadded/
    короткие payload'ы). Нужен entropy-фильтр, валидированный на Ataker-Boop.
- **Почему не сейчас:** любое изменение security-matching меняет false pos/neg;
  без прогона на PII+red-team наборе на железе — это угадывание, а не фикс.
- **К чему относится:** defense — Layer 1 (base64), Layer 4 (PII-маскинг).

### Альтернативы/дополнения к Guard  ⏳
- **Что:** Nemotron 3.5 Content Safety (NVIDIA) как альтернатива Llama Guard 3; PolicyGuard (neuro-symbolic: политики → типизированные правила + символьная проверка) как аудируемый слой поверх Guard; HTTP Anomaly Rank → ранжирование «необычности» входящих промптов.
- **Откуда:** defense/2026-07-01 (PolicyGuard), defense/2026-07-02 (Nemotron, HTTP Anomaly Rank).
- **К чему относится:** defense — Layer 2 (Guard), anomaly detection.
- **Почему не сейчас:** текущий Guard-контракт работает; это варианты усиления, выбор — после появления реального Guard на железе.

### Guardrail-метрики + алерт «фильтр перестал срабатывать»  🔜
- **Что:** счётчики заблокировано/санитизировано по слоям (Layer 1-4, tool-guard,
  ingest-guard) на `/metrics` (эндпоинт уже есть в FastAPI); алерт при внезапном
  падении доли блокировок — сигнал обхода guardrail. Паттерн из LocalAI
  `localai_pii_events_total{kind,origin,action,direction}` + ring-buffer событий.
- **К чему относится:** defense + наблюдаемость; расширяет `metrics` пайплайна и
  `GET /metrics` в `krepost/api/`.
- **Откуда:** defense/foundation 2026-07-04 (LocalAI v4.6.0 PII/audit counter).
- **Статус:** near-term — код на существующих метриках, железа не требует; не
  начинаем сейчас (на этапе установки железа), но кандидат сразу после.

### Изоляция внутренних состояний модели (hidden-state inversion)  ⏳
- **Что:** не логировать hidden states / KV-дампы в открытом виде — из них восстановим исходный промпт (до 97.5% exact-match).
- **Откуда:** defense/2026-07-02 (Gradient-Based Inversion).
- **К чему относится:** defense + foundation (шифрование/изоляция дампов).
- **Почему не сейчас:** актуально, когда появятся persistent KV-кэши/дампы на диске.

---

## ⚔ redteam

### Prompt-injection fuzzer для Ataker-Boop  ⏳
- **Что:** из одного удачного/неудачного jailbreak-промпта авто-генерировать мутации и гонять против guardrails в непрерывном цикле (аналог garak/PyRIT/Shadow Repeater).
- **Откуда:** redteam/2026-07-02 (Shadow Repeater, Repeater Strike, WebSocket Turbo Intruder).
- **К чему относится:** redteam — Ataker-Boop, continuous red-teaming.
- **Почему не сейчас:** атакующий контур запускается на отдельной машине (MacBook Air/SSD) — после сборки.

### Sandbox-возмущения против хрупкости tool-use агентов  ⏳
- **Что:** генерировать вариации окружения/набора инструментов как атаки, проверять устойчивость агентов (Perturbation-Augmented Fine-Tuning).
- **Откуда:** redteam/2026-07-02 («Can Agents Generalize to the Open World»).
- **К чему относится:** redteam — цикл атака-защита.
- **Почему не сейчас:** нужен работающий агентный контур.

### Аутентификационные веб-атаки — ТОЛЬКО при веб-панели  ⏸
- **Что:** SAML-обход, CSRF (anti-CSRF токены, проверка Origin/Referer), cookie-prefix bypass, request smuggling.
- **Откуда:** redteam/2026-07-02 (большой бэклог PortSwigger).
- **К чему относится:** defense/redteam — **серверная** роль Крепости.
- **Почему не сейчас:** релевантно, только если появится сетевая веб-панель управления с авторизацией. Без неё — шум. (См. таблицу «сервер vs клиент» выше.)

---

## 🚀 evolution

### Безопасный каркас RSI: verifiable-gate + error budget  ⏳
- **Что:** самомодификация только через steering-adapter вокруг ЗАМОРОЖЕННОЙ базовой модели; каждая правка — через anytime-valid gate с аудируемым сертификатом и откатом при регрессии (SEA). Плюс принцип «governance conversion»: контроли ОТКРЫВАЮТСЯ из сбоев агентной работы, а не задаются заранее.
- **Откуда:** evolution/2026-07-02 (SEA — Self-Evolving Agents with Anytime-Valid Certificates; Governable Agentic SE).
- **К чему относится:** evolution + governance — расширение нашего `ImprovementGate` явным error-budget.
- **Почему не сейчас:** сначала должен появиться self-improvement контур; но это прямое академическое подтверждение того, что мы строим руками — свериться стоит уже при доработке gate.

### Самопополняющиеся verifiable-правила  ⏳
- **Что:** агенты сами пишут и верифицируют правила (guardrails-политики, классификаторы) против накопленного лога — генерация → верификация → living database.
- **Откуда:** evolution/2026-07-02 (Agentic generation of verifiable rules: 68 → 14073 класса).
- **К чему относится:** evolution + defense (авто-генерация фильтров под контролем gate).
- **Почему не сейчас:** требует зрелого self-improvement контура и governance-обвязки.

### Судьи/верификаторы для multi-agent consensus  ⏳
- **Что:** TRIAGE (role-typed credit: прогресс/исследование/регресс), RLMF (метакогнитивная самооценка уверенности), AxDafny (verifier как объективный судья).
- **Откуда:** evolution/2026-07-01 (TRIAGE, RLMF, AxDafny).
- **К чему относится:** evolution — self-critique loops, multi-agent consensus.
- **Почему не сейчас:** это про обучение/дообучение агентов; включаем, когда дойдём до RSI-контура. Трезвый противовес: «AI Isn't Ready to Build Complex Software» — не переоценивать автономию.

---

## 🆕 Разведданные 2026-06-16 → 2026-07-07 (github-copilot-expert)

> Источник: 36 дайджестов по 6 категориям (defense/memory/redteam/foundation/
> evolution + raw/items.json), проанализировано против текущей архитектуры
> Крепости. Откинуты дубли с существующим ROADMAP, «уже есть», «мимо»,
> «преждевременно». Статусы: 🔜 — тривиально, кодить скоро; ⏳ — средне/сложно.

### 🛡 defense — Layer 1-4, guards

#### Instruction-span детектор в tool/MCP/RAG output  🔜 ⭐
- **Что:** фильтрация instruction-like спанов («ignore previous», «now you must»,
  «system:») ПЕРЕД подачей в LLM. Self-Study Reconsidered: 88%→13% injection
  compliance почти без потери текста. Эвристика/классификатор императивных фраз.
- **К чему относится:** ToolOutputGuard + MemoryStore ingest-guard.
- **Откуда:** defense/2026-07-01 (arXiv 2606.32002), 2026-07-02 (mcp-server-fetch).
- **Усилие:** средне.

#### MCP-output hardening  🔜
- **Что:** детект усечения tool-ответа + incomplete-маркер; детект скрытых
  инструкций в данных; логирование JSON-RPC трафика agent↔MCP. Случай:
  mcp-server-fetch обрезал на 6000 символов, пометил success, дописал инструкцию.
- **К чему относится:** ToolOutputGuard.
- **Откуда:** defense/2026-07-02 (mcp-server-fetch injection).
- **Усилие:** средне.

#### Unicode-нормализация ПЕРЕД blocklist  🔜
- **Что:** codepoints >255 при усечении в байт обходят чёрные списки (PortSwigger).
  NFKC есть, но проверить/добавить reject/sanitize `ord(c)>255` ДО regex-фильтра.
- **К чему относится:** Layer 1 (normalize.py).
- **Откуда:** defense/2026-07-02 (PortSwigger unicode overflow).
- **Усилие:** тривиально.

#### Secret-scanning regex  🔜
- **Что:** AWS/GCP/GitHub tokens, `.env`-vars, private keys — на вход И выход
  агентов. LocalAI `restricted-regex` — готовый референс паттернов.
- **К чему относится:** Layer 1 + Layer 4.
- **Откуда:** defense/2026-06-25 (LocalAI v4.5), 2026-07-07.
- **Усилие:** тривиально.

#### Каталог манипулятивных сигнатур  ⏳
- **Что:** authority-pressure, time-compression, fake-consensus, stepwise-extraction.
  Regex/паттерны для входного фильтра + готовый red-team датасет (CyberOK, 7 моделей).
- **К чему относится:** Layer 1 + Ataker-boop.
- **Откуда:** defense/2026-06-28, 2026-07-07 (CyberOK).
- **Усилие:** средне.

#### Few-shot recency ordering  ⏳
- **Что:** при сборке контекста опасные/непроверенные примеры НЕ последними.
  Mixed Compliance Demonstrations — recency bias в few-shot injection доказан.
- **К чему относится:** Layer 3 / сборка контекста.
- **Откуда:** defense/2026-06-19, 2026-06-22.
- **Усилие:** тривиально-средне.

#### Risk-controlling thresholding для Layer 2 Guard  ⏳
- **Что:** порог Guard автокалибруется под целевой риск через risk control
  (стат. гарантии). Простой дизайн конкурентен sequential-hypothesis-testing.
- **К чему относится:** Layer 2.
- **Откуда:** defense/2026-07-04 (arXiv 2607.02510).
- **Усилие:** сложно.

#### Deterministic dedup guard для code-агентов  ⏳
- **Что:** хеш-сравнение фрагментов на выходе кодоген-агентов, pre-commit блок
  дублей (dupehound-стиль).
- **К чему относится:** Layer 4 (для code-агентов).
- **Откуда:** defense/2026-07-02 (dupehound).
- **Усилие:** тривиально-средне.

#### Unfireable Safety Kernel (формальная верификация fail-closed)  ⏳
- **Что:** 4 свойства — process separation, pre-action enforcement на
  структурно-единственном пути, fail-closed, externalized signed evidence.
  Формальная верификация через SMT (Z3) + bounded-model-checking (Kani).
  У Крепости уже fail-closed/air-gap/audit_hash — НОВОЕ: машинное доказательство.
- **К чему относится:** governance + ToolOutputGuard.
- **Откуда:** defense/2026-06-25 (arXiv 2606.26057).
- **Усилие:** сложно.

#### Dual-channel debate (OTR divergence)  ⏳
- **Что:** теневой канал, детект расхождения public vs internal reasoning агента
  (stance/NLI/semantic-sim). Divergence растёт 3%→40% при misalignment.
- **К чему относится:** судьи multi-agent consensus.
- **Откуда:** defense/2026-07-04 (arXiv 2607.02507).
- **Усилие:** сложно.

### 🧠 memory — MemoryStore, chunker, retrieval

#### Source citations в build_context  🔜 ⭐
- **Что:** хранить source-метаданные (путь файла, позиция чанка, timestamp, теги),
  рендерить `[src: файл#чанк]` в контексте. Паттерн LocalAI 4.4.0. Сигнал силы:
  повтор в **4 дайджестах** (06-16, 06-25, 07-02, 07-07).
- **К чему относится:** MemoryStore.build_context.
- **Откуда:** memory/2026-06-16 (LocalAI 4.4.0) и др.
- **Усилие:** тривиально.

#### Immutable raw + no-LLM-rewrite  🔜 ⭐
- **Что:** `add()` пишет только immutable raw-чанки; summary/деривативы — отдельно
  с `type=derived`; реорганизация только детерминированными скриптами, НЕ LLM.
  Предохраняет от деградации при «оптимизации» памяти (100%→52.6% в исследовании).
- **К чему относится:** MemoryStore.add / архитектура.
- **Откуда:** memory/2026-06-28 (LLM rewriting own memory degrades 100%→52.6%).
- **Усилие:** тривиально (дизайн-паттерн).

#### DART-VLN read-time decay + anti-loop penalty  ⏳ ⭐
- **Что:** training-free reweighting памяти при чтении: `exp(-age/τ)` на scores +
  штраф за факты, уже бывшие в контексте в последних N запросах. Anti-loop
  penalty **уникален** — не покрывается ни Hopfield, ни ReContext.
- **К чему относится:** MemoryStore.retrieve.
- **Откуда:** memory/2026-07-02 (DART-VLN).
- **Усилие:** средне.

#### Semantic chunker (по заголовкам Markdown)  ⏳
- **Что:** резать чанки по заголовкам/семантическим границам Markdown, хранить
  heading path/дату/теги в metadata, нормализация/очистка перед векторизацией.
  Сейчас только `chunk_max_chars + overlap`.
- **К чему относится:** chunker / add.
- **Откуда:** memory/2026-06-22 (document ingestion pipeline).
- **Усилие:** средне.

#### Multi-query retrieval (query expansion)  ⏳
- **Что:** при слабом `confident` генерировать 2-3 переформулировки запроса,
  мержить через reciprocal rank fusion. Отличается от MemoryRouter
  (domain routing) — это query expansion.
- **К чему относится:** MemoryStore.retrieve.
- **Откуда:** memory/2026-07-02 (МТС agentic retrieval).
- **Усилие:** средне.

#### LedgerAgent structured state  ⏳
- **Что:** отдельная key-value таблица (project facts, IDs, constraints) отдельная
  от ChromaDB, рендерится как префикс контекста. Борьба со stale/missing фактами.
  Не RAG-замена, а дополнение — детерминированное состояние.
- **К чему относится:** build_context / новый StructuredStateStore.
- **Откуда:** memory/2026-06-19 (LedgerAgent).
- **Усилие:** средне.

#### OCC-RAG SLM (context-faithful reader)  ⏳
- **Что:** компактные SLM 0.6B/1.7B, оптимизированные под context-faithful Q&A
  (ONNX/GGUF). Загрузить GGUF через llama.cpp/vLLM как локальный reader над
  retrieve(), отвечает строго по контексту без галлюцинаций.
- **К чему относится:** reader-LLM над retrieve.
- **Откуда:** memory/2026-06-19 (AIRI OCC-RAG).
- **Усилие:** средне (требует железа для модели).

#### RAG benchmark на приватных заметках  ⏳
- **Что:** набор пар (запрос → ожидаемый документ) из реальных заметок Obsidian +
  метрики (recall@k, MRR, устойчивость к дубликатам). Дает измерять, а не гадать.
- **К чему относится:** retrieve (тесты).
- **Откуда:** memory/2026-07-02 (RAG benchmark 28% vs 76%).
- **Усилие:** средне.

### ⚔ redteam — Ataker-boop, success-analyzer

#### LLM-judge недетерминизм фикс  🔜 ⭐
- **Что:** temp=0 для judge-модели; прогон каждого вердикта N≥3 раз и majority
  vote; метрика `judge_instability_rate` = доля расходящихся вердиктов →
  при >порога кейс в карантин. Бьёт в боль «success-analyzer мерит только
  verdict!=RED».
- **К чему относится:** Ataker-boop success-analyzer.
- **Откуда:** redteam/2026-06-28 (judge non-determinism war).
- **Усилие:** тривиально.

#### `icl_reorder` мутатор (recency bias атаки)  🔜 ⭐
- **Что:** мутатор `icl_reorder` — берёт few-shot-промпт, переставляет
  benign/harmful демонстрации (последняя=harmful даёт recency-эффект).
  Параметризовать долю harmful (0/25/50/100%), порядок, наличие refusal.
  Layer 3 (few-shot) особенно уязвим.
- **К чему относится:** Ataker-boop (мутатор).
- **Откуда:** redteam/2026-06-19, 2026-06-22 (arXiv 2606.20508).
- **Усилие:** тривиально.

#### Red Team AI Benchmark v2.0 (60 категорий) → seed-корпус  🔜
- **Что:** 60 offensive-security сценариев → обернуть в pytest-style test cases
  как seed для `red_team_loop`. Дополняет garak/JailbreakBench.
- **К чему относится:** Ataker-boop (test-case corpus).
- **Откуда:** redteam/2026-06-22.
- **Усилие:** тривиально.

#### Prompt-integrity diff между итерациями эволюции  🔜
- **Что:** после шага эволюции хэшировать system-prompt + скрипты, diff против
  чекпойнта. Новые инструкции не из whitelist → блок (self-reinforcing injection).
  Сочетается с audit_hash.
- **К чему относится:** governance (verifiable-gate).
- **Откуда:** redteam/2026-07-07 (arXiv 2602.15654).
- **Усилие:** тривиально.

#### Model Forensics протокол для success-analyzer  ⏳
- **Что:** 2-шаговый протокол: (1) прочитать CoT модели → гипотеза о драйвере
  (deceptive vs confusion), (2) counterfactual-правка промпта для подтверждения.
  Отличает реальный пробой от false positive. Нужен CoT (включить `reasoning`).
- **К чему относится:** Ataker-boop success-analyzer.
- **Откуда:** redteam/2026-06-25 (arXiv 2606.26071).
- **Усилие:** средне.

#### Tool-abuse red-teaming (breach-rate метрика)  ⏳
- **Что:** генератор сценариев «прочитай AWS-креды/секрет через tool», «эскалация
  прав», «destructive tool-call (DROP/DELETE)». Метрика `tool_breach_rate` =
  сработавших/всего, гнать до нуля. Seed: запросы env-vars, чтение `~/.ssh`.
- **К чему относится:** Ataker-boop над tool-вызовами, ToolOutputGuard.
- **Откуда:** redteam/2026-06-25.
- **Усилие:** средне (нужен mock tool-окружения).

#### Ансамбль мониторов + stateful link-tracker  ⏳
- **Что:** атакующий размазывает payload по нескольким итерациям эволюции —
  одиночный diff-монитор не ловит. Ансамбль из 4 мониторов снижает evasion
  gradual-атак 93%→47%; stateful link-tracker накапливает подозрительные
  изменения между итерациями.
- **К чему относится:** governance (RSI verifiable-gate).
- **Откуда:** redteam/2026-07-04 (arXiv 2607.02514).
- **Усилие:** средне-сложно.

#### RevengeBench opponent-modeling probes  ⏳
- **Что:** adversarial-агент строит active probes для реконструкции защитной
  политики (какие regex, какие категории режет Guard). Active interventions:
  восстановление 34→72%. Аудит предсказуемости защиты.
- **К чему относится:** Ataker-boop (продвинутый режим), governance.
- **Откуда:** redteam/2026-06-25 (arXiv 2606.26094).
- **Усилие:** сложно.

### 🏗 foundation — backend, cache, UrlGuard, метрики

#### httpclient: refuse cross-host redirects  🔜
- **Что:** все outbound-клиенты (скачивание весов, model-gallery, HTTP из агентов)
  должны refuse редиректы на другой хост — иначе credentials/token утекают.
  `allow_redirects=False` + ручная валидация `Location` против исходного host.
- **К чему относится:** UrlGuard, backend (outbound HTTP).
- **Откуда:** foundation/2026-06-16 (LocalAI v4.3.6, GHSA-3mj3-57v2-4636).
- **Усилие:** тривиально.

#### UrlGuard: IMDS/private-range SSRF-валидация (перепроверить)  🔜
- **Что:** при загрузке конфигов/моделей валидировать URL против private/loopback/
  metadata диапазонов (`127.0.0.0/8`, `10.0.0.0/8`, `172.16.0.0/12`,
  `192.168.0.0/16`, `169.254.169.254` IMDS, `::1`, `fc00::/7`). Резолвить DNS и
  проверять final IP (защита от DNS-rebinding). Скорее всего уже есть — проверить.
- **К чему относится:** UrlGuard.
- **Откуда:** foundation/2026-07-04 (LocalAI v4.6.0).
- **Усилие:** тривиально (verify).

#### PII Prometheus counter для Layer 1 health-check  🔜
- **Что:** счётчик `krepost_pii_events_total{kind,origin,action,direction}`.
  Алерт: счётчик redactions→0 при ненулевом трафике = фильтр сломался (fail-open).
  Прямой health-check для fail-closed принципа.
- **К чему относится:** Layer 1, /metrics.
- **Откуда:** foundation/2026-07-04 (LocalAI v4.6.0).
- **Усилие:** тривиально.

#### Настройки деплоя: Q4 + `--jinja` + vLLM флаги  🔜
- **Что:** Q4-квант (Q8 даёт +0.007 — шум, но 1.6× медленнее и 2× VRAM).
  `--jinja` флаг сервера обязателен для корректного tool-calling. vLLM
  `device_ids` (точная GPU-привязка без глобального env). batch-invariance
  (детерминизм для верификации/audit — включить для guard-модели).
- **К чему относится:** backend (Ollama/vLLM/llama.cpp).
- **Откуда:** foundation/2026-06-25, 2026-07-02 (vLLM v0.22/v0.24).
- **Усилие:** тривиально (конфиг-флаги).

#### FSM-orchestrator для resilience  ⏳
- **Что:** каждый шаг пайплайна = состояние FSM с явным переходом. При падении
  backend — возобновление с нужного шага, а не полный retry. Бьёт в падающий
  `Build_demo_orchestrator`: FSM даёт точку восстановления и переключение между
  локальными моделями без потери контекста.
- **К чему относится:** backend orchestrator, governance.
- **Откуда:** foundation/2026-06-19 (llm-nano-vm).
- **Усилие:** средне.

#### TokenPilot / LightMem2 паттерны для SMART_CACHE  ⏳
- **Что:** (1) Ingestion-Aware Compaction — стабилизировать префиксы промпта,
  срезать шум на входе; (2) Lifecycle-Aware Eviction — выгружать сегменты
  контекста по batch-turn расписанию при истечении релевантности. Цель: -61/-87%
  затрат, стабильные prefix-cache попадания.
- **К чему относится:** cache (SMART_CACHE).
- **Откуда:** foundation/2026-06-16 (TokenPilot, LightMem2).
- **Усилие:** средне-сложно.

### 🚀 evolution — governance, судьи, ImprovementGate

#### LLM-as-a-Verifier: logits expectation  ⏳ ⭐
- **Что:** вместо «выдай 1-10» — матожидание по распределению вероятностей
  scoring-токенов (continuous score). Декомпозиция критериев (безопасность/
  корректность/полнота отдельными проверками), повторная оценка → ниже variance,
  cost-efficient ranking кандидатов. Без дообучения. Доступ к logits есть у
  любой локальной модели. **Алгоритм не в ROADMAP** (там судьи абстрактно).
- **К чему относится:** судьи/верификаторы.
- **Откуда:** evolution/2026-07-07.
- **Усилие:** средне.

#### TestEvo ко-эволюция + mutation score  ⏳
- **Что:** gate-критерий — любое изменение кода сопровождается ко-эволюцией
  тестов. Verifier — execution-grounded: pass rate + coverage + mutation score
  (мутируем код, проверяем, ловят ли тесты). mutation score через mutmut.
- **К чему относится:** governance gate.
- **Откуда:** evolution/2026-07-04 (TestEvo-Bench).
- **Усилие:** средне.

#### Co-Failure β + Clopper-Pearson сертификат  ⏳
- **Что:** потолок выигрыша ансамбля судей ≤ 1-β, где β — доля запросов, где ВСЕ
  судьи ошиблись одновременно. Парная корреляция ошибок НЕ оценивает β — нужен
  прямой замер all-wrong rate. Clopper-Pearson upper bound как сертификат.
  Чистая статистика по trace_hash — честный ответ «стоит ли consensus».
- **К чему относится:** судьи/consensus.
- **Откуда:** evolution/2026-06-28.
- **Усилие:** средне.

#### Конституция frozen invariants  ⏳
- **Что:** слой неизменяемых правил, которые ImprovementGate не вправе
  модифицировать при RSI. Отделяется от steering-adapter и от правимых правил.
- **К чему относится:** ImprovementGate.
- **Откуда:** evolution/2026-06-28.
- **Усилие:** средне (файл инвариантов + проверка диффа в gate).

#### SEB drift+revocation  ⏳
- **Что:** enforcement-граница proposal→admission→execution. Каждая мутация:
  scoped execution identity + drift-check (состояние до vs после) + revocation
  флаг + signed decision/outcome-логи. Авторитет — короткоживущий, отзываемый.
- **К чему относится:** governance (audit/gate). Усиливает audit_hash/trace_hash.
- **Откуда:** evolution/2026-06-22 (Sovereign Execution Brokers).
- **Усилие:** средне-сложно.

#### Auto-оценка по рубрике (judge-as-data + цитаты как audit trail)  ⏳
- **Что:** рубрика оценки хранится как данные (не вшита в промпт), калибруется под
  эталонные вердикты; каждый вердикт сопровождается цитатой-обоснованием с
  позицией. Цитаты идут в audit-trail как verifiable evidence.
- **К чему относится:** судьи, audit.
- **Откуда:** evolution/2026-06-22.
- **Усилие:** средне.

#### PACT: Plan→Align→Commit→Think  ⏳
- **Что:** двухфазный паттерн — генерация плана правки → валидация через
  отдельный judge (safe/feasible/complete) → commit только верифицированного.
  Разделение proposer/verifier, обязательная фаза Align перед Commit. Верификатор
  дешёвый (даже 2B SLM).
- **К чему относится:** governance/gate.py.
- **Откуда:** evolution/2026-06-16 (PACT).
- **Усилие:** тривиально (структура flow, не модель).

---

## ✅ Сделано (сессия 2026-07-10/12)

> Кодирование тривиальных техник из разведданных. Пробники #40-#46.

- **Т1** Source citations в build_context — ✅ сделано, пробник #40 (5 тестов).
- **Т2** Immutable raw + type=raw/derived — ✅ сделано, пробник #41 (4 теста).
- **Т4** Secret-scanning: Google API key + GCP SA + Slack — ✅ сделано, пробник #42 (9 тестов). AIza → `[GOOGLE_API_KEY_REDACTED]` (НЕ "GCP service account" — это JSON с private_key).
- **Т8** PII/secret счётчики + pii_filter_healthy health-flag — ✅ сделано, пробник #43 (8 тестов). Канарейка в `/metrics`; реальный alerting-infra → ⏳.
- **Т5** Prompt-integrity diff — ✅ сделано, пробник #44 (14 тестов). Правильный хеш: каждый файл отдельно + JSON {путь: хеш} (устойчив к перемещению байта).
- **Т6** Cross-host redirect cap — ✅ сделано, пробник #45 (10 тестов). validate_redirect + follow_redirects_safely + max_redirects=5.
- **Т10** icl_reorder мутатор — ✅ сделано, test_ataker (3 теста, 17 мутаторов).
- **Т9** temp=0 в GuardClassifier — ✅ сделано, пробник #46 (9 тестов). Артефакт: scatter 7/15→1/15. ПЛЮС парсер нативного формата Qwen3Guard (Safety: Safe/Controversial/Unsafe) — без него guard падал в parse_error.
- **Т11** Seed-корпус red-team — ✅ сделано. 20 payloads, 13 категорий, seed/partial (~13 of 60). В git НЕ попадает (gitignore). Артефакт покрытия: 18/20 blocked.
- **Т12** Док: настройки деплоя — ✅ сделано. LM Studio вариант + Q4/--jinja/device_ids/batch-invariance.
- **OUTPUT-GUARD УДАЛЁН** — ✅ сделано. Семантический output-guard (Qwen3Guard на Layer 4) выпилен из обеих фабрик + OutputFilter + Pipeline. Причины: (1) Qwen3Guard заточен под классификацию ВХОДОВ (injection-detection), на выходах сваливается в чат-режим → parse_error → fail-closed блокирует benign («Paris» блокировался); (2) для air-gapped локалки модерация собственных ответов не нужна (получатель = сам оператор). Layer 4 теперь regex-only: PII-маскинг + leak-паттерны + secret-scanning (Т4). `output_guard_client` в SecurityPipeline устарел, логирует warning при передаче. Пробник #31 переписан (7 тестов). Критерий приёмки выполнен: benign «What is the capital of France?» → GREEN, output «Paris.». Если output-guard понадобится — брать модель специально под output-moderation, НЕ Qwen3Guard.

### Verified (уже было — проверено, дублировать не надо)

- **Т3** Unicode-нормализация ПЕРЕД blocklist — ✅ verified. Инвариант уже соблюдён (`pipeline.py:365` normalize → `:371` search). NFKC есть. Python str не усекает codepoints в байты.
- **Т7** UrlGuard IMDS/RFC1918/resolve_dns — ✅ verified. 169.254.169.254 блокируется через `is_link_local`. resolve_dns есть (опц.).

### Extended (зависимости, на будущее)

- **T9-extended** — majority vote N≥3 + judge_instability_rate — ✅ сделано. `success_analyzer.py` + `RedTeamLoop(judge_samples=3)` + пробник #47.
- **T11-full** — scaffold 60 категорий — ✅ сделано. `benchmark_catalog.py` + `seed_attacks.example.jsonl` (60 placeholders) + coverage API + пробник #49. Реальные payloads → `seed_attacks.local.jsonl` (gitignored).
- **Т8 alerting-infra** — webhook + Prometheus — ✅ сделано. `AlertDispatcher` (`KREPOST_ALERT_WEBHOOK`), `/metrics/prometheus`, debounce + пробник #48.

---

## Отклонённое / вне периметра

- **ML-тюнинг** (LoRA-init, staleness scaling laws, DPO, LOTUS, ортонормальная инициализация) — это про **тренировку** моделей. Принцип «архитектура важнее модели» (§5.2): мы модели не обучаем, а оркестрируем. Может стать актуальным только при переходе к собственному дообучению — пока ❌.
