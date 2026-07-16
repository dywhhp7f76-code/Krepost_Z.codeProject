# Krepost Vault — индекс

> Дом долговременной памяти на Mac Studio. Источник истины для RAG (BGE-M3 + Chroma cosine).

## Дерево

| Раздел | Назначение |
|--------|------------|
| `00-System/` | Система, модели, промпты, скрипты |
| `01-Energy/` | Энергетика и автономность |
| `02_Weapons_Defense/` | Оборона и тактика |
| `03-Programming_Hacking/` | Код, безопасность, инструменты |
| `04-Philosophy_AI/` | Философия и governance ИИ |
| `05_Knowledge_Base/` | Книги, схемы, справочники |
| `05-Archive/` | Холодный архив |
| `06-Research/` | Статьи и исследовательские заметки |
| `07-Krepost_Architecture/` | Архитектура Крепости |
| `07-promts/` | Черновики промптов |
| `08-Logs/` | Операционные логи |
| `09-Inbox/` | Входящие до сортировки |
| `10-Projects/` | Активные и архивные проекты |
| `12-Konechny_rezultat_promta/` | Итоги промпт-прогонов |
| `13-other/` | Прочее |
| `14_grok/` | Grok-материалы |
| `99-Templates/` | Шаблоны заметок |
| `Knowledge_chistaya_baza_znaniy/` | Чистая база знаний |

## Ingest

```bash
python ingest_vault.py              # полная индексация vault/
python ingest_vault.py --dry-run  # только список файлов
```

## RAG smoke

См. `07-Krepost_Architecture/01_Core/RAG_SMOKE_TEST.md` — уникальный код **KREPOST-RAG-7742** для e2e-проверки retrieval.
