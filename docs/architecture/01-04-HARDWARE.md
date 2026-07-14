# Железо и распределение

Спецификации hardware и распределение ресурсов. Архитектура КРЕПОСТЬ рассчитана на работу целиком на локальном железе без зависимости от облачных GPU.

> **Обновлено:** 2026-07-15 — железо на месте (Mac Studio + MacBook Air).

## Основные вычислительные узлы

### Mac Studio M4 Max — 64 GB RAM / 1 TB SSD

Основной боевой сервер. Production-задачи:
- **AI-инференс:** Qwen3.6-35B-A3B (MoE, Q4) — основная генеративная модель
- **Guard:** Qwen3Guard-Gen-4B — классификация запросов (Layer 2)
- **Эмбеддинги:** BGE-M3 / nomic-embed-text v1.5 — векторный поиск
- **RAG-пайплайн:** ChromaDB + гибридный поиск

64 GB unified memory: MoE 35B-A3B активирует не все эксперты — на Studio это основной «мозг»; плотнее и умнее dense 27B при сопоставимом RAM-бюджете.

### MacBook Air M5 — 32 GB RAM / 1 TB SSD

Грязная зона (adversarial training, Камень 1):
- **Attacker:** uncensored local LLM (кандидат: `dolphin3-cyber-8b`) — генерация adversarial-промптов для Ataker-boop
- LM Studio / Ollama smoke, seed-корпус против guard
- **Не** крутит боевой main и **не** хранит production RAG

32 GB достаточно для guard smoke + attacker 7–8B Q4 и тренировочных скриптов.

## Хранилище

### WD Black SN850X 2 TB — корпус Thunderbolt 5 (~80 Gbps)

Съёмный быстрый SSD:
- Тренировочные данные, adversarial-примеры, seed-корпус (local JSONL)
- Разметка, метаданные red-team
- Отключение диска = Studio стерилен (нет ядов на боевом узле)

### HDD 4 TB (ускоренный)

Архивное хранилище:
- Бэкапы, полные audit-логи (audit_hash + trace_hash)
- Cold storage вектор-индексов, снапшоты

> Ранее в доках фигурировал 6 TB — фактически **4 TB**.

## Периферия

### UGREEN Revodok Max — Thunderbolt 5, 13-in-1

Док-станция (до 120 Gbps unidirectional / 80 Gbps bidirectional):
- Питание, мониторы (до quad-screen), downstream TB5/USB
- Центральный хаб: Mac Studio ↔ SN850X ↔ HDD ↔ периферия
- **6× кабелей Thunderbolt 40 Gbps** в комплекте

### Прочее

- Мелкая периферия (адаптеры, клавиатуры и т.д.)
- **Мышь:** ⏳ в пути (предыдущая потеряна)

## Мониторинг (без изменений)

### iPad Air M4 256 GB — дашборд мониторинга

### iPhone Air 256 GB — Pushover / Telegram алерты

## Модели и распределение

| Модель | Назначение | Узел | Примечание |
|--------|-----------|------|------------|
| Qwen3.6-35B-A3B (MoE, Q4) | Основная генерация | Mac Studio | Выбор оператора 2026-07 |
| Qwen3Guard-Gen-4B | Guard / безопасность | Studio (+ Air smoke) | LM Studio id: `qwen3guard-gen-4b` |
| BGE-M3 / nomic-embed | Эмбеддинги | Mac Studio | RAG |
| dolphin3-cyber-8b (канд.) | Adversarial attacker | MacBook Air | Uncensored, red-team only |
| llama-3.2-1b-instruct | Smoke / draft | MacBook Air | LM Studio smoke ok |
| FLUX.1 | Генерация изображений | Mac Studio | planned |
