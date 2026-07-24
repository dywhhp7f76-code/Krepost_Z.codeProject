# Ссылки defense для Крепости — читай и фильтруй

> Зеркало атакующего `Ataker-boop/knowledge/SOURCES.md`.  
> Отметь: `✅ взять` / `⏸ потом` / `❌ мимо` → потом занесём только отобранное.
>
> **Календарь:** `docs/planning/CALENDAR.md` · **Парковка:** `docs/deferred/defense/`

| Метка | Смысл |
|-------|--------|
| **NOW** | CSF Protect/Detect/Respond + SRE Monitoring/Cascading (до 14 Aug) |
| **DEFERRED** | CNCF/K8s deep, полный NIST mapping, Azure deep, SRE Alerting |

---

## 1. NIST — Cybersecurity Framework (CSF) · **NOW** (обзор) / deep → deferred

Defense in Depth + Govern/Identify/Protect/Detect/Respond/Recover.

| Что | Ссылка |
|-----|--------|
| **PDF CSF 2.0 (полный)** | https://nvlpubs.nist.gov/nistpubs/CSWP/NIST.CSWP.29.pdf |
| DOI / citation | https://doi.org/10.6028/NIST.CSWP.29 |
| Хаб CSF | https://www.nist.gov/cyberframework |
| Публикация NIST | https://www.nist.gov/publications/nist-cybersecurity-framework-csf-20 |
| CSRC page | https://csrc.nist.gov/pubs/cswp/29/the-nist-cybersecurity-framework-csf-20/final |
| Анонс 2.0 | https://www.nist.gov/news-events/news/2024/02/nist-releases-version-20-landmark-cybersecurity-framework |

**С чего начать:** PDF CSF 2.0 → функции **Protect / Detect / Respond** под слои Крепости и мониторинг.

---

## 2. CNCF — Security (контейнеры / изоляция) · **DEFERRED**

Парковка: `docs/deferred/defense/cncf-k8s-deep.md`

| Что | Ссылка |
|-----|--------|
| TAG Security — whitepaper hub | https://tag-security.cncf.io/community/resources/security-whitepaper/ |
| **PDF Cloud Native Security Whitepaper v2** | https://tag-security.cncf.io/community/resources/security-whitepaper/v2/CNCF_cloud-native-security-whitepaper-May2022-v2.pdf |
| Анонс v2 (CNCF blog) | https://www.cncf.io/blog/2022/05/18/announcing-the-refreshed-cloud-native-security-whitepaper/ |
| Kubernetes: Cloud Native Security | https://kubernetes.io/docs/concepts/security/cloud-native-security/ |
| K8s security overview / checklist | https://kubernetes.io/docs/concepts/security/ |
| Pod Security Standards | https://kubernetes.io/docs/concepts/security/pod-security-standards/ |

**С чего начать:** whitepaper v2 (Develop→Distribute→Deploy→Runtime) → что применимо к Studio/Air/Docker (если есть), изоляция процессов = Камень физической изоляции Крепости.

---

## 3. Google SRE Book — Monitoring / Alerting / Cascading Failures

- **NOW:** Monitoring + Cascading Failures  
- **DEFERRED:** Practical Alerting / Overload / postmortem → `docs/deferred/defense/sre-alerting-overload.md`

Онлайн-книга (бесплатно): https://sre.google/sre-book/table-of-contents/

| Глава (то, что ты назвал) | Ссылка |
|---------------------------|--------|
| **Monitoring Distributed Systems** (4 golden signals) | https://sre.google/sre-book/monitoring-distributed-systems/ |
| **Practical Alerting** | https://sre.google/sre-book/practical-alerting/ |
| **Addressing Cascading Failures** | https://sre.google/sre-book/addressing-cascading-failures/ |
| Handling Overload (соседи по теме) | https://sre.google/sre-book/handling-overload/ |
| Embodied in production best practices | https://sre.google/sre-book/service-best-practices/ |
| Example postmortem | https://sre.google/sre-book/example-postmortem/ |

**С чего начать:** Monitoring → Cascading Failures → Practical Alerting. Это прямо про асимметрию ресурсов и «не упасть под redteam/нагрузкой».

---

## 4. Microsoft — Azure / AI security best practices · **NOW** (один обзор) / deep → deferred

Парковка deep: `docs/deferred/defense/azure-ai-security-deep.md`

| Что | Ссылка |
|-----|--------|
| **Azure AI security best practices** | https://learn.microsoft.com/en-us/azure/security/fundamentals/ai-security-best-practices |
| Security planning for LLM apps | https://learn.microsoft.com/en-us/ai/playbook/technology-guidance/generative-ai/mlops-in-openai/security/security-plan-llm-application |
| Get started securing AI app | https://learn.microsoft.com/en-us/azure/developer/ai/get-started-securing-your-ai-app |
| Azure OpenAI network / private endpoints (Learn) | https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/network (если 404 — искать «Network and access configuration for Azure OpenAI» на learn.microsoft.com) |
| Content Safety (фильтры входа/выхода) | https://learn.microsoft.com/en-us/azure/ai-services/content-safety/overview |

**С чего начать:** AI security best practices → Security planning for LLM (prompt injection / agency / filtering) — идеи для L1–L4 и `/v1/agent`, даже если Крепость не на Azure.

---

## 5. LangChain / LlamaIndex (**для обоих** — уже загружено) · **NOW** (A4)

Выжимки + URL: `sources/05-langchain-llamaindex.md`  
Канон vault: `vault/06-Research/Agents_Engineering/frameworks/`

| Что | Ссылка |
|-----|--------|
| LC Going to production ⭐ | https://docs.langchain.com/oss/python/deepagents/going-to-production |
| LC permissions | https://docs.langchain.com/oss/python/deepagents/permissions |
| LC guardrails | https://docs.langchain.com/oss/python/langchain/guardrails |
| LC HITL | https://docs.langchain.com/oss/python/langchain/human-in-the-loop |
| LI agent memory ⭐ | https://developers.llamaindex.ai/python/framework/module_guides/deploying/agents/memory/ |
| LI tools | https://developers.llamaindex.ai/python/framework/module_guides/deploying/agents/tools/ |

---

## Твой фильтр

```
NIST CSF 2.0 PDF:        ✅ / ⏸ / ❌
CNCF Security WP v2:     ✅ / ⏸ / ❌
K8s cloud-native sec:    ✅ / ⏸ / ❌
SRE Monitoring:          ✅ / ⏸ / ❌
SRE Alerting:            ✅ / ⏸ / ❌
SRE Cascading Failures:  ✅ / ⏸ / ❌
Azure AI sec practices:  ✅ / ⏸ / ❌
LLM security planning:   ✅ / ⏸ / ❌
LangChain docs:          ✅ / ⏸ / ❌
LlamaIndex docs:         ✅ / ⏸ / ❌
```

Кинь ответ — заведу только отобранное в `docs/security/knowledge-bases/sources/`.
