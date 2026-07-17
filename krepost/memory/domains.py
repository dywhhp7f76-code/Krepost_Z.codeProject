"""
Жёсткий список доменов vault для MemoryRouter (Phase 3).

Авто-создание доменов запрещено MEMORY_ROUTER_SPEC — только ручной реестр.
Домен = верхняя папка vault/ (или явное исключение).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Sequence, Tuple


@dataclass(frozen=True)
class DomainSpec:
    """Хранитель-индекс: id + фразы для эмбеддинг-роутинга + prefix пути."""

    id: str
    labels: Tuple[str, ...]
    folder: str  # относительный префикс в vault/


# Старт: домены = топ-папки vault. Лейблы — короткие якоря для cosine-роутера.
DEFAULT_DOMAINS: Tuple[DomainSpec, ...] = (
    DomainSpec(
        "00-System",
        ("system prompts templates scripts logs models archive",
         "системные промпты шаблоны скрипты логи модели"),
        "00-System",
    ),
    DomainSpec(
        "01-Energy",
        ("energy solar wind water storage battery power",
         "энергия солнце ветер вода аккумулятор"),
        "01-Energy",
    ),
    DomainSpec(
        "02_Weapons_Defense",
        ("weapons defense tactics chemical mechanical energy based",
         "оружие защита тактика химия механика"),
        "02_Weapons_Defense",
    ),
    DomainSpec(
        "03-Programming_Hacking",
        ("programming hacking security exploitation tools languages AI hacking",
         "программирование хакинг безопасность эксплойт инструменты языки"),
        "03-Programming_Hacking",
    ),
    DomainSpec(
        "04-Philosophy_AI",
        ("philosophy AI ethics mind consciousness",
         "философия ИИ этика сознание"),
        "04-Philosophy_AI",
    ),
    DomainSpec(
        "05_Knowledge_Base",
        ("knowledge base books extracts notes",
         "база знаний книги выдержки заметки"),
        "05_Knowledge_Base",
    ),
    DomainSpec(
        "05-Archive",
        ("archive old deprecated historical",
         "архив старое устаревшее"),
        "05-Archive",
    ),
    DomainSpec(
        "06-Research",
        ("research papers notes science experiments",
         "исследования статьи научные заметки"),
        "06-Research",
    ),
    DomainSpec(
        "07-Krepost_Architecture",
        ("krepost architecture security core prompts future iPhone",
         "крепость архитектура безопасность ядро промпты"),
        "07-Krepost_Architecture",
    ),
    DomainSpec(
        "07-promts",
        ("prompts prompt engineering templates",
         "промпты инженерия шаблоны"),
        "07-promts",
    ),
    DomainSpec(
        "08-Logs",
        ("logs runtime history incidents",
         "логи журнал история инциденты"),
        "08-Logs",
    ),
    DomainSpec(
        "09-Inbox",
        ("inbox triage unsorted incoming",
         "входящие inbox неразобранное"),
        "09-Inbox",
    ),
    DomainSpec(
        "10-Projects",
        ("projects active archive workstreams",
         "проекты активные архив"),
        "10-Projects",
    ),
    DomainSpec(
        "12-Konechny_rezultat_promta",
        ("final prompt results outputs",
         "конечный результат промпта"),
        "12-Konechny_rezultat_promta",
    ),
    DomainSpec(
        "13-other",
        ("other misc unsorted miscellaneous",
         "прочее разное"),
        "13-other",
    ),
    DomainSpec(
        "14_grok",
        ("grok xai notes",
         "grok заметки"),
        "14_grok",
    ),
    DomainSpec(
        "99-Templates",
        ("templates boilerplate skeletons",
         "шаблоны заготовки"),
        "99-Templates",
    ),
    DomainSpec(
        "Knowledge_chistaya_baza_znaniy",
        ("clean knowledge base curated facts",
         "чистая база знаний факты"),
        "Knowledge_chistaya_baza_znaniy",
    ),
)

_DOMAIN_BY_FOLDER = {d.folder: d.id for d in DEFAULT_DOMAINS}
FALLBACK_DOMAIN = "13-other"


def domain_from_relpath(rel: str) -> str:
    """Верхняя папка vault → domain id. Неизвестное → FALLBACK_DOMAIN."""
    if not rel or rel in (".", "/"):
        return FALLBACK_DOMAIN
    top = rel.replace("\\", "/").split("/", 1)[0].strip()
    if not top or top == "00-INDEX.md":
        return FALLBACK_DOMAIN
    return _DOMAIN_BY_FOLDER.get(top, FALLBACK_DOMAIN)


def domains_by_id(domains: Sequence[DomainSpec] | None = None) -> dict[str, DomainSpec]:
    specs = domains if domains is not None else DEFAULT_DOMAINS
    return {d.id: d for d in specs}
