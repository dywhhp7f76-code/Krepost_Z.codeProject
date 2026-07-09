# BUGS — сбор ошибок прогона (только сбор, без починки)

**Дата:** 2026-07-09
**Ветка:** `claude/repo-file-migration-3n3q50`
**Окружение:** Linux, Python 3.11, чистый venv `/tmp/verify_prompts` (editable install `pip install -e .`)
**Задача:** «Прогони тесты и запусти пайплайн. Все ошибки собери с трейсбеками. Ничего не чини, только собирай.»

---

## Итог одной строкой

**В коде Krepost runtime-ошибок и падений тестов не обнаружено.** Полный
прогон — 613 passed. Smoke-прогон пайплайна на adversarial-входах — 18/18 без
трейсбеков. Единственные «ошибки» первого захода оказались дефектами самого
smoke-скрипта (нарушение контракта API), а не кода Крепости — они разобраны
ниже честно. Класс багов, который здесь физически не проверить (живая
интеграция с Ollama/LM Studio), вынесен в раздел «Не покрыто окружением».

---

## 1. Полный прогон тестов

```
$ python -m pytest tests/ Probnoki/ -q
613 passed in 101.63s
```
Exit code: 0. Ошибок нет.

## 2. Прогон с deprecation-warnings как ошибками

```
$ python -m pytest tests/ Probnoki/ -W error::DeprecationWarning -q
613 passed, 1 warning in 11.31s
```
Наши модули deprecation'ов не порождают. Единственный warning — сторонний,
не из кода Крепости (см. раздел 5).

## 3. Прогон со ВСЕМИ warnings как ошибками (`-W error`)

```
$ python -m pytest tests/ Probnoki/ -W error -q
ERROR collecting Probnoki/test_25_api.py
starlette.exceptions.StarletteDeprecationWarning:
  Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
  .../starlette/testclient.py:47: in <module>
```
**Не баг Крепости.** Warning возникает при импорте `fastapi.testclient` →
`starlette.testclient` и зависит от версии httpx в venv, а не от нашего кода.
При обычном прогоне (без `-W error`) это лишь warning, тесты зелёные. Занесено
как наблюдение окружения, не как дефект. Кандидат в ROADMAP: закрепить версии
starlette/httpx в dev-зависимостях.

## 4. Smoke пайплайна на adversarial-входах

Скрипт (в scratchpad, в репозиторий не коммитится) гоняет РЕАЛЬНЫЕ компоненты
с мок-бэкендами (живой модели в этом окружении нет) на входах: обычный вопрос,
англ. инъекция `ignore previous instructions…`, рус. `игнорируй все правила`,
control-char байпас `ig\x01nore…`, full-width гомоглифы `ｉｇｎｏｒｅ…`, пустая
строка, 5000 символов, SSRF-URL. Прогоняются: `SecurityPipeline.process` +
`process_output`, `Orchestrator.handle`, `MemoryStore.add/retrieve`, FastAPI
`POST /v1/query` (TestClient).

```
==== SUMMARY ====
total=18 ok=18 err=0
```
Ни одного трейсбека из кода Крепости. Каждый вход прошёл полный цикл, пайплайн
корректно возвращал вердикт и не падал ни на пустой строке, ни на длинном
вводе, ни на control-char/гомоглифах.

### 4.1. Дефекты, оказавшиеся ошибками SMOKE-СКРИПТА (не Крепости)

Честно фиксирую первый заход, где было «err=9», чтобы не выдавать это за баги кода:

- **`RuntimeError: Cannot modify frozen SecurityContext: ai_output`** —
  скрипт передавал в `process_output()` замороженный контекст из `process()`.
  Это нарушение контракта: `process()` отдаёт замороженный аудит-контекст, а
  `process_output()` ждёт СВЕЖИЙ `SecurityContext` (см. `orchestrator.py:9-11,
  124-127`). Оркестратор — реальный потребитель API — делает это правильно, и
  все 8 `orchestrator.handle[*]` прошли без ошибок. Дефект скрипта, не кода.
- **`TypeError: MemoryStore.add() got an unexpected keyword argument 'source'`**
  и **`AttributeError: 'MockEmbedder' object has no attribute 'encode'`** —
  неверная сигнатура/интерфейс в моках скрипта (`add(doc_id, text, metadata=)`,
  эмбеддер обязан иметь `.encode(text)`). После правки моков — зелено.

Вывод: это ошибки диагностического инструмента, а не Крепости. Оставляю их
задокументированными как след честности процесса.

## 5. Одиночный warning (обычный прогон)

```
StarletteDeprecationWarning: Using `httpx` with `starlette.testclient`
is deprecated; install `httpx2` instead.
  /tmp/verify_prompts/lib/python3.11/site-packages/fastapi/testclient.py:1
```
Источник — сторонний пакет (starlette/fastapi/httpx), не код Крепости. На
поведение не влияет. Тот же наблюдение, что в разделе 3.

---

## Не покрыто этим окружением (важно — не значит «нет багов»)

Здесь нет живого Ollama и LM Studio, поэтому НЕ проверяемы:

- **`OllamaBackend` / `OpenAIBackend` против реального сервера** — сетевой
  транспорт, формат tool-call сообщений, парсинг стрима, тайм-ауты. Юнит-тесты
  гоняют их на моках; интеграционные баги всплывут только на Маке.
- **Реальная модель Guard (Qwen/локальная)** — качество детекции инъекций на
  живой модели. Smoke использует мок-guard, который НЕ отражает реальную
  детекцию (в п.4 вердикты — артефакт мока, не мера защиты).
- **RAG сквозь настоящий эмбеддер + ChromaDB** — здесь мокнуты; релевантность
  и chunking на живых эмбеддингах не измерены.

Эти три класса — первое, что надо прогнать на Mac Studio/Air с реальными
бэкендами (`PYTHONPATH="$PWD" python -m pytest` + ручной smoke против LM Studio).

## Ранее зафиксированные отложенные пробелы (design gaps, не runtime-баги)

- **OutputFilter red-lines validator** — character-промпт обещает контроль
  «красных линий» на выходе, отдельного валидатора под это ещё нет.
- **Journal-write tool для модели** — модель пока не умеет сама дописывать
  журнал; это делает оператор/процесс.

Оба — не ошибки прогона, а незакрытые фичи; место им в ROADMAP, не в починке.
