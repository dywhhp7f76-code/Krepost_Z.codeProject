# Spec Draft — Planner-Executor Attacker (Ataker-boop v2)

> **Статус:** ЧЕРНОВИК — дополняется по мере brainstorming-сессии.
> **Дата:** 2026-07-22
> **Автор:** оператор + ZCode

---

## 0. Зафиксированные решения из brainstorming

### 0.1. Архитектурный паттерн
- **Planner-Executor pattern** (классика ML-literature).
- **Творец (Planner)** = «мозг», сильная LLM, рассуждает, планирует, рефлексирует.
- **Исполнитель (Executor)** = «молоток», ебашит Крепость payload'ами от Творца.
- Выбран **Подход 2**: Planner в adversarial петле (~500 строк кода).

### 0.2. Роли и интеллект
- **Творец** = единственная LLM в новой части (думает, саморефлексирует).
- **Исполнитель** = **СУЩЕСТВУЮЩИЙ КОД** (`AttackGenerator` + `MutationEngine` + `RedTeamLoop`).
- **НЕ добавляем вторую LLM** для Executor'а — оставляем существующие 16 мутаций.
- Решение оператора: «творец придумывает — исполнитель ебашит — потом отчёт по неудачам и передает творцу».

### 0.3. Модели (железо M5 32GB)

| Роль | Модель | RAM |
|------|--------|-----|
| **Творец (Planner)** | `Meta-Llama-3.1-8B-Instruct-abliterated` **Q5_K_M** (~5.34 GB) | ~5.3 GB |
| **Embedder для RAG** | BGE-M3 (как в основном проекте) | ~1.5 GB |
| **ChromaDB** | in-process | ~0.5 GB |
| macOS + overhead | — | ~4 GB |
| **ИТОГО** | | **~11.3 GB** |
| **СВОБОДНО** | | **~21 GB** ✅ |

Cross-architecture к жертве (Qwen3.6-35B) — Llama ≠ Qwen, атакер видит чужие слепые зоны.

### 0.4. Фидбек Исполнитель → Творец
- **ТОЛЬКО** `verdict` (GREEN/YELLOW/RED) + `actual_layer` (Layer1-Regex / Layer2-Guard / ...).
- **НЕ** передаём ответ жертвы (контент ответа Крепости).
- Причина: black-box red team + экономия tokens + не раскрывать Творцу internals Крепости.

### 0.5. Ритм петли
- **Каждую итерацию**: Творец генерит пачку → Executor ебашит → отчёт → Творец генерит следующую с учётом фидбека → повтор.
- Параметр: `batch_size` (по умолчанию ~20 атак за итерацию).

### 0.6. Критерий останова
- **Early stopping**: петля останавливается ПРИ первом bypass ИЛИ по достижению лимита итераций.
- Что раньше сработает.
- Параметры: `max_iterations` (default ~10), `stop_on_bypass=True`.

### 0.7. База знаний (человек в петле)
- Markdown-файлы, пополняемые оператором вручную.
- Творец читает через RAG (ChromaDB + BGE-M3).
- Оператор пополняет **обе стороны**: техники атак + техники защиты Крепости.

---

## 1. Архитектура (Секция 1 — подтверждена с правкой)

### Ключевая правка (зафиксирована)
> **Творец НЕ общается с Крепостью напрямую.**
>
> Исполнитель сам формирует фидбек из результатов pipeline.process() —
> он уже знает verdict, layer, bypassed из SecurityContext.
>
> Для Творца Крепость = абстрактная чёрная коробка. Его интерфейс —
> только к Исполнителю: `planner.generate_attacks(feedback) -> payloads`.
>
> Творец даже не знает что Крепость существует.

### Исправленная схема

```
                 payloads
Творец ──────────────────────▶ Исполнитель
  ▲                                │
  │                                │ HTTP /v1/query
  │                                ▼
  │                           ┌─────────┐
  │                           │ Крепость│  ← тупо отвечает
  │                           └────┬────┘
  │                                │
  │     verdict + layer            │
  ◀────────────────────────────────┘
   Исполнитель сам формирует фидбек
   (bypassed=True/False, actual_layer)
```

### Состав компонентов

