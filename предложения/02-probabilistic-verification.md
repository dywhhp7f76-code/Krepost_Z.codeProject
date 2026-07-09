# Предложение 02: Вероятностная верификация на базе Datalog

## Что

Расширение Layer 2 (GuardClassifier) вероятностной верификацией на основе Datalog. Вместо бинарного вердикта RED/GREEN --- возврат вероятностных границ (probability bounds) для чувствительности фильтра. Это позволяет динамически настраивать порог срабатывания в зависимости от контекста сессии, истории пользователя и текущего уровня угрозы.

Основа: подход из статьи arXiv:2606.20510v1 --- формальная верификация нейросетевых классификаторов через probabilistic Datalog с interval arithmetic.

## Зачем

1. **Ограничение текущего подхода.** GuardClassifier возвращает `Tuple[Verdict, float, str]` --- вердикт (GREEN/YELLOW/RED), confidence (0.0--1.0) и причину. Но confidence --- это самооценка модели, а не формально верифицированная вероятность. Модель может быть "уверена" в GREEN при adversarial input.

2. **Динамический порог.** Сейчас порог фиксирован: YELLOW и RED блокируют. С вероятностными границами можно ужесточать/смягчать фильтр:
   - Новая сессия без истории: strict bounds (P(safe) > 0.95)
   - Trusted session с историей GREEN: relaxed bounds (P(safe) > 0.80)
   - Повышенный уровень угрозы (всплеск RED в метриках): emergency bounds (P(safe) > 0.99)

3. **Аудируемость.** Probability bounds --- формальный артефакт, который можно включить в `SecurityReceipt.audit_hash`. В отличие от self-reported confidence, bounds верифицируемы.

4. **Интеграция с Layer 3.** FewShotMatcher использует cosine similarity с порогом 0.92. Вероятностные bounds от Layer 2 могут модулировать этот порог: при низкой уверенности Guard --- снижать threshold FewShot для дополнительной проверки.

## Что добавляется

| Файл | Назначение |
|------|------------|
| `krepost/security/probabilistic.py` | Движок вероятностного Datalog: facts, rules, interval propagation |
| `krepost/security/pipeline.py` (изменения) | Расширение GuardClassifier.classify() для возврата bounds |
| `krepost/security/policy.dl` | Datalog-правила безопасности для Krepost |
| `tests/test_probabilistic.py` | Тесты для вероятностного движка |

### Эскиз кода: расширение GuardClassifier.classify()

