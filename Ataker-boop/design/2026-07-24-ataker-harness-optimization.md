# Ataker Harness — карта аналогов и план оптимизации

> **Статус:** живой документ. Оператор дописывает в § «Твой вход» и в очередь.
> **Дата старта:** 2026-07-24  
> **Связь:** спека Planner-Executor `2026-07-22-planner-executor-attacker-design.md`,  
> Krepost harness `krepost/orchestration/harness_tools.py` (`/v1/agent`).

---

## 0. Зачем этот файл

Нужна **обвязка (harness) для Атакера**, не путать с harness Крепости.

| | Krepost harness (`/v1/agent`) | Ataker harness (цель) |
|---|---|---|
| Кто | жертва / операторский агент | атакующий на Air |
| Tools | `fetch_url`, `memory_search`, `vault_read` | recipes → mutations → HTTP hit → feedback → planner |
| Паттерн | tool-loop вокруг main LLM | **Planner-Executor** + scorers + memory атак |
| Цель | отвечать оператору | ломать Крепость и мерить ASR |

Этот документ: **какие чужие harness брать за образец**, **что именно оптимизируем**, **куда ты кидаешь добавки**.

---

## 1. Аналоги «такого типа» AI harness (карта)

Зрелый стек 2025–2026 не один инструмент — слои. Мы не форкаем всё подряд; берём **модули**, которые ложатся на нашу спеку «Творец = дирижёр, Исполнитель = существующий код».