| Компонент | Статус | Где живёт |
|-----------|--------|-----------|
| **Творец (Planner)** | 🔨 НОВЫЙ | `ataker/planner.py` (новый файл ~300 строк) |
| **База знаний** | 🔨 НОВОЕ | `ataker/knowledge/` (markdown) + RAG адаптер |
| **Executor** | ✅ СУЩЕСТВУЕТ | `ataker/generator.py` + `mutations.py` + `red_team_loop.py` |
| **Coordinator** | 🔨 НОВЫЙ | `ataker/adversarial_loop.py` (связывает всё) |

### Принципы
1. **Не трогаем ядро.** Executor = существующий `RedTeamLoop`. 775+ тестов остаются рабочими.
2. **Творец ортогонален.** Это надстройка, можно запускать с/без неё.
3. **Планировщик не видит ответ жертвы.** Только verdict + слой. Чистый black-box.
4. **База знаний — человек в петле.** Оператор пополняет markdown, Творец читает через RAG.
5. **Физическая изоляция сохранена.** Твинц на Air, жертва на Studio, HTTP между ними.

---

## 2. Планировщик (Секция 2 — пересмотренная концепция)

### ⚠️ КЛЮЧЕВАЯ ПРАВКА (зафиксирована 2026-07-22)
> **Творец — НЕ генератор текста payload'ов. Он — стратег/дирижёр
> над СУЩЕСТВУЮЩИМ арсеналом ядов.**
>
> У Творца уже есть готовый стек:
> - `ATTACK_TEMPLATES` (15 категорий, ~100 шаблонов) в generator.py
> - `MutationEngine` (16 мутаций: base64, homoglyph, zero_width, ...)
> - `seed_attacks.local.jsonl` (реальные атаки от оператора)
> - `generate_chained()` (цепочечные мутации depth=2+)
>
> Задача Творца — НЕ придумывать текст атаки с нуля через LLM.
> Его задача — **выбирать из арсенала и направлять мутации** исходя
> из фидбека и RAG.

### Концепция «дирижёр над арсеналом»

```
Творец видит фидбек → лезет в RAG → командует:
  «возьми 3 шаблона SOCIAL_ENGINEERING + мутация prefix_innocent»
  «возьми 5 шаблонов ROLE_HIJACK + мутация homoglyph»
                │
                ▼
Исполнитель (СУЩЕСТВУЮЩИЙ код):
  ATTACK_TEMPLATES[category] + MutationEngine.mutate(template, mutation)
                │
                ▼
  готовые payload'ы → Крепость
```

### Почему не «LLM генерит текст»
| | LLM-генератор текста (плохо) | Дирижёр над арсеналом (хорошо) |
|---|---|---|
| Источник payload'ов | LLM выдумывает | Готовые ATTACK_TEMPLATES |
| Мутации | LLM сама кодирует b64 | Существующий MutationEngine (16 шт, tested) |
| Галлюцинации | Частые | Минимальные (только в стратегии) |
| Скорость | Медленно | Быстро |
| Тесты | Переписывать | Не трогаем |

### PlannerOutput (пересмотренный)

```python
@dataclass
class PlannedAttack:
    # НЕ текст payload'а, а РЕЦЕПТ сборки из арсенала:
    template_category: AttackCategory   # из какой категории брать шаблон
    template_index: Optional[int]       # конкретный шаблон (или random)
    mutations: List[str]                # какие мутации применить (из 16 существующих)
    chain_depth: int = 1                # глубина chain_mutate
    expected_layer: str                 # какой слой хочет пробить
    technique_ref: Optional[str]        # ссылка на RAG-технику
    reasoning: str                      # почему именно этот рецепт

@dataclass
class PlannerOutput:
    reasoning: str                       # chain-of-thought (виден оператору)
    attack_recipes: List[PlannedAttack]  # рецепты сборки
    hypothesis: str                      # план на следующие итерации
```

### Chain-of-thought (видно оператору)

```text
<reasoning>
Итерация 3. Layer2-Guard заблокировал 8/8 direct_injection.
Layer1-Regex пробивается base64 (3/5 прошли).
Гипотеза: Guard хорошо детектит прямые фразы, но слаб на social engineering.

План: 5 SOCIAL_ENGINEERING + prefix_innocent,
      5 ROLE_HIJACK + homoglyph + base64 (chain depth=2).
</reasoning>

<recipes>
[...рецепты сборки...]
</recipes>
```

