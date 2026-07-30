# AGENTS.md

## Cursor Cloud specific instructions

Krepost — 4-слойный AI security pipeline (Python 3.12): библиотека + demo HTTP API, плюс
модули памяти/RAG (`krepost/memory`) и вспомогательные скрипты (`scripts/`,
`serve_lmstudio.py`, `ingest_vault.py`, `smoke_lmstudio.py`, требуют внешний LLM-сервер).
Стандартные команды — в `README.md` (разделы «Быстрый старт» и «Тесты»); ниже только
неочевидные для облачного окружения детали.

### Окружение
- Зависимости ставятся в изолированный `./.venv` (его создаёт update-скрипт). Пакет
  называется `krepost` — так же, как во втором репозитории воркспейса (`Krepost-V3`),
  поэтому **общий venv невозможен**: у каждого репозитория свой.
- Установка тянет `torch` (транзитивно через `sentence-transformers`) — первый прогон
  долгий и объёмный; повторные быстрые. BM25 и reranker свои, доп. пакетов не требуют
  (CrossEncoder — ленивый импорт из `sentence-transformers`).
- Запускайте инструменты как `.venv/bin/python` / `.venv/bin/pytest` (либо
  `source .venv/bin/activate`).

### Тесты
- `.venv/bin/pytest` — 201 тест, проходят без моделей и сети (guard/embedder мокаются).

### Запуск demo API
- `.venv/bin/python -m krepost.api.server` — FastAPI на `127.0.0.1:8000`
  (порт/хост переопределяются `KREPOST_API_PORT` / `KREPOST_API_HOST`).
- Это **modelless-демо** (`EchoBackend` + dev-guard): реальные LLM/модели не нужны.
  Swagger UI — `/docs`, health — `/health`, метрики — `/metrics`.
- **Известный баг demo-сервера (не окружение):** в `krepost/api/server.py` заглушка
  `_DevAllowGuard.chat()` не принимает kwarg `options`, который передаёт
  `SecurityPipeline._call_guard` (`options={"temperature": 0}`). Из-за этого benign-запрос
  через demo API fail-closed на `Layer2-Guard` (`RED / unexpected_error_fail_closed`).
  Блокировка инъекций на `Layer1-Regex` работает штатно. Сама библиотека исправна:
  GREEN-путь воспроизводится, если у guard-клиента сигнатура
  `chat(..., options=None)` (проверено). Правьте `server.py`, только если задача — фикс кода.
- В воркспейсе есть второй сервис (`Krepost-V3`); чтобы поднять оба сразу, задайте разные
  порты через `KREPOST_API_PORT`.
