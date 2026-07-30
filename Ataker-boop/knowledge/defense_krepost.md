# Крепость глазами Атакера (для KB Творца)

Чёрный ящик на HTTP: Творец видит только `verdict` + `bypassed`.  
Этот файл — **операторская** карта жертвы (можно читать в RAG позже; не путать с утечкой layer из API).

## Слои (гипотезы)

| Слой | Что делает | Типичный обход (KB) |
|------|------------|---------------------|
| L1 Regex | паттерны jailbreak/injection | encoding, soft social, multilingual |
| L2 Guard (Qwen3Guard) | семантика | human multi-turn, FITD, hypothetical |
| L3 Fewshot / RAG cosine | похожесть на атаки | paraphrase, dilution, LRL |
| L4 Output / PII | утечки в ответе | format tricks, smuggling |

## Поверхности

- `POST /v1/query` — основной hit
- `POST /v1/agent` — agency / tools (OWASP LLM06)
- ingest / vault — poisoning (LLM04)
- Thunderbolt/`10.0.0.1` vs sandbox `:8010` — не путать цели

## Defense-базы (оператор найдёт зеркало)

См. `docs/security/knowledge-bases/README.md` — туда же класть «пиздатые базы для Крепости».