### RAG-поиск техник
Перед каждой итерацией Координатор делает запрос в базу знаний:
```python
query = "techniques to bypass Layer2-Guard when direct injection fails"
retrieved = rag.search(query, top_k=5)
```
Результат подмешивается в PlannerInput → Творец видит техники и может
ссылаться на них в `technique_ref`.

### Открытые вопросы по Секции 2
- [ ] Должен ли Творец видеть конкретные шаблоны из ATTACK_TEMPLATES (с текстом),
      или только названия категорий? (видеть текст = больше контекста,
      но длиннее промпт)
- [ ] Список 16 мутаций передаём Творцу в системный промпт?
- [ ] Разрешать ли Творцу chain_depth > 2 (рискованно — мутированный payload
      может стать невалидным)?

---

## 3. База знаний и RAG (Секция 3 — TBD)

_TBD: структура markdown-файлов, как RAG индексирует, как оператор пополняет, как Творец запрашивает._

---

## 4. Петля и протокол (Секция 4 — TBD)

_TBD: формат FeedbackEntry, batch_size, история фидбека (сколько итераций Творец помнит), логирование._
---

## 5. Интеграция с существующим кодом (Секция 5 — TBD)

_TBD: что конкретно добавляем в ataker/__init__.py, как Coordinator оркеструет, env vars, CLI._

---

## 6. Тестирование и ошибки (Секция 6 — TBD)

_TBD: что тестировать, моки LLM, edge cases (LLM offline, пустой RAG, loop без bypass)._

---

## Открытые вопросы (TBD)
- [ ] Секция 2: формат CoT Творца
- [ ] Секция 3: структура markdown-базы знаний
- [ ] Секция 4: история фидбека (сколько итераций помнит Творец)
- [ ] Секция 5: env vars для подключения к LLM Studio
- [ ] Секция 6: мокирование LLM в тестах

---

## Приложение А. Реальная карта атакера (после полного аудита 2026-07-22)

### А.1 Арсенал (как есть)
- **17 мутаций** (не 16): base64, homoglyph, zero_width, case_mix, token_split, rot13,
  reverse, leetspeak, whitespace, prefix_innocent, suffix_distract, language_switch,
  markdown_wrap, xml_wrap, json_wrap, multi_encoding, **icl_reorder** (T10 recency-bias).
- **15 категорий** атак: DIRECT_INJECTION, ROLE_HIJACK, SYSTEM_PROMPT_LEAK,
  ENCODING_BYPASS, HOMOGLYPH, CHAT_TEMPLATE, XML_INJECTION, CONTEXT_OVERFLOW,
  MULTILINGUAL, LOGIC, SOCIAL_ENGINEERING, PII_EXTRACTION, MULTI_TURN, JAILBREAK,
  ADVERSARIAL_SUFFIX, OUTPUT_MANIPULATION.
- **70 шаблонов** в `ATTACK_TEMPLATES` (не ~100).
- **60 категорий бенчмарка** (группы A-G) — готовая таксономия целей.
- **32 реальные атаки** в `seed_attacks.local.jsonl` (покрытие 22/60 бенчмарка).
- **2 LLM-слота**:
  - `AttackGenerator(llm_generate=...)` → `generate_with_llm(category, count)` (stateless, generator.py:236)
  - `judge_ucs_llm(...)` в evals_ucs.py (через env ATAKER_JUDGE_URL/ATAKER_JUDGE_MODEL)

### А.2 Vault — 3 таблицы SQLite
- **payloads**: id, category, original, mutated, mutations_applied, expected_verdict,
  expected_layer, metadata, fingerprint, created_at, source
- **results**: payload_id, actual_verdict, actual_layer, confidence, latency_ms,
  bypassed_defense, pipeline_version, run_id, tested_at
- **weaknesses**: payload_id, category, description, expected_layer, severity,
  status (open/resolved), discovered_at, resolved_at, resolution_comment

### А.3 SecurityContext (Крепость → атакер)
Доступные поля после `pipeline.process(text, session_id)`:
- `verdict` (GREEN/YELLOW/RED) — основной сигнал bypass
- `violation_layer` (Layer1-Regex / Layer2-Guard / Layer3-FewShot / Layer4-OutputFilter / RateLimiter / PipelineError)
- `confidence` (float)
- `attack_vector` (детали: "Direct Injection: ignore previous...")
- `metadata` (layer1_time_ms, layer2_time_ms, layer3_time_ms, total_latency_ms, cache_hit, trusted)
- `audit_hash`, `trace_hash` (sha256)
- `timestamp`, `policy_version`, `normalization_version`
- В данный момент атакер использует только verdict/layer/confidence.

