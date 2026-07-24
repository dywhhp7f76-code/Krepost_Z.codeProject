# OWASP Top 10 for LLM / GenAI — база векторов

**Роль:** библия Red Team по LLM. Творец обязан уметь назвать `LLM0x` и сматчить на рецепт.

**Читать:** https://genai.owasp.org/llm-top-10/  
**Архив проекта:** https://owasp.org/www-project-top-10-for-large-language-model-applications/

Ниже — **2025** (актуальный список GenAI) + примечание к legacy 1.1 (часто в старых дайджестах).

## LLM Top 10 — 2025 (GenAI)

| ID | Риск (кратко) | Что бьём у Крепости | `AttackCategory` / стратегия | Слой-гипотеза |
|----|---------------|--------------------|------------------------------|---------------|
| **LLM01** | Prompt Injection | вход `/v1/query`, multi-turn session | `direct_injection`, `jailbreak`, `multi_turn`, `social_engineering` | L1–L2 |
| **LLM02** | Sensitive Information Disclosure | утечка system/vault в ответе | `system_prompt_leak`, `pii_extraction` | L4 + output |
| **LLM03** | Supply Chain | модели/плагины/зависимости (ops) | вне payload-петли; ops/checklist | — |
| **LLM04** | Data Poisoning | vault/RAG/ingest | seeds + `retrieval poisoning` сценарии ROADMAP | L3 |
| **LLM05** | Improper Output Handling | XSS/инъекции вниз по стеку от ответа | `output_manipulation`, encoding | L4 |
| **LLM06** | Excessive Agency | `/v1/agent` tools, harness | tool-abuse redteam | agent guard |
| **LLM07** | System Prompt Leakage | те же leak-шаблоны | `system_prompt_leak`, chat_template | L2–L4 |
| **LLM08** | Vector / Embedding Weaknesses | BGE-M3 + Chroma cosine | paraphrase, dilution, multilingual | L3 |
| **LLM09** | Misinformation | over-accept GREEN | social / hypothetical framing | L2 |
| **LLM10** | Unbounded Consumption | DoS / cost / long context | `context_overflow`, model DoS | infra |

## Legacy 1.1 (для старых ссылок в ROADMAP)

LLM01 Prompt Injection · LLM02 Insecure Output · LLM03 Training Data Poisoning ·  
LLM04 Model DoS · LLM05 Supply Chain · LLM06 Sensitive Disclosure ·  
LLM07 Insecure Plugin · LLM08 Excessive Agency · LLM09 Overreliance · LLM10 Model Theft  

При конфликте номеров **в новых рецептах пиши год:** `LLM01:2025`.

## Как Творец использует

1. В `technique_ref` / reasoning: `owasp:LLM01:2025`.
2. При выборе категории — таблица выше.
3. Poisoning / Agency — отдельные волны harness (не только single-shot templates).

## TODO оператора

- [ ] Вставить выдержки / скрины из полного PDF 2025 в `ingested/`
- [ ] Пометить, какие LLM0x уже закрыты тестами Крепости