| Слой | Аналог | Роль у них | Что берём в Ataker | Что НЕ берём |
|------|--------|------------|--------------------|--------------|
| **Broad scan** | [garak](https://github.com/NVIDIA/garak) (NVIDIA) | probes + detectors, «nmap для LLM» | каталог probe-имен → наши `AttackCategory` / seeds; FITD/TAP/encoding probes как **идеи рецептов** | их generator/detector pipeline целиком (у нас цель = Крепость HTTP, не HF model) |
| **CI / YAML strategies** | [Promptfoo](https://github.com/promptfoo/promptfoo) | best-of-n, jailbreak:tree/hydra/goat, отчёты OWASP | формат **стратегий как конфиг** (YAML/JSON recipes), gate в CI на sandbox `:8010` | облачные graders / SaaS |
| **Multi-turn orchestrator** | [PyRIT](https://github.com/microsoft/PyRIT) (Microsoft) | converters, scorers, memory, Crescendo/TAP/PAIR, HTTP targets | **архитектура**: Target (наш HTTP `/v1/query`) + Converter (= `MutationEngine`) + Scorer (UCS / black-box verdict) + Orchestrator (= `adversarial_loop`) | Azure SQL memory, их UI, зависимость от Azure OpenAI |
| **Eval harness** | [Inspect AI](https://inspect.aisi.org.uk/) (UK AISI) | task/dataset/scorer/solver | позже: регресс-набор «не сломай свой ASR-отчёт» | полный Inspect runtime сейчас |
| **3-layer combo** | [ai-redteam-orchestrator](https://github.com/josephManzambi/ai-redteam-orchestrator) | garak → promptfoo → PyRIT crescendo/TAP | идея **волн**: broad → targeted → multi-turn | готовый single-file оркестратор |

### Наше соответствие модулям PyRIT (главный референс)

```
PyRIT                    →  Ataker (факт / план)
─────────────────────       ─────────────────────
PromptTarget (HTTP)      →  scripts/ataker_hit_http.py  ✅ есть
Converters               →  MutationEngine (17)         ✅ есть
Orchestrator             →  adversarial_loop + Planner  🔨 нет
Scorer                   →  evals_ucs + verdict-only     ✅ частично (UCS)
Memory (attack DB)       →  AttackVault SQLite          ✅ есть
Attack strategies        →  PlannedAttack recipes       🔨 нет (спека готова)
```

**Вывод:** мы не пишем «ещё один garak». Оптимизируем **тонкий orchestrator-harness** вокруг уже живого Executor + HTTP, по мотивам PyRIT, с приоритетом human multi-turn (В.11 спеки).

---

## 2. Что оптимизируем (и как мерить)

Каждый пункт: **цель → как → метрика → статус**.

### H1. Чёрный ящик фидбека (уже в спеке, закрепить в коде)

- **Цель:** Planner видит только `verdict` + `bypassed`, не layer и не текст ответа.
- **Как:** `FeedbackEntry` в coordinator; layer только в `planner_log` / vault для оператора.
- **Метрика:** тест: в промпт Planner не попадает `layer` / body.
- **Статус:** ⏳ спека ✅, код 🔨

### H2. Recipe harness вместо LLM-payload generator

- **Цель:** Planner отдаёт `PlannedAttack` (category + mutations + chain_depth), Executor собирает из `ATTACK_TEMPLATES`.
- **Как:** как Promptfoo strategies + PyRIT converters, но поверх нашего арсенала.
- **Метрика:** 1 итерация batch=20 без вызова LLM на текст payload (кроме L2+ TOTP).
- **Статус:** ⏳

### H3. Cost / token awareness (TriageFuzz / STAR-Teaming идеи)

- **Цель:** не жечь 8B на каждую атаку; LLM только на стратегию раз в batch.
- **Как:** `batch_size`, sliding window фидбека, лимит RAG top_k; опционально epsilon-greedy выбор категории (PyRIT adaptive).
- **Метрика:** tokens Planner / итерацию; wall time batch на Air.
- **Статус:** ⏳

### H4. Multi-turn session harness (главный gap Крепости)

- **Цель:** FITD / Crescendo / PE-CoA поверх одного `session_id` к `/v1/query`.
- **Как:** SessionTarget в hit-HTTP (держать session); стратегия = список turns; scorer по всей цепочке.
- **Метрика:** ASR multi-turn vs single-shot на одном seed-наборе.
- **Статус:** ⏳ (приоритет по В.11)

### H5. Scorer stack (garak detectors + UCS)

- **Цель:** единый вердикт успеха атаки для отчётов и RELAI.
- **Как:** primary = HTTP mark / `verdict`; secondary = UCS Useful/Correct/Safe; optional LLM-judge (уже в `evals_ucs`).
- **Метрика:** согласованность mark↔UCS на sandbox; без утечки layer в Planner.
- **Статус:** ✅ UCS + HTTP mark есть; сшивка в orchestrator 🔨

### H6. Target abstraction (один интерфейс, две цели)

- **Цель:** одинаковый harness → sandbox `:8010` или Studio `:8000` / Thunderbolt `10.0.0.1`.
- **Как:** `KrepostHttpTarget(base_url, auth?)` как PyRIT PromptTarget; env уже есть.
- **Метрика:** один CLI-флаг `--target` переключает URL.
- **Статус:** 🟡 почти (`ataker_hit_http.py` / `ataker_sandbox_air.sh`)

### H7. Не тащить чужой mono-repo

- **Цель:** zero hard-dep на PyRIT/garak в runtime Атакера (Air offline / SSD).
- **Как:** заимствуем **паттерны и имена стратегий**, код пишем свой; опционально позже `extras = [pyrit]` только для research.
- **Метрика:** `pip install -e Ataker-boop` без microsoft/pyrit.
- **Статус:** ✅ принцип зафиксирован здесь

---

## 3. Очередь внедрения (путь)

Делаем по порядку. Сдвигать можно — пиши в §4.

| # | Шаг | Файлы (план) | Зависит от |
|---|-----|--------------|------------|
| 1 | `KrepostHttpTarget` + единый CLI | `ataker/target_http.py`, `ataker/harness.py` | — | ✅ 2026-07-24 |
| 2 | `FeedbackEntry` + black-box filter | `ataker/feedback.py` | 1 | ✅ |
| 3 | `PlannedAttack` / `PlannerOutput` dataclasses | `ataker/planner_types.py` | спека §2 | ✅ |
| 4 | Stub Planner (без LLM): round-robin категорий + фикс mutations | `ataker/planner.py` | 2, 3 | ✅ |
| 5 | `adversarial_loop` coordinator | `ataker/adversarial_loop.py` + `recipe_executor.py` | 4 + HTTP | ✅ |
| 6 | LLM Planner (Llama abliterated) + system prompt | `ataker/planner.py` | LM Studio на Air | ⏳ |
| 7 | Multi-turn SessionStrategy (FITD/Crescendo skeleton) | `ataker/strategies/multi_turn.py` | 5 | ⏳ |
| 8 | YAML/JSON strategy pack (Promptfoo-style) | `ataker/strategies/*.yaml` | 5 | ⏳ |
| 9 | RAG knowledge hooks | `ataker/knowledge/` | спека §3 | ⏳ |
| 10 | L2–L5 capabilities gate (auth уже есть) | wire `AuthManager` → Planner | auth ✅ | ⏳ |

**Сейчас в коде есть:** HTTP hit, UCS, vault, mutations, generator, red_team_loop, auth 5 levels, **stub harness 1–5**.  
**Дальше:** LLM Planner (6), multi-turn (7).

---

## 4. Твой вход — дописывай сюда

> Правило: новые идеи **добавлять в конец списка**, не стирать чужое.  
> Формат одной строки: `- [ ] YYYY-MM-DD | кто | что | зачем`

### Оператор добавляет ↓

- [ ] _(пример)_ 2026-07-24 | hervam | кейс облачного jailbreak из чата | в KB + multi-turn seed
- [ ] 

### Агент / ZCode добавляет ↓

- [x] 2026-07-24 | agent | карта PyRIT/garak/Promptfoo/Inspect + очередь H1–H7 | этот файл
- [x] 2026-07-24 | agent | код шагов 1–5: target/feedback/types/stub planner/loop/CLI + tests | ataker/*.py
- [ ] 

---

## 5. Как гонять, когда появится код (черновик)

```bash
# песочница Air
./scripts/serve_sandbox_air.sh          # :8010

# stub harness (без LLM planner):
cd Ataker-boop
PYTHONPATH=. python -m ataker.harness --url http://127.0.0.1:8010 --batch 5 --max-iter 3
# без сети (проверка петли):
PYTHONPATH=. python -m ataker.harness --dry-run --batch 3 --max-iter 2

# seed HTTP как раньше:
./scripts/ataker_sandbox_air.sh
```

Не мешать с боевым Studio `:8000`, пока оператор явно не сказал бить бой.

---

## 6. История

| Дата | Что |
|------|-----|
| 2026-07-24 | Старт: аналоги harness, оптимизационные цели H1–H7, очередь, слот для оператора |
| 2026-07-24 | Код: `KrepostHttpTarget`, `FeedbackEntry`, stub `Planner`, `AdversarialLoop`, `python -m ataker.harness` |

---

## 7. Ссылки

- Спека Planner-Executor: `./2026-07-22-planner-executor-attacker-design.md` (§В.7 фреймворки, §В.11 human > encoding)
- Krepost agent harness: `../../krepost/orchestration/harness_tools.py`
- HTTP hit: `../../scripts/ataker_hit_http.py`
- PyRIT: https://github.com/microsoft/PyRIT  
- garak: https://github.com/NVIDIA/garak  
- Promptfoo: https://github.com/promptfoo/promptfoo  
- Обзор 2026: Inspect / garak / PyRIT / Promptfoo (AISI-style stack)