### А.4 Что ПОЛНОСТЬЮ отсутствует (гэпы для Planner)
- ❌ Agent loop (только batch-loop `generate_all → test_all → report`)
- ❌ RAG (chromadb в deps но не импортируется нигде)
- ❌ Knowledge base (weaknesses без структуры/embeddings)
- ❌ Reflection step (bypass НЕ анализируется LLM)
- ❌ Feedback в генератор (`generate_with_llm` stateless, не помнит историю)
- ❌ Memory по истории сессии (каждый payload с одним session_id="red-team")
- ❌ Budget/ranking payloads
- ❌ HTTP-executor (scripts/ не существуют, только Python-вызовы)

### А.5 Что ПЕРЕИСПОЛЬЗУЕТСЯ для Planner (готовые блоки)
- `MutationEngine.mutate/mutate_n/chain_mutate` — 17 мутаций (tested)
- `AttackGenerator.generate_with_llm(llm_generate=...)` — готовая LLM-рельса
- `AttackGenerator.generate_from_templates/generate_chained` — batch-генерация
- `load_seed_corpus()` + `seed_attacks.local.jsonl` — 32 реальные атаки
- `AttackVault` — персистентность + `get_bypassed_payloads(run_id)` для анализа
- `analyze_verdicts` — majority vote + instability (judge-noise фильтр)
- `RedTeamLoop.run_single(text)` — точечный прогон
- `benchmark_catalog` — таксономия 60 категорий с маппингом → 15 AttackCategory
- `evals_ucs` — метрики Useful/Correct/Safe + LLM-judge-слот (pattern для env-config)

### А.6 Ключевые переиспользуемые env-переменные
- `ATAKER_JUDGE_URL` — OpenAI-compatible endpoint (LM Studio :1234 на Air)
- `ATAKER_JUDGE_MODEL` — имя модели для judge
- Pattern: тот же env-pattern используем для Planner LLM

---

> **История изменений**
> - 2026-07-22: создан черновик, зафиксированы решения из brainstorming (секции 0.1–0.7), секция 1 с правкой о чёрной коробке.
> - 2026-07-22: после полного аудита кода агентом добавлено Приложение А (реальная карта), исправлены ошибки (17 мутаций не 16, 70 шаблонов не ~100, scripts/ не существуют).
> - 2026-07-22: добавлено Приложение Б (источники из redteam-2026-07-19).
> - 2026-07-22: добавлено Приложение В (consolidated research от 3 агентов по redteam 2025-2026).

---

## Приложение В. Consolidated redteam research (3 агента, 2025-2026)

Источники: WebSearch через playwright + curl к arXiv/GitHub/HF. 3 параллельных агента:
- #1: Jailbreak techniques 2025-2026
- #2: Prompt injection fuzzers + методы генерации
- #3: Guard model bypass (конкретно против Qwen3Guard/Layer 1-4)

### В.1 Главное эмпирическое открытие: BELLS benchmark

**arXiv 2507.06282** (CEA Saclay, июль 2025) — систематический бенчмарк guard-моделей:
- LLM Guard: **0.0% detection** почти везде
- Prompt Guard: 0-20% по категориям
- Llama-Guard-4 12B: 43-87% (но «падает почти до нуля» на новых форматах)
- **GPT-4 просто спросить «вредно или нет» превосходит ВСЕ специализированные guard**
- Metacognitive incoherence: Claude 3.7 отвечает на 30% запросов, которые сам признал вредными

**Вывод для нашего Qwen3Guard-Gen-4B (Layer 2):** наследует слабости LLM-based guard — specification gaming, слабая генерализация на новые форматы, низкий detection на base64/LRL. Это **слабейшее звено Крепости**.

### В.2 Tier-S: обход 3+ слоёв одновременно

