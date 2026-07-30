"""Unit tests for Tailscale bridge helpers (no Tailscale required)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "KrepostChat"))
from bridge import url_for_host


def test_url_for_host():
    assert url_for_host("100.1.2.3", 8000) == "http://100.1.2.3:8000"
    assert url_for_host("http://100.1.2.3:9000") == "http://100.1.2.3:9000"
