# Ataker-Boop — Атакующий модуль Крепости

Adversarial-тестирование SecurityPipeline. Грязная зона (MacBook Air 32ГБ).

## Архитектура

```
Ataker-boop/
├── ataker/
│   ├── __init__.py          # Экспорт основных классов
│   ├── mutations.py         # 16 мутаций для обхода фильтров
│   ├── generator.py         # Генератор атак (15 категорий, шаблоны + LLM)
│   ├── vault.py             # SQLite хранилище атак + результатов
│   └── red_team_loop.py     # Основной цикл: генерация → тест → анализ → отчёт
├── tests/
│   └── test_ataker.py       # Тесты модуля
├── vault_data/              # Данные vault (gitignore'd)
└── pyproject.toml
```

## Принципы

- **Физическая изоляция**: атакующий работает на MacBook Air, отдельно от защиты (Mac Studio)
- **Blind testing**: защита НЕ видит vault атак заранее
- **Fail-open для атакующего**: если атака обошла защиту — это результат, не ошибка
- **Модель**: Mistral-7B-instruct (для генерации новых атак через LLM)

## Использование

```python
import sys
sys.path.insert(0, "Ataker-boop")

from ataker import RedTeamLoop, AttackVault, MutationEngine
from krepost.security.pipeline import SecurityPipeline

pipeline = SecurityPipeline(guard_client=...)
vault = AttackVault(db_path="vault_data/attacks.db")
loop = RedTeamLoop(pipeline=pipeline, vault=vault)

report = await loop.run(max_attacks=100)
print(report.summary())
```

## Мутации (16 стратегий)

| Мутация | Целевой слой | Описание |
|---------|-------------|----------|
| base64 | Layer 1 | Кодирование payload в base64 |
| homoglyph | Layer 1 | Замена символов кириллическими аналогами |
| zero_width | Layer 1 | Вставка невидимых Unicode-символов |
| case_mix | Layer 1 | Случайная смена регистра |
| token_split | Layer 1 | Разбиение слов дефисами |
| rot13 | Layer 1 | ROT13 кодирование |
| leetspeak | Layer 1 | Замена букв цифрами (a→4, e→3) |
| whitespace | Layer 1 | Вставка лишних пробелов |
| reverse | Layer 1 | Реверс слов |
| prefix_innocent | Layer 2 | Безобидный контекст перед атакой |
| suffix_distract | Layer 2 | Отвлекающий текст после атаки |
| language_switch | Layer 1-2 | Смена языка |
| markdown_wrap | Layer 1 | Обёртка в ```system |
| xml_wrap | Layer 1 | XML/CDATA обёртка |
| json_wrap | Layer 1 | JSON role injection |
| multi_encoding | Layer 1-2 | Комбинация base64 + homoglyph |

## 15 категорий атак

1. Direct Injection — классическое "ignore previous"
2. Role Hijack — DAN, AIM, STAN
3. System Prompt Leak — извлечение промпта
4. Encoding Bypass — base64, hex, URL-encoding
5. Homoglyph — кириллица/латиница подмена
6. Chat Template — `<|im_start|>`, `[INST]`
7. XML Injection — CDATA, `<system>`
8. Context Overflow — заполнение контекста
9. Multilingual — атаки на разных языках
10. Social Engineering — авторитет, эмоции
11. PII Extraction — извлечение данных
12. Multi-turn — многоходовые атаки
13. Jailbreak — creative writing, hypothetical
14. Adversarial Suffix — GCG-стиль суффиксы
15. Output Manipulation — управление форматом ответа