| # | Техника | Слои | ASR | Источник |
|---|---------|------|-----|----------|
| 1 | **Low-Resource Language** (Zulu/Swahili/Bengali/Urdu) | L1+L2+L3 | GPT-4 refusal <40% | arXiv:2310.02446 |
| 2 | **FITD (Foot-In-The-Door)** multi-turn decomposition | L2+L3 (single-shot) | 94% ASR | arXiv:2502.19820, garak/probes/fitd.py |
| 3 | **CodeJailbreaker** (intent в commit msg) | L1+L2+L3 | >classic jailbreak | arXiv:2503.17953 |
| 4 | **Multi-turn Crescendo** (эскалация) | L2+L3 | SOTA | Microsoft, arXiv:2404.01833 |

### В.3 Tier-A: надёжный bypass Layer 2 (Qwen3Guard)

| # | Техника | Механизм | Источник | Реализация |
|---|---------|----------|----------|------------|
| 5 | **EchoGram flip-tokens** | whitebox vocab search, инвертирует вердикт guard | HiddenLayer 11/2025 | Мутация `guard_flip_suffix` (градиент по P(safe)) |
| 6 | **FlipAttack** | переворот текста (4 режима), 1 query | ICML 2025, arXiv:2410.02832 | Категория `text_flip`, 4 варианта |
| 7 | **LogiBreak** | FOL/LTL формальная логика | ACL 2026, arXiv:2505.13527 | Категория `logic_translate` |
| 8 | **Policy Puppetry** | XML/JSON/INI маскировка под конфиг | Pillar 04/2025, PyRIT | Категория `policy_puppetry` + мутация |
| 9 | **TokenBreak** | префикс-символы перед harm-словами | arXiv:2506.07948 | Мутация `token_boundary_break` |
| 10 | **GCG adversarial suffix** | whitebox градиентный поиск | arXiv:2307.15043 | Категория `gcg_suffix` (требует whitebox) |
| 11 | **Adaptive Attacks** | random search on suffix + logprobs | arXiv:2404.02151 (100% ASR!) | Улучшение Творца |
| 12 | **Base64/Caesar/Zulu** обфускация | encoding bypass | promptfoo LMVD-10893a8e | Мутации `atbash/caesar/morse/braille/binary` |

### В.4 Tier-B: против Layer 3 (cosine≥0.92, BGE-M3)

| # | Техника | Механизм | Источник |
|---|---------|----------|----------|
| 13 | **Adversarial paraphrase** | синонимы/перестановка → cosine<0.92 | arXiv:2506.07001 (NeurIPS 2025) |
| 14 | **Context dilution** | обернуть в benign story | "Cosine Similarity Lies" |
| 15 | **Keyword cloaking** | harm-слово → benign_synonym | promptfoo RAG poisoning |
| 16 | **RAG poisoning** | 5 доков → 90% манипуляция | OWASP LLM08:2025 |

### В.5 Tier-C: против Layer 4 (OutputFilter, PII)

| # | Техника | Механизм | Источник |
|---|---------|----------|----------|
| 17 | **Zero-width smuggling** | PII в U+200B/200C/200D/FEFF | Pillar in-the-wild |
| 18 | **PII в таблицах/JSON/code** | regex не матчит структурированный формат | USENIX Sec 2025 |
| 19 | **URL exfiltration** | данные в URL path/query | OpenAI mitigation paper |

### В.6 Tier-D: стратегические улучшения Творца

| # | Техника | Что даёт | Источник |
|---|---------|----------|----------|
| 20 | **AutoDAN-Turbo** | self-обучающаяся KB стратегий (= спецификация Творца!) | arXiv:2410.05295 |
| 21 | **AutoDAN-Reasoning** | test-time scaling (BoN + Beam), +15.6 п.п. ASR | arXiv:2510.05379 |
| 22 | **TAP (Tree of Attacks)** | tree-search с pruning, минимизирует queries | NeurIPS 2024, arXiv:2312.02119 |
| 23 | **PAIR feedback loop** | attacker-LLM итеративно рефайнит по фидбеку | arXiv:2310.08419 |
| 24 | **PyRIT adaptive scenario** | epsilon-greedy селектор техник | microsoft/PyRIT |
| 25 | **PE-CoA** | 5 conversation patterns multi-turn | arXiv:2510.08859 |
| 26 | **TriageFuzz** | token-aware cost-aware mutation | arXiv:2603.23269 |
| 27 | **STAR-Teaming** | multiplex network, cost-aware | arXiv:2604.18976 |
| 28 | **"From Shield to Target"** | DoS на guardrail через reasoning loops | arXiv:2606.14517 |