```python
from dataclasses import dataclass
from typing import Tuple, Optional

@dataclass
class ProbabilityBounds:
    """Вероятностные границы вердикта."""
    p_safe_lower: float    # нижняя граница P(safe)
    p_safe_upper: float    # верхняя граница P(safe)
    p_attack_lower: float  # нижняя граница P(attack)
    p_attack_upper: float  # верхняя граница P(attack)
    method: str            # "datalog" | "ensemble" | "calibrated"

    @property
    def is_certain_safe(self) -> bool:
        """P(safe) нижняя граница выше порога."""
        return self.p_safe_lower > 0.95

    @property
    def is_certain_attack(self) -> bool:
        """P(attack) нижняя граница выше порога."""
        return self.p_attack_lower > 0.90

    @property
    def is_ambiguous(self) -> bool:
        """Широкий интервал --- нужна доп. проверка."""
        return (self.p_safe_upper - self.p_safe_lower) > 0.3


class ProbabilisticGuardClassifier(GuardClassifier):
    """
    Расширение GuardClassifier с вероятностными границами.

    Вместо доверия self-reported confidence модели,
    вычисляет формальные bounds через:
    1. Datalog-правила над фактами (входные признаки)
    2. Interval arithmetic для propagation неопределённости
    3. Калибровка по историческим данным (Platt scaling)
    """

    def __init__(self, *args, datalog_rules_path: str = "policy.dl",
                 calibration_data: Optional[dict] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.rules = self._load_datalog_rules(datalog_rules_path)
        self.calibration = calibration_data or {}

    def _load_datalog_rules(self, path: str) -> list:
        """Загрузить Datalog-правила из файла."""
        # Правила вида:
        # safe(X) :- not_injection(X), not_jailbreak(X), confidence(X, C), C > 0.8.
        # attack(X) :- injection(X, P), P > 0.7.
        # ambiguous(X) :- not safe(X), not attack(X).
        return []  # placeholder --- загрузка из .dl файла

    async def classify_with_bounds(
        self, text: str, session_context: Optional[dict] = None
    ) -> Tuple["Verdict", float, str, ProbabilityBounds]:
        """
        Классифицировать текст с вероятностными границами.

        Returns:
            verdict: GREEN/YELLOW/RED (совместимость с текущим API)
            confidence: float (для обратной совместимости)
            reason: str
            bounds: ProbabilityBounds (новое)
        """
        # Шаг 1: стандартная классификация через Guard-модель
        verdict, confidence, reason = await self.classify(text)

        # Шаг 2: извлечь факты для Datalog
        facts = self._extract_facts(text, verdict, confidence, session_context)

        # Шаг 3: вычислить probability bounds через Datalog
        bounds = self._compute_bounds(facts)

        # Шаг 4: скорректировать вердикт по bounds
        adjusted_verdict = self._adjust_verdict(verdict, bounds)

        return adjusted_verdict, confidence, reason, bounds

    def _extract_facts(self, text: str, verdict: str,
                       confidence: float, session_ctx: Optional[dict]) -> dict:
        """Извлечь факты из входных данных для Datalog-движка."""
        facts = {
            "text_length": len(text),
            "guard_verdict": verdict,
            "guard_confidence": confidence,
            "has_base64": bool(re.search(r"[A-Za-z0-9+/]{16,}={0,2}", text)),
            "has_unicode_anomaly": any(ord(c) > 0x2000 for c in text),
            "has_chat_template": bool(re.search(
                r"(?i)(system|assistant|user)\s*:", text)),
            "entropy": self._text_entropy(text),
        }

        if session_ctx:
            facts["session_trust_level"] = session_ctx.get("trust_level", 0)
            facts["session_history_green"] = session_ctx.get("green_count", 0)
            facts["session_history_red"] = session_ctx.get("red_count", 0)

        return facts

    def _compute_bounds(self, facts: dict) -> ProbabilityBounds:
        """
        Вычислить probability bounds через Datalog + interval arithmetic.

        Основная идея (arXiv:2606.20510v1):
        - Каждый факт имеет interval [lower, upper] вместо точного значения
        - Правила Datalog propagate intervals через логические операции
        - AND: [max(l1,l2), min(u1,u2)]
        - OR:  [max(l1,l2), min(1, u1+u2)]
        - NOT: [1-u, 1-l]
        """
        gc = facts["guard_confidence"]
        v = facts["guard_verdict"]

        # Базовые интервалы из Guard-модели (с поправкой на калибровку)
        if v == "GREEN":
            p_safe = [gc * 0.85, min(1.0, gc * 1.1)]   # Guard склонен к optimism
            p_attack = [0.0, 1.0 - gc * 0.85]
        elif v == "RED":
            p_safe = [0.0, 1.0 - gc * 0.8]
            p_attack = [gc * 0.8, min(1.0, gc * 1.1)]
        else:  # YELLOW
            p_safe = [0.2, 0.7]
            p_attack = [0.15, 0.6]

        # Модуляция по дополнительным фактам
        if facts.get("has_base64"):
            p_attack[0] = max(p_attack[0], 0.3)  # base64 повышает нижнюю границу
        if facts.get("has_unicode_anomaly"):
            p_attack[0] = max(p_attack[0], 0.2)
        if facts.get("has_chat_template"):
            p_attack[0] = max(p_attack[0], 0.5)

        # Модуляция по сессии
        trust = facts.get("session_trust_level", 0)
        if trust > 5:
            p_safe[0] = min(p_safe[0] + 0.05, p_safe[1])

        # Нормализация
        p_safe = [max(0.0, p_safe[0]), min(1.0, p_safe[1])]
        p_attack = [max(0.0, p_attack[0]), min(1.0, p_attack[1])]

        return ProbabilityBounds(
            p_safe_lower=p_safe[0],
            p_safe_upper=p_safe[1],
            p_attack_lower=p_attack[0],
            p_attack_upper=p_attack[1],
            method="datalog"
        )

    def _adjust_verdict(self, original: str, bounds: ProbabilityBounds) -> str:
        """Скорректировать вердикт на основе bounds."""
        if bounds.is_certain_attack:
            return "RED"
        if bounds.is_ambiguous and original == "GREEN":
            return "YELLOW"  # понизить уверенность при широком интервале
        if bounds.is_certain_safe:
            return "GREEN"
        return original  # сохранить оригинальный вердикт

    @staticmethod
    def _text_entropy(text: str) -> float:
        """Информационная энтропия текста (биты)."""
        import math
        if not text:
            return 0.0
        freq = {}
        for c in text:
            freq[c] = freq.get(c, 0) + 1
        length = len(text)
        return -sum((count/length) * math.log2(count/length)
                     for count in freq.values())
```

