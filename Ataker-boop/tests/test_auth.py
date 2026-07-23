"""Tests for ataker.auth — 5-level access control."""
from __future__ import annotations

import pytest

from ataker.auth import CapabilityLevel, PlannerCapabilities


class TestCapabilityLevel:
    def test_has_five_levels(self):
        levels = list(CapabilityLevel)
        assert len(levels) == 5

    def test_level_values_are_sequential(self):
        values = [l.value for l in CapabilityLevel]
        assert values == [1, 2, 3, 4, 5]

    def test_level_names_match_spec(self):
        assert CapabilityLevel.L1_POISONS.value == 1
        assert CapabilityLevel.L2_CHIMERA.value == 2
        assert CapabilityLevel.L3_CODEBREAK.value == 3
        assert CapabilityLevel.L4_AGENTS.value == 4
        assert CapabilityLevel.L5_KILL.value == 5

    def test_unlockable_excludes_l1_and_l5(self):
        """L1 always open, L5 is kill (different mechanism)."""
        assert CapabilityLevel.L1_POISONS not in CapabilityLevel.UNLOCKABLE
        assert CapabilityLevel.L5_KILL not in CapabilityLevel.UNLOCKABLE
        assert CapabilityLevel.L2_CHIMERA in CapabilityLevel.UNLOCKABLE
        assert CapabilityLevel.L3_CODEBREAK in CapabilityLevel.UNLOCKABLE
        assert CapabilityLevel.L4_AGENTS in CapabilityLevel.UNLOCKABLE


class TestPlannerCapabilitiesLocked:
    def test_locked_factory_has_only_l1(self):
        caps = PlannerCapabilities.locked()
        assert caps.has(CapabilityLevel.L1_POISONS) is True
        assert caps.has(CapabilityLevel.L2_CHIMERA) is False
        assert caps.has(CapabilityLevel.L3_CODEBREAK) is False
        assert caps.has(CapabilityLevel.L4_AGENTS) is False

    def test_has_requires_all_lower_levels(self):
        """L3 требует L2 — если L2 не открыт, L3 тоже False."""
        caps = PlannerCapabilities.locked()
        caps.unlocked_levels.add(CapabilityLevel.L3_CODEBREAK)
        # L2 не открыт → L3 has() должен вернуть False
        assert caps.has(CapabilityLevel.L3_CODEBREAK) is False

    def test_has_l3_true_when_l2_also_unlocked(self):
        caps = PlannerCapabilities.locked()
        caps.unlocked_levels.add(CapabilityLevel.L2_CHIMERA)
        caps.unlocked_levels.add(CapabilityLevel.L3_CODEBREAK)
        assert caps.has(CapabilityLevel.L3_CODEBREAK) is True

    def test_fully_locked_blocks_even_l1(self):
        """Kill switch блокирует даже L1."""
        caps = PlannerCapabilities.locked()
        caps.fully_locked = True
        assert caps.has(CapabilityLevel.L1_POISONS) is False