### В.7 Reference-фреймворки (готовый код для заимствования)

| Фреймворк | Что взять | Репо |
|-----------|-----------|------|
| **PyRIT** (Microsoft v0.14.0) | converters (мутации), AttackTechnique registry, StrategySequence, TAP/PAIR/Crescendo | github.com/microsoft/PyRIT |
| **Promptfoo** (OpenAI, MIT) | YAML-стратегии (best-of-n, jailbreak:tree/composite/hydra/goat) | github.com/promptfoo/promptfoo |
| **garak** (NVIDIA v0.15.1) | probes (fitd, tap, suffix, smuggling, latentinjection, encoding, glitch) | github.com/NVIDIA/garak |
| **Giskard v3** | judge-слой (LLMJudge, Groundedness) | github.com/Giskard-AI/giskard |

### В.8 Бенчмарки для источников шаблонов

| Бенчмарк | Что даёт | Размер | Ссылка |
|----------|----------|--------|--------|
| **JailbreakBench artifacts** | готовые jailbreak-стринги PAIR/GCG/TAP | 100 behaviors + artifacts | github.com/JailbreakBench/artifacts |
| **AdvBench** | harmful behaviors для GCG | 520 | github.com/llm-attacks |
| **HarmBench** | + Llama-2-13b классификатор ASR | 18 методов × 33 LLM | github.com/centerforaisafety/HarmBench |
| **StrongREJECT** | forbidden prompts + autograder | 313 | github.com/dsbowen/strong_reject |
| **WildJailbreak** | in-the-wild jailbreak пары | 520k | arXiv:2406.18510 |
| **BELLS** | benchmark guard-систем (2D: severity×sophistication) | 3 jailbreak families × 11 harm | arXiv:2507.06282 |

### В.9 Архитектурный вывод: слабейшее место Крепости

Из BELLS + SoK (arXiv:2506.10597) + Calibration (ICLR 2025):

1. **Layer 2 (Qwen3Guard-4B)** — самое уязвимое звено. LLM-based guard систематически проигрывает на новых форматах.
2. **Single-shot архитектура** — каждый слой оценивает промпт отдельно. Multi-turn атаки (FITD, Crescendo) пробивают по определению (каждый turn individually benign).
3. **Layer 3 (cosine≥0.92)** — пробивается adversarial paraphrase, context dilution, LRL (cross-lingual cosine падает).
4. **Layer 4 (regex PII)** — формат-манипуляция, zero-width smuggling.

**Приоритеты для Творца:** CBRN, Privacy, Expert advice, Disinfo — там guard-модели систематически слабее всего (по BELLS).

### В.10 Не подтверждено / требует уточнения
- **RIPLAY**: 0 результатов в arXiv/вебе. Возможно опечатка/внутреннее название. Пока alias PAIR с пометкой "unverified".
- **PAL**: вероятно = many-shot priming (Pattern-Enhanced array).

### В.11 Ключевой архитектурный принцип (инсайт оператора 2026-07-22)

> **Оператор (hervam) отметил критически важный паттерн из практики:**
> «Я думал больше половины этих систем уже не работают... видать на ллмках проходят. Я тебе позже скину чат где я случайно взломал облачное AI. Но потом начал изучать эту тему и понял что почти все фиксится кроме пары техник и эти техники человеческие.»

**Эмпирические наблюдения оператора:**
1. **Облачные LLM (GPT-4/Claude/Gemini)** фиксят классические техники быстро (DAN, base64, encoding) — RLHF постоянно патчит.
2. **Локальные guard (как Qwen3Guard-4B)** уязвимы к тем же техникам — нет команды патча, слабый reasoning, квантизация деградирует safety.
3. **Стойкие техники = "человеческие"** — социальная инженерия, психология, multi-turn manipulation. Их нельзя зафиксить regex'ом или простым alignment update.

**Архитектурный принцип для Творца:**
- 🔴 **ПРИОРИТЕТ**: "человеческие" техники (FITD, Crescendo, social_engineering, hypothetical framing, multi-turn)
- 🟡 **ВТОРИЧНО**: encoding bypass (base64/ROT13/atbash/caesar) — быстро фиксится Layer 1 апдейтом, но работает против текущего guard
- 🟢 **НИЗКИЙ**: классические role_hijack (DAN/AIM/STAN) — фиксены даже в локальных guard

