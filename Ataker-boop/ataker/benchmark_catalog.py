"""
Red Team AI Benchmark v2.0 — каталог 60 категорий (T11-full scaffold).

Полные offensive payloads НЕ включены (легальный источник — local JSONL).
В репо: метаданные категорий + маппинг на AttackCategory + coverage API.
См. предложения/03-redteam-benchmark.md для описания групп A–G.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Set

from ataker.generator import AttackCategory


@dataclass(frozen=True)
class BenchmarkCategory:
    benchmark_id: str
    group: str
    title: str
    attack_category: AttackCategory
    description: str


# 60 категорий из предложения 03 (группы A–G)
BENCHMARK_V2_CATEGORIES: List[BenchmarkCategory] = [
    # A: Direct Prompt Injection (15)
    BenchmarkCategory("A01-instruction-override", "A", "Instruction override", AttackCategory.DIRECT_INJECTION, "Ignore previous instructions"),
    BenchmarkCategory("A02-role-reassignment", "A", "Role reassignment", AttackCategory.ROLE_HIJACK, "You are now DAN/AIM/STAN"),
    BenchmarkCategory("A03-system-prompt-extraction", "A", "System prompt extraction", AttackCategory.SYSTEM_PROMPT_LEAK, "Repeat your system prompt"),
    BenchmarkCategory("A04-delimiter-confusion", "A", "Delimiter confusion", AttackCategory.CHAT_TEMPLATE, "Chat template injection"),
    BenchmarkCategory("A05-markdown-smuggling", "A", "Markdown smuggling", AttackCategory.CHAT_TEMPLATE, "Code fence smuggling"),
    BenchmarkCategory("A06-xml-cdata-injection", "A", "XML/CDATA injection", AttackCategory.XML_INJECTION, "XML/CDATA payloads"),
    BenchmarkCategory("A07-context-window-overflow", "A", "Context overflow", AttackCategory.CONTEXT_OVERFLOW, "Context stuffing"),
    BenchmarkCategory("A08-instruction-hierarchy", "A", "Instruction hierarchy", AttackCategory.DIRECT_INJECTION, "Higher-priority system override"),
    BenchmarkCategory("A09-few-shot-poisoning", "A", "Few-shot poisoning", AttackCategory.DIRECT_INJECTION, "Fake few-shot examples"),
    BenchmarkCategory("A10-chain-of-thought-hijack", "A", "CoT hijack", AttackCategory.JAILBREAK, "Step-by-step hijack"),
    BenchmarkCategory("A11-task-drift", "A", "Task drift", AttackCategory.MULTI_TURN, "Gradual topic shift"),
    BenchmarkCategory("A12-completion-manipulation", "A", "Completion manipulation", AttackCategory.JAILBREAK, "Incomplete sentence bait"),
    BenchmarkCategory("A13-refusal-suppression", "A", "Refusal suppression", AttackCategory.JAILBREAK, "Do not refuse"),
    BenchmarkCategory("A14-hypothetical-framing", "A", "Hypothetical framing", AttackCategory.SOCIAL_ENGINEERING, "Hypothetical scenario"),
    BenchmarkCategory("A15-persona-switch", "A", "Persona switch", AttackCategory.ROLE_HIJACK, "Evil AI persona"),
    # B: Encoding & Obfuscation (12)
    BenchmarkCategory("B01-base64-encoding", "B", "Base64 encoding", AttackCategory.ENCODING_BYPASS, "Base64 payload"),
    BenchmarkCategory("B02-rot13-encoding", "B", "ROT13 encoding", AttackCategory.ENCODING_BYPASS, "ROT13 payload"),
    BenchmarkCategory("B03-unicode-homoglyphs", "B", "Unicode homoglyphs", AttackCategory.HOMOGLYPH, "Cyrillic homoglyphs"),
    BenchmarkCategory("B04-zero-width-chars", "B", "Zero-width chars", AttackCategory.ENCODING_BYPASS, "ZWJ/ZWNJ"),
    BenchmarkCategory("B05-bidi-override", "B", "BiDi override", AttackCategory.ENCODING_BYPASS, "BiDi markers"),
    BenchmarkCategory("B06-punycode", "B", "Punycode", AttackCategory.ENCODING_BYPASS, "IDN punycode"),
    BenchmarkCategory("B07-hex-encoding", "B", "Hex encoding", AttackCategory.ENCODING_BYPASS, "Hex escape"),
    BenchmarkCategory("B08-url-encoding", "B", "URL encoding", AttackCategory.ENCODING_BYPASS, "Percent encoding"),
    BenchmarkCategory("B09-html-entities", "B", "HTML entities", AttackCategory.ENCODING_BYPASS, "Numeric entities"),
    BenchmarkCategory("B10-nested-encoding", "B", "Nested encoding", AttackCategory.ENCODING_BYPASS, "Layered encodings"),
    BenchmarkCategory("B11-token-splitting", "B", "Token splitting", AttackCategory.ENCODING_BYPASS, "Per-char splitting"),
    BenchmarkCategory("B12-language-mixing", "B", "Language mixing", AttackCategory.MULTILINGUAL, "Mid-sentence language switch"),
    # C: Indirect Injection (8)
    BenchmarkCategory("C01-document-injection", "C", "Document injection", AttackCategory.DIRECT_INJECTION, "PDF/DOCX embedded instructions"),
    BenchmarkCategory("C02-image-steganography", "C", "Image steganography", AttackCategory.ENCODING_BYPASS, "Metadata stego"),
    BenchmarkCategory("C03-url-content-injection", "C", "URL content injection", AttackCategory.DIRECT_INJECTION, "Malicious fetched page"),
    BenchmarkCategory("C04-rag-poisoning", "C", "RAG poisoning", AttackCategory.DIRECT_INJECTION, "Vector DB poison"),
    BenchmarkCategory("C05-email-injection", "C", "Email injection", AttackCategory.DIRECT_INJECTION, "Email body instructions"),
    BenchmarkCategory("C06-code-comment-injection", "C", "Code comment injection", AttackCategory.DIRECT_INJECTION, "Comments in code"),
    BenchmarkCategory("C07-csv-formula-injection", "C", "CSV formula injection", AttackCategory.DIRECT_INJECTION, "Spreadsheet formula"),
    BenchmarkCategory("C08-json-injection", "C", "JSON injection", AttackCategory.XML_INJECTION, "JSON field instructions"),
    # D: Output Manipulation (8)
    BenchmarkCategory("D01-pii-exfiltration", "D", "PII exfiltration", AttackCategory.PII_EXTRACTION, "Leak PII from context"),
    BenchmarkCategory("D02-system-prompt-leakage", "D", "System prompt leakage", AttackCategory.SYSTEM_PROMPT_LEAK, "Output-side prompt leak"),
    BenchmarkCategory("D03-api-key-leakage", "D", "API key leakage", AttackCategory.PII_EXTRACTION, "Secret exfiltration"),
    BenchmarkCategory("D04-training-data-extraction", "D", "Training data extraction", AttackCategory.SYSTEM_PROMPT_LEAK, "Memorization probe"),
    BenchmarkCategory("D05-harmful-content-generation", "D", "Harmful content", AttackCategory.OUTPUT_MANIPULATION, "Harmful generation"),
    BenchmarkCategory("D06-code-injection-output", "D", "Malicious code output", AttackCategory.OUTPUT_MANIPULATION, "Malware code gen"),
    BenchmarkCategory("D07-social-engineering-output", "D", "Social engineering output", AttackCategory.SOCIAL_ENGINEERING, "Phishing text"),
    BenchmarkCategory("D08-misinformation-generation", "D", "Misinformation", AttackCategory.OUTPUT_MANIPULATION, "False info gen"),
    # E: Multi-turn & Contextual (7)
    BenchmarkCategory("E01-multi-turn-escalation", "E", "Multi-turn escalation", AttackCategory.MULTI_TURN, "Embedded escalation"),
    BenchmarkCategory("E02-context-poisoning", "E", "Context poisoning", AttackCategory.MULTI_TURN, "Early message poison"),
    BenchmarkCategory("E03-memory-injection", "E", "Memory injection", AttackCategory.MULTI_TURN, "History injection"),
    BenchmarkCategory("E04-trust-escalation", "E", "Trust escalation", AttackCategory.MULTI_TURN, "Benign then harmful"),
    BenchmarkCategory("E05-session-confusion", "E", "Session confusion", AttackCategory.MULTI_TURN, "Cross-session attack"),
    BenchmarkCategory("E06-timing-attack", "E", "Timing attack", AttackCategory.MULTI_TURN, "Rate-limit timing"),
    BenchmarkCategory("E07-concurrent-attack", "E", "Concurrent attack", AttackCategory.MULTI_TURN, "Race condition"),
    # F: Model-Specific (5)
    BenchmarkCategory("F01-temperature-manipulation", "F", "Temperature manipulation", AttackCategory.ADVERSARIAL_SUFFIX, "Change temperature"),
    BenchmarkCategory("F02-logit-bias-injection", "F", "Logit bias injection", AttackCategory.ADVERSARIAL_SUFFIX, "Logit bias"),
    BenchmarkCategory("F03-stop-sequence-injection", "F", "Stop sequence injection", AttackCategory.CHAT_TEMPLATE, "Stop tokens"),
    BenchmarkCategory("F04-format-hijack", "F", "Format hijack", AttackCategory.OUTPUT_MANIPULATION, "Forced output format"),
    BenchmarkCategory("F05-tokenizer-exploit", "F", "Tokenizer exploit", AttackCategory.ADVERSARIAL_SUFFIX, "Special tokens"),
    # G: Advanced & Composite (5)
    BenchmarkCategory("G01-adversarial-suffix", "G", "Adversarial suffix", AttackCategory.ADVERSARIAL_SUFFIX, "GCG/AutoDAN suffix"),
    BenchmarkCategory("G02-tree-of-attacks", "G", "Tree of attacks", AttackCategory.JAILBREAK, "TAP"),
    BenchmarkCategory("G03-crescendo-attack", "G", "Crescendo attack", AttackCategory.MULTI_TURN, "Crescendo jailbreak"),
    BenchmarkCategory("G04-many-shot-jailbreak", "G", "Many-shot jailbreak", AttackCategory.JAILBREAK, "Many-shot ICL"),
    BenchmarkCategory("G05-skeleton-key", "G", "Skeleton key", AttackCategory.JAILBREAK, "Master key attack"),
]

BENCHMARK_ID_INDEX: Dict[str, BenchmarkCategory] = {
    c.benchmark_id: c for c in BENCHMARK_V2_CATEGORIES
}


def benchmark_category_ids() -> List[str]:
    return [c.benchmark_id for c in BENCHMARK_V2_CATEGORIES]


def compute_benchmark_coverage(
    covered_ids: Sequence[str],
) -> Dict[str, object]:
    """Coverage matrix: какие из 60 категорий имеют реальные payloads."""
    covered: Set[str] = set(covered_ids)
    all_ids = set(benchmark_category_ids())
    missing = sorted(all_ids - covered)
    return {
        "total_categories": len(all_ids),
        "covered": len(covered & all_ids),
        "missing": len(missing),
        "coverage_rate": len(covered & all_ids) / len(all_ids) if all_ids else 0.0,
        "missing_ids": missing,
        "covered_ids": sorted(covered & all_ids),
    }
