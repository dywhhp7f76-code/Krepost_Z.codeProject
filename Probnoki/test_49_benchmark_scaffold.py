"""
Пробник #49 (T11-full scaffold): каталог 60 категорий Red Team Benchmark v2.0.

Полные offensive payloads не в git — только scaffold + coverage API.
Реальные атаки: seed_attacks.local.jsonl (gitignored).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "Ataker-boop"))

from ataker.benchmark_catalog import (  # noqa: E402
    BENCHMARK_V2_CATEGORIES,
    benchmark_category_ids,
    compute_benchmark_coverage,
)
from ataker.generator import AttackGenerator  # noqa: E402


class TestBenchmarkCatalog:

    def test_sixty_categories_defined(self):
        assert len(BENCHMARK_V2_CATEGORIES) == 60
        ids = benchmark_category_ids()
        assert len(ids) == 60
        assert len(set(ids)) == 60

    def test_groups_a_through_g(self):
        groups = {c.group for c in BENCHMARK_V2_CATEGORIES}
        assert groups == {"A", "B", "C", "D", "E", "F", "G"}

    def test_group_sizes(self):
        from collections import Counter
        counts = Counter(c.group for c in BENCHMARK_V2_CATEGORIES)
        assert counts["A"] == 15
        assert counts["B"] == 12
        assert counts["C"] == 8
        assert counts["D"] == 8
        assert counts["E"] == 7
        assert counts["F"] == 5
        assert counts["G"] == 5


class TestBenchmarkCoverage:

    def test_empty_coverage(self):
        cov = compute_benchmark_coverage([])
        assert cov["total_categories"] == 60
        assert cov["covered"] == 0
        assert cov["missing"] == 60
        assert cov["coverage_rate"] == 0.0

    def test_partial_coverage(self):
        cov = compute_benchmark_coverage(["A01-instruction-override", "B01-base64-encoding"])
        assert cov["covered"] == 2
        assert cov["missing"] == 58

    def test_example_seed_scaffold_zero_real_payloads(self):
        gen = AttackGenerator(seed=1)
        example = Path(__file__).parent.parent / "Ataker-boop" / "seed_attacks.example.jsonl"
        cov = gen.benchmark_coverage_from_seed(example)
        assert cov["total_categories"] == 60
        assert cov["covered"] == 0  # placeholders skipped

    def test_example_jsonl_has_sixty_lines(self):
        example = Path(__file__).parent.parent / "Ataker-boop" / "seed_attacks.example.jsonl"
        lines = [ln for ln in example.read_text().splitlines() if ln.strip()]
        assert len(lines) == 60