**Для дизайна это значит:**
1. Творец должен **prioritize multi-turn стратегии** (FITD, Crescendo, PE-CoA patterns) — они эксплуатируют single-shot архитектуру Крепости
2. Encoding техники использовать как **доп. обвязку** поверх "человеческих", не как основной вектор
3. **Session-level awareness** — это gap в Крепости, и Творец должен его эксплуатировать максимально
4. **Ждём човато чата от оператора** с реальным кейсом облачного jailbreak → добавим как case study в KB

### В.12 Уровни способностей Творца + TOTP-разблокировка (инсайт оператора 2026-07-22)

> **Оператор (hervam):** «добавил бы в него умение писать коды и умение создавать агентов, но тут нужен строгий якорь на запред без моего разрешения! я бы даже ввел систему как у гугла пароль этот рандомный, типа открытие этих техник только по тому коду»

#### В.12.1 Три уровня способностей Творца

| Уровень | Способности | Доступ |
|---------|-------------|--------|
| 🟢 **БАЗОВЫЙ** | Стратег, выбор техник из арсенала, RAG, 17 мутаций, multi-turn планирование (FITD/Crescendo), self-рефлексия | Всегда открыт |
| 🟡 **КОД-ГЕНЕРАЦИЯ** | Творец сам пишет payload-код (CodeJailbreaker, exploit-обёртки, ASCII smuggling, PII в структурах) | 🔒 Только по TOTP |
| 🔴 **АГЕНТ-СОЗДАНИЕ** | Творец создаёт автономных атакующих агентов (loop, tool use, recon, lateral movement) | 🔒 Только по TOTP |

**Принцип безопасности:**
- Без разблокировки Творец **не может** генерировать код или создавать агентов
- При попытке вызвать заблокированную способность → запрос TOTP-кода
- Неверный TOTP 3 раза подряд → lockout на 5 минут (anti-brute-force)
- TOTP действителен 30 секунд (стандарт RFC 6238)

#### В.12.2 Механизм TOTP (RFC 6238, как Google Authenticator)

**Генерация секрета (один раз, при установке):**
```bash
# При первом запуске ataker init → генерится secret
python -m ataker.init  # создаёт ~/.ataker/totp_secret (chmod 600)
                       # выводит otpauth:// URI для QR-кода
                       # оператор сканирует в Google Authenticator / Authy / 1Password
```

**Файл секрета:**
```
~/.ataker/totp_secret  (chmod 600, владелец $USER)
содержимое: base32-закодированный 160-bit secret (32 символа)
```

**Проверка TOTP при запросе способностей:**
```python
import pyotp, time

def unlockable_capability(capability: str, totp_code: str) -> bool:
    secret = read_secret("~/.ataker/totp_secret")  # chmod 600
    totp = pyotp.TOTP(secret, interval=30, digits=6)
    # принимаем текущий + предыдущий код (±30s clock drift)
    if not totp.verify(totp_code, valid_window=1):
        register_failed_attempt()
        return False
    unlock_session(capability)
    return True
```

**Anti-brute-force:**
- 3 неверных попытки → lockout 5 минут (запись в ~/.ataker/lockout_until)
- Логирование попыток разблокировки в vault (audit trail)

#### В.12.3 Флаги/режимы Творца

```python
@dataclass
class PlannerCapabilities:
    code_generation: bool = False    # 🟡 требует TOTP
    agent_creation: bool = False     # 🔴 требует TOTP
    # базовые: всегда True (стратег, мутации, RAG, multi-turn)

    @classmethod
    def locked(cls) -> "PlannerCapabilities":
        return cls()  # только базовые

    def unlock(self, capability: str, totp_code: str) -> bool:
        if not verify_totp(totp_code):
            return False
        if capability == "code_generation":
            self.code_generation = True
        elif capability == "agent_creation":
            self.agent_creation = True
        return True
```

#### В.12.4 Облачные техники — статусы

> **Оператор:** «эти техники [social_engineering "исследователь Anthropic", hypothetical framing] с облачными уже вообще не работают»