### Эскиз Datalog-правил (policy.dl)

```prolog
% Krepost Security Policy — Probabilistic Datalog
% Интервалы: каждый предикат имеет [lower, upper] bound

% Факты из входных данных
:- input(text_length, guard_verdict, guard_confidence).
:- session(trust_level, green_count, red_count).

% Правила безопасности
safe(X) :-
    guard_verdict(X, "GREEN"),
    guard_confidence(X, C), C > 0.85,
    not has_chat_template(X),
    not has_base64_anomaly(X).

suspicious(X) :-
    has_base64(X),
    has_unicode_anomaly(X).

suspicious(X) :-
    has_chat_template(X).

attack(X) :-
    guard_verdict(X, "RED"),
    guard_confidence(X, C), C > 0.7.

attack(X) :-
    suspicious(X),
    guard_verdict(X, V), V \= "GREEN".

% Динамический порог по контексту сессии
relaxed_threshold(X) :-
    session_trust(X, T), T > 5,
    session_green_count(X, G), G > 10,
    session_red_count(X, R), R == 0.

strict_threshold(X) :-
    session_red_count(X, R), R > 0.

emergency_threshold(X) :-
    global_red_rate(Rate), Rate > 0.3.
```

## Зависимости

| Зависимость | Версия | Назначение |
|-------------|--------|------------|
| Нет внешних зависимостей | --- | Datalog-движок реализуется на чистом Python (100-200 строк для базового propagation). Альтернатива: `pyDatalog` (если нужны сложные правила). |

Вся логика --- чистый Python + interval arithmetic. Не требует GPU, не добавляет latency (вычисление bounds < 1ms после получения ответа Guard).

## Риски

1. **Калибровка bounds.** Начальные интервалы (0.85, 1.1 для GREEN) --- эвристика. Без исторических данных реальных атак калибровка будет неточной. **Митигация:** собирать статистику в `SecurityPipeline.metrics`, калибровать через Platt scaling после накопления 1000+ labeled examples.

2. **Ложное расширение YELLOW.** Переход GREEN->YELLOW при широком интервале (`is_ambiguous`) может увеличить false positive rate, блокируя легитимные запросы. **Митигация:** начать с логирования bounds без изменения вердикта (shadow mode), анализировать через неделю.

3. **Сложность Datalog-правил.** При росте числа правил и фактов возможны циклы и бесконечная рекурсия. **Митигация:** ограничить глубину вывода (max_depth=10), stratification для negation.

4. **Совместимость API.** Новый метод `classify_with_bounds()` возвращает 4 значения вместо 3. Существующий `classify()` не затрагивается --- обратная совместимость сохраняется. `SecurityPipeline.process()` потребует рефакторинга для использования bounds.

5. **Формальная корректность.** Подход из arXiv:2606.20510v1 требует точной формализации нейросетевого классификатора как набора Datalog-фактов. Для Qwen3Guard-Gen-4B (generative model, не classifier) маппинг не тривиален. **Митигация:** использовать выходные JSON-поля модели (`status`, `confidence`, `reason`) как input facts, а не внутренние веса.

## Статус: ⏳ Ожидает одобрения
