"""Tests for ataker.auth — 5-level access control."""
from __future__ import annotations

import pytest

from ataker.auth import CapabilityLevel


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
