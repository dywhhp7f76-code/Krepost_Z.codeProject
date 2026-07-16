#!/usr/bin/env python3
"""Создать дерево vault/ с README в каждой leaf-папке и 00-INDEX.md."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "vault"

# (path, one-liner для README)
LEAVES: list[tuple[str, str]] = [
    ("00-System/Archive", "Архив системных артефактов и устаревших конфигов."),
    ("00-System/Copilot", "Заметки и промпты для coding-ассистентов."),
    ("00-System/Logs", "Экспорт системных логов и диагностики."),
    ("00-System/Models", "Карточки моделей, квантизации и профилей инференса."),
    ("00-System/Prompts", "Системные и инженерные промпты Крепости."),
    ("00-System/Scripts", "Вспомогательные скрипты обслуживания vault."),
    ("00-System/Templates", "Шаблоны заметок и документов."),
    ("01-Energy/Other_Sources", "Альтернативные и резервные источники энергии."),
    ("01-Energy/Solar", "Солнечная генерация и балансировка."),
    ("01-Energy/Storage", "Аккумуляторы, BESS и стратегии хранения."),
    ("01-Energy/Water", "Гидро и водные источники энергии."),
    ("01-Energy/Wind", "Ветровая генерация и профили нагрузки."),
    ("02_Weapons_Defense/Chemical", "Химическая защита и контрмеры."),
    ("02_Weapons_Defense/Energy_Based", "Энергетические системы поражения и ПВО."),
    ("02_Weapons_Defense/Mechanical", "Механические средства и тактика применения."),
    ("02_Weapons_Defense/Tactics", "Тактика, доктрины и сценарии обороны."),
    ("03-Programming_Hacking/AI_Hacking", "Атаки и защита LLM/агентных систем."),
    ("03-Programming_Hacking/Exploitation", "Эксплуатация уязвимостей и PoC."),
    ("03-Programming_Hacking/Languages", "Языки, рантаймы и идиомы кода."),
    ("03-Programming_Hacking/Security", "AppSec, hardening и threat modeling."),
    ("03-Programming_Hacking/Tools", "Инструменты разработки и пентеста."),
    ("04-Philosophy_AI/Alignment_Truth", "Alignment, истина и epistemics ИИ."),
    ("04-Philosophy_AI/Consciousness", "Сознание, qualia и когнитивные модели."),
    ("04-Philosophy_AI/Ethics_Control", "Этика, контроль и governance ИИ."),
    ("04-Philosophy_AI/Future_Scenarios", "Сценарии будущего с сильным ИИ."),
    ("05_Knowledge_Base/Books_Extracts", "Выдержки из книг и конспекты."),
    ("05_Knowledge_Base/Diagrams", "Схемы, mind-map и визуальные модели."),
    ("05_Knowledge_Base/References", "Справочники, стандарты и ссылки."),
    ("05-Archive", "Холодный архив заметок вне активного RAG."),
    ("06-Research/Papers", "Научные статьи и preprint-конспекты."),
    ("06-Research/Notes", "Исследовательские заметки и гипотезы."),
    ("07-Krepost_Architecture/01_Core", "Ядро архитектуры Крепости и инварианты."),
    ("07-Krepost_Architecture/02_Security", "Security pipeline, guard и threat model."),
    ("07-Krepost_Architecture/03_Prompts", "Промпты и политики основной модели."),
    ("07-Krepost_Architecture/04_Logs", "Архитектурные логи и postmortem."),
    ("07-Krepost_Architecture/05_Future", "Roadmap и экспериментальные идеи."),
    ("07-Krepost_Architecture/10-Krepost_na_iPhone", "Мобильный контур и iPhone-вариант."),
    ("07-Krepost_Architecture/11-qwer_Ai", "Экспериментальный контур qwer_Ai."),
    ("07-promts", "Черновики промптов вне основного реестра."),
    ("08-Logs", "Операционные логи сессий и API."),
    ("09-Inbox", "Входящие заметки до сортировки по PARA."),
    ("10-Projects/Active", "Активные проекты и рабочие пакеты."),
    ("10-Projects/Archive", "Завершённые проекты."),
    ("12-Konechny_rezultat_promta", "Финальные артеfact'ы промпт-экспериментов."),
    ("13-other", "Прочие материалы без жёсткой классификации."),
    ("14_grok", "Материалы и эксперименты с Grok."),
    ("99-Templates", "Obsidian-шаблоны для новых заметок."),
    ("Knowledge_chistaya_baza_znaniy", "Чистая база знаний без производных правок."),
]

INDEX = """# Krepost Vault — индекс

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
"""


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    for rel, blurb in LEAVES:
        d = ROOT / rel
        d.mkdir(parents=True, exist_ok=True)
        readme = d / "README.md"
        if not readme.exists():
            readme.write_text(f"# {d.name}\n\n{blurb}\n", encoding="utf-8")

    smoke = ROOT / "07-Krepost_Architecture/01_Core/RAG_SMOKE_TEST.md"
    if not smoke.exists():
        smoke.write_text(
            "# RAG smoke test\n\n"
            "Уникальный идентификатор для e2e-проверки retrieval: **KREPOST-RAG-7742**.\n"
            "Если модель отвечает этим кодом на вопрос «какой smoke-код Крепости?», "
            "RAG на Studio работает.\n",
            encoding="utf-8",
        )

    index_path = ROOT / "00-INDEX.md"
    index_path.write_text(INDEX, encoding="utf-8")
    print(f"vault ready: {len(LEAVES)} leaves under {ROOT}")


if __name__ == "__main__":
    main()
