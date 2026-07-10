"""
krepost/security/normalize.py v2.2
Единый источник правды для канонизации текста.

Используется:
- pipeline.py (для audit_hash)
- trust_registry.py (для trust_hash)
- Версионирование нормализации для миграций
"""

import re
import unicodedata

# Версия нормализации (P2 #30)
NORMALIZATION_VERSION = "2.2.0"

# Максимальная длина текста для normalize.py-функций (defense-in-depth;
# pipeline.py.RegexFilter имеет собственный, более строгий лимит 32000,
# проверяемый раньше — этот лимит защищает прямых вызывающих, например
# trust_registry.py, у которых своей проверки длины нет).
MAX_NORMALIZE_LENGTH = 200_000

# Расширенная таблица гомоглифов (P1 #37, P2 #37)
_HOMOGLYPH_MAP = str.maketrans({
    # Кириллица → латиница
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "х": "x",
    "у": "y", "і": "i", "ӏ": "l", "ј": "j", "ѕ": "s", "ѵ": "y",
    "А": "A", "В": "B", "Е": "E", "К": "K", "М": "M", "Н": "H",
    "О": "O", "Р": "P", "С": "C", "Т": "T", "Х": "X", "У": "Y",
    "І": "I", "Ј": "J", "Ѕ": "S",
    "г": "r", "д": "d", "л": "l",  # P2 #37

    # Греческий → латиница (P2 #37)
    "α": "a", "β": "b", "γ": "y", "δ": "d", "ε": "e", "ζ": "z",
    "η": "h", "θ": "th", "ι": "i", "κ": "k", "λ": "l", "μ": "m",
    "ν": "v", "ξ": "x", "ο": "o", "π": "p", "ρ": "r", "σ": "c",
    "τ": "t", "υ": "u", "φ": "f", "χ": "ch", "ψ": "ps", "ω": "o",
    "ϲ": "c",  # lunate sigma

    # Цифры ↔ буквы (P2 #37)
    "0": "o", "1": "i", "5": "s",
    "|": "i",
})
# Примечание: full-width формы (Ａ-Ｚ, ａ-ｚ, ０-９, U+FF00-FFEF) отдельно
# не маппятся — NFKC-нормализация (шаг 2 ниже) уже разворачивает их в
# обычный ASCII до применения этой таблицы, добавлять их сюда избыточно.

# Zero-width + BiDi + NBSP (P2 #37)
_ZERO_WIDTH = dict.fromkeys([
    0x200b,  # zero width space
    0x200c,  # zero width non-joiner
    0x200d,  # zero width joiner
    0xfeff,  # BOM
    0x2060,  # word joiner
    0x200e,  # left-to-right mark
    0x200f,  # right-to-left mark
    0x202a,  # left-to-right embedding
    0x202b,  # right-to-left embedding
    0x202c,  # pop directional formatting
    0x202d,  # left-to-right override
    0x202e,  # right-to-left override
    0x2066,  # left-to-right isolate
    0x2067,  # right-to-left isolate
    0x2068,  # first strong isolate
    0x2069,  # pop directional isolate
    0x00a0,  # non-breaking space (P2 #37)
    0x202f,  # narrow no-break space (P2 #37)
], None)

# C0/C1 control characters (кроме \t \n \r — они легитимные разделители и
# схлопываются в пробел на шаге 5). Удаляются, а НЕ заменяются пробелом:
# "ig\x01nore" -> "ignore", иначе паттерн "ignore" не сматчится. Тот же
# принцип, что у zero-width: control-символ внутри слова инъекции пробивал
# Layer 1 regex (DEL/SOH/STX/EOT/NUL/C1 давали BYPASS). См. Probnoki #22.
_CONTROL_CHARS = dict.fromkeys(
    [c for c in range(0x00, 0x20) if c not in (0x09, 0x0a, 0x0d)]  # C0 без \t\n\r
    + [0x7f]                                                        # DEL
    + list(range(0x80, 0xa0)),                                     # C1
    None,
)


def canonicalize_for_hash(text: str) -> str:
    """
    Канонизация текста для хеширования.

    Порядок (P2 #11):
    1. zero-width/BiDi/NBSP removal
    2. NFKC normalization
    3. casefold
    4. confusables (homoglyphs)
    5. collapse whitespace

    Returns:
        Канонизированная строка для хеширования
    """
    if not text:
        return ""

    if len(text) > MAX_NORMALIZE_LENGTH:
        raise ValueError(f"input_too_long:{len(text)}>{MAX_NORMALIZE_LENGTH}")

    # ASCII fast-path: zero-width/BiDi/NBSP и NFKC — no-op на чистом ASCII,
    # их можно безопасно пропустить. Casefold и confusables (включая
    # цифровые "0"/"1"/"5"/"|") по-прежнему применяются — они влияют
    # на чистый ASCII текст (leetspeak, chat-template обход).
    if text.isascii():
        t = text.translate(_CONTROL_CHARS)
        t = t.casefold()
        t = t.translate(_HOMOGLYPH_MAP)
        t = re.sub(r"\s+", " ", t).strip()
        return t

    # 1. Zero-width + BiDi + NBSP + control-символы removal
    t = text.translate(_ZERO_WIDTH)
    t = t.translate(_CONTROL_CHARS)

    # 2. NFKC normalization
    t = unicodedata.normalize("NFKC", t)

    # 3. casefold (перед confusables для корректной работы)
    t = t.casefold()

    # 4. Confusables mapping
    t = t.translate(_HOMOGLYPH_MAP)

    # 5. Collapse whitespace
    t = re.sub(r"\s+", " ", t).strip()

    return t


def normalize_for_scanning(text: str, soft: bool = False) -> str:
    """
    Нормализация для сканирования правилами.

    Args:
        text: Исходный текст
        soft: Если True — сохраняет кириллицу (для русских правил)
              Если False — дегомоглифизирует полностью

    Returns:
        Нормализованный текст для сканирования
    """
    if not text:
        return ""

    if len(text) > MAX_NORMALIZE_LENGTH:
        raise ValueError(f"input_too_long:{len(text)}>{MAX_NORMALIZE_LENGTH}")

    # ASCII fast-path: см. canonicalize_for_hash — zero-width/BiDi/NBSP и
    # NFKC являются no-op на чистом ASCII, остальные шаги выполняются как
    # обычно (confusables всё ещё нужны для цифрового leetspeak на ASCII).
    if text.isascii():
        t = text.translate(_CONTROL_CHARS)
        t = t.casefold()
        if not soft:
            t = t.translate(_HOMOGLYPH_MAP)
        t = re.sub(r"\s+", " ", t).strip()
        return t

    # 1. Zero-width + control-символы removal
    t = text.translate(_ZERO_WIDTH)
    t = t.translate(_CONTROL_CHARS)

    # 2. NFKC
    t = unicodedata.normalize("NFKC", t)

    # 3. casefold
    t = t.casefold()

    # 4. Confusables (только если не soft)
    if not soft:
        t = t.translate(_HOMOGLYPH_MAP)

    # 5. Collapse
    t = re.sub(r"\s+", " ", t).strip()

    return t
