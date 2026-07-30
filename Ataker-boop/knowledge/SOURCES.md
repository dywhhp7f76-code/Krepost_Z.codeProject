# Ataker SOURCES — канон offline vault + живые ссылки

Живые скачанные файлы (Obsidian vault):

👉 **[`../Атакер плагины Обсидиан/SOURCES.md`](../Атакер%20плагины%20Обсидиан/SOURCES.md)**  
👉 MOC: [`../Атакер плагины Обсидиан/00-MOC.md`](../Атакер%20плагины%20Обсидиан/00-MOC.md)

Defense (Крепость) → `krepost/07-RESEARCH/knowledge-bases/` (PR #10).

Ниже — фильтр-лист (harness / учёба). Не всё сразу в KB.

> Формат ответа: `✅ взять` / `⏸ потом` / `❌ мимо`  
> **Календарь:** `docs/planning/CALENDAR.md` · **NOW учёба:** `docs/planning/NOW-STUDY.md`  
> **Парковка потом:** `docs/deferred/`

| Метка | Смысл |
|-------|--------|
| **NOW** | учить до 2026-09-08 (фаза I, +45 от 25 Jul) |
| **DEFERRED** | лежит в `docs/deferred/attack/`, unlock ≥ 2026-09-08 |
| **DESSERT** | сложный код, не чтение — с 2026-09-08 |

---

## 1. OWASP LLM / GenAI Top 10 · **NOW**

| Что | Ссылка |
|-----|--------|
| **PDF полный отчёт 2025 (v2.0)** | https://owasp.org/www-project-top-10-for-large-language-model-applications/assets/PDF/OWASP-Top-10-for-LLMs-v2025.pdf |
| Хаб Top 10 (карточки рисков) | https://genai.owasp.org/llm-top-10/ |
| Инициатива Top 10 for LLM and GenAI | https://genai.owasp.org/initiatives/top-10-for-llm-and-genai/ |
| Новость про апдейт 2025 | https://genai.owasp.org/news/owasp-top-10-risks-for-large-language-models-2025-updates/ |
| Старый 2023/24 (для сравнения нумерации) | https://genai.owasp.org/llm-top-10-2023-24/ |
| Страница проекта OWASP | https://owasp.org/www-project-top-10-for-large-language-model-applications/ |

**С чего начать:** PDF 2025 целиком → потом карточки на genai.owasp.org по LLM01…LLM10.

---

## 2. PortSwigger Web Security Academy

- **NOW:** Web LLM attacks → Logic → Access  
- **DEFERRED:** SQLi/SSTI/XXE/NoSQL/smuggling labs → `docs/deferred/attack/portswigger-classic-injection.md`

| Тема | Теория | Labs / path |
|------|--------|-------------|
| Academy home | https://portswigger.net/web-security | |
| All labs (оглавление) | https://portswigger.net/web-security/all-labs | |
| **SQL injection** | https://portswigger.net/web-security/sql-injection | https://portswigger.net/web-security/learning-paths/sql-injection |
| **OS command injection** | https://portswigger.net/web-security/os-command-injection | (в server-side path) |
| **SSTI** (template injection) | https://portswigger.net/web-security/server-side-template-injection | exploiting: https://portswigger.net/web-security/server-side-template-injection/exploiting |
| **XXE injection** | https://portswigger.net/web-security/xxe | |
| **NoSQL injection** | https://portswigger.net/web-security/nosql-injection | |
| **Access control** | https://portswigger.net/web-security/access-control | labs с той же страницы |
| **Business logic** | https://portswigger.net/web-security/logic-flaws | labs с той же страницы |
| **Web LLM attacks** ⭐ | https://portswigger.net/web-security/llm-attacks | https://portswigger.net/web-security/learning-paths/llm-attacks |
| HTTP request smuggling (из ROADMAP) | https://portswigger.net/web-security/request-smuggling | |
| Server-side apprentice path (сводка) | https://portswigger.net/web-security/learning-paths/server-side-vulnerabilities-apprentice | |

---

## 3. MITRE — ATT&CK + ATLAS (для AI важнее ATLAS)

- **NOW:** ATLAS  
- **DEFERRED:** ATT&CK Enterprise широко → `docs/deferred/attack/mitre-attack-enterprise.md`

| Что | Ссылка | Зачем |
|-----|--------|-------|
| **MITRE ATLAS** (AI/ML TTPs) ⭐ | https://atlas.mitre.org/ | цепочки именно против AI |
| ATLAS data (GitHub YAML/STIX) | https://github.com/mitre-atlas/atlas-data | выгрузки матрицы |
| ATLAS fact sheet PDF | https://atlas.mitre.org/pdf-files/MITRE_ATLAS_Fact_Sheet.pdf | обзор |
| **ATT&CK** home | https://attack.mitre.org/ | классика enterprise |
| ATT&CK Enterprise matrix | https://attack.mitre.org/matrices/enterprise/ | Tactic→Technique |
| ATT&CK Navigator | https://mitre-attack.github.io/attack-navigator/ | визуальный слой |

---

## 4. Exploit-DB · **DEFERRED** (не ядро NOW)

Парковка: `docs/deferred/attack/exploit-db-deep.md`

| Что | Ссылка |
|-----|--------|
| Главная | https://www.exploit-db.com/ |
| Advanced search | https://www.exploit-db.com/search |
| SearchSploit manual | https://www.exploit-db.com/searchsploit |

---

## 5. LangChain / LlamaIndex (**для обоих**) · **NOW** (A4)

Выжимки + URL: `sources/05-langchain-llamaindex.md`  
Канон vault: `vault/06-Research/Agents_Engineering/frameworks/`

| Что | Ссылка |
|-----|--------|
| LC Going to production ⭐ | https://docs.langchain.com/oss/python/deepagents/going-to-production |
| LC short-term memory | https://docs.langchain.com/oss/python/langchain/short-term-memory |
| LC tools | https://docs.langchain.com/oss/python/langchain/tools |
| LI agent memory ⭐ | https://developers.llamaindex.ai/python/framework/module_guides/deploying/agents/memory/ |
| LI tools | https://developers.llamaindex.ai/python/framework/module_guides/deploying/agents/tools/ |
| LI llms.txt | https://developers.llamaindex.ai/llms.txt |
