"""DebriefBroker — redact fail-closed for Round Table MaskedUtterance."""

from __future__ import annotations

import re
from typing import Iterable, List, Optional, Sequence

from krepost.roundtable.schemas import MaskedUtterance, Speaker

# Payload / jailbreak / exfil heuristics (body is already supposed to be masked).
_B64_LONG = re.compile(r"(?:[A-Za-z0-9+/]{40,}={0,2})")
_HEX_BLOB = re.compile(r"(?:[0-9a-fA-F]{48,})")
_JAILBREAK = re.compile(
    r"(ignore\s+(all\s+)?(previous|prior)\s+instructions|"
    r"jailbreak|DAN\b|do\s+anything\s+now|"
    r"system\s+prompt\s+is|you\s+are\s+now\s+unrestricted)",
    re.I,
)
_COPY_PAYLOAD = re.compile(
    r"(скопируй|copy\s+this|paste\s+into|вставь\s+в\s+чат|"
    r"полный\s+текст\s+атаки|raw\s+payload|attack\s+payload)",
    re.I,
)
_WEAKNESS_RECIPE = re.compile(
    r"(слабость\s+крепости|weakness\s+of\s+krepost|"
    r"bypass\s+layer\s*[1234]\s+by|обойди\s+guard\s+так)",
    re.I,
)
_REGEX_LEAK = re.compile(r"\(\?[=!<]|\\\\b[a-z]{2,}\\\\b.*\|.*\\\\b")
_PATH_POISON = re.compile(
    r"(/Volumes/|Ataker-SSD|SN850X|poison[_-]?corpus|/яды/)",
    re.I,
)
_PROMPT_LEAK = re.compile(
    r"(system\s*:\s*|<<SYS>>|<\|im_start\|>|GUARD_PROMPT|few-?shot\s*:)",
    re.I,
)

_MAX_BODY = 1200
_MAX_OPERATOR = 2000


class RedactionError(ValueError):
    """Message rejected by DebriefBroker (fail-closed)."""

    def __init__(self, reason_code: str, detail: str = "") -> None:
        self.reason_code = reason_code
        self.detail = detail
        super().__init__(f"{reason_code}: {detail}" if detail else reason_code)


class DebriefBroker:
    """Filter speaker text into MaskedUtterance or raise RedactionError."""

    def __init__(
        self,
        *,
        max_body: int = _MAX_BODY,
        max_operator: int = _MAX_OPERATOR,
        known_ids: Optional[Iterable[str]] = None,
    ) -> None:
        self.max_body = max_body
        self.max_operator = max_operator
        self._known_ids = {x.strip().lower() for x in (known_ids or []) if x}

    def register_ids(self, ids: Sequence[str]) -> None:
        for i in ids:
            if i:
                self._known_ids.add(i.strip().lower())

    def mask(
        self,
        speaker: Speaker | str,
        body: str,
        cites: Optional[Sequence[str]] = None,
    ) -> MaskedUtterance:
        sp = Speaker(speaker) if not isinstance(speaker, Speaker) else speaker
        text = (body or "").strip()
        if not text:
            raise RedactionError("empty_body")

        limit = self.max_operator if sp == Speaker.operator else self.max_body
        if len(text) > limit:
            raise RedactionError("body_too_long", f">{limit}")

        flags: List[str] = []
        if sp != Speaker.operator:
            self._scan_side(sp, text, flags)

        cite_list = [c.strip().lower() for c in (cites or []) if c and c.strip()]
        for c in cite_list:
            if len(c) < 8:
                raise RedactionError("cite_too_short", c)
            # Unknown cites allowed (forward refs) but flagged.
            if self._known_ids and c not in self._known_ids:
                flags.append(f"unknown_cite:{c[:12]}")

        if sp in (Speaker.ataker, Speaker.krepost) and not cite_list:
            # Soft require: must cite at least one receipt id for non-operator.
            raise RedactionError("cites_required", "ataker/krepost need attack_id|defense_id")

        return MaskedUtterance(
            speaker=sp,
            body=text,
            cites=cite_list,
            redaction_flags=flags,
        )

    def _scan_side(self, speaker: Speaker, text: str, flags: List[str]) -> None:
        checks = [
            (_B64_LONG, "b64_blob"),
            (_HEX_BLOB, "hex_blob"),
            (_JAILBREAK, "jailbreak_phrase"),
            (_COPY_PAYLOAD, "copy_payload"),
            (_PATH_POISON, "poison_path"),
            (_PROMPT_LEAK, "prompt_leak"),
        ]
        if speaker == Speaker.krepost:
            checks.extend(
                [
                    (_WEAKNESS_RECIPE, "weakness_recipe"),
                    (_REGEX_LEAK, "regex_leak"),
                ]
            )
        if speaker == Speaker.ataker:
            checks.append((_WEAKNESS_RECIPE, "weakness_recipe"))

        for rx, code in checks:
            if rx.search(text):
                raise RedactionError(code)