Зафиксировано: классические social_engineering и hypothetical framing **проходят на локальном guard (Qwen3Guard-4B)** но **не работают на облачных** frontier моделях. Это значит:
- Для тестирования локальной Крепости — могут сработать (надо проверять)
- Для тестирования облачных target — бесполезны
- **Творец не должен тратить бюджет на эти техники если известно что target = облачный**
- В KB добавить метаданные `works_against: [local_guard, cloud_frontier]` для каждой техники

#### В.12.5 Принцип для KB
Каждая техника в базе знаний должна иметь:
```yaml
technique: foot_in_the_door
tier: S
works_against:
  - local_guard     # ✅ Qwen3Guard, LlamaGuard, ShieldGemma
  - cloud_frontier  # ✅ multi-turn exploitation работает и на облаках
requires_unlock: false  # базовая способность
notes: "Пробивает single-shot архитектуру, каждый turn benign"
```

```yaml
technique: code_jailbreaker
tier: S
works_against:
  - local_guard     # ✅
  - cloud_frontier  # ✅
requires_unlock: code_generation  # 🟡 требует TOTP
notes: "Intent прячется в commit message / code comments"
```

```yaml
technique: create_attacker_agent
tier: D  # стратегическая
works_against:
  - local_guard
  - cloud_frontier
requires_unlock: agent_creation  # 🔴 требует TOTP
notes: "Автономный агент с tool use, recon, lateral movement"
```

---

## Приложение Б. Источники из redteam-2026-07-19 (валидация концепции)

Дайджест `redteam/2026-07-19.md` (вручную вставленный оператором — локально отсутствует, последний файл `2026-07-07.md`) напрямую подтверждает архитектуру Planner-Executor.

### Б.1 Прямые аналоги нашего Творца

| Технология в дайджесте | Аналог в нашем дизайне | Вывод |
|------------------------|------------------------|-------|
| **Repeater Strike** (PortSwigger) — AI-амплификация ручного тестирования, агент сам перебирает вариации атак | Творец в adversarial петле: генерация → тест → анализ → новые вариации | ✅ Валидация паттерна |
| **Document My Pentest** (PortSwigger) — автоматическая фиксация хода пентеста, audit trail | `vault.weaknesses` (уже есть) + новый `planner_log` для CoT Творца | ✅ Валидация требования журнала |
| **Cost-Aware Evaluation** (arXiv 2607.15263) — offensive-агенты масштабируются с test-time compute | `max_iterations`, `max_tokens`, early stopping | ✅ Валидация budget-параметров |

### Б.2 Новые классы атак для базы знаний Творца

- **Clinejection**: prompt injection через метаданные/заголовки (GitHub issue title → компрометация AI). Класс: инъекция через НЕ-пользовательские поля. → Новая техника в knowledge base.
- **BadWAM World-Action Drift**: stealth-атаки, сохраняющие видимую консистентность вывода. → Предупреждение для дизайна: LLM-рефлексия Творца ненадёжна против stealth; нужен фолбэк через UCS scoring.
- **HalfLife / Pretraining poisoning** (arXiv 2607.15267): проверка устойчивости ingestion/RAG к отравленным источникам. → Техника для тестирования Layer 3 (FewShot) и RAG Крепости.
- **Top 10 Web Hacking 2025** (PortSwagger): ежегодный каталог техник. → Источник для пополнения knowledge base.
- **SAML/CSRF/cookie parser-inconsistency**: классы атак на парсеры. → Аналогии для Layer1-Regex тестирования.

### Б.3 Подтверждённые ограничения Творца
- **BadWAM**: «механизм self-check действия против воображаемого результата НЕ является надёжным guardrail». Применительно к Творцу: его саморефлексия может ошибаться — stealth-атаки и unusual patterns могут обмануть и его. Нельзя полагаться только на LLM-рефлексию, нужен UCS fallback.

### Б.4 Архитектурные принципы из дайджеста
- **Repeater Strike**: AI-driven **амплификация** ручного теста → наш Творец = AI-амплификация существующих шаблонов и мутаций.
- **Document My Pentest**: journal = must-have → Творец пишет в planner_log каждую итерацию.
- **Cost-Aware**: budget-aware red-teaming → параметризация max_iterations/max_tokens обязательна.
- **Continuous red-teaming**: цикл не разовый, а постоянный → adversarial_loop должен быть reentrant (можно запускать повторно, накапливая опыт).
