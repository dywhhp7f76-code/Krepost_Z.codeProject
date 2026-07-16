"""Харнесс-инструменты: path-escape vault_read + schema параметров."""
from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path

from krepost.orchestration.harness_tools import (
    build_default_harness_tools,
    make_vault_read_tool,
)


class HarnessToolsTests(unittest.TestCase):
    def test_tool_names_and_parameters(self):
        tools = build_default_harness_tools(memory_store=None)
        names = {t.name for t in tools}
        self.assertEqual(names, {"fetch_url", "vault_read"})
        for t in tools:
            self.assertIn("properties", t.spec()["parameters"])

    def test_vault_read_blocks_escape(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "note.md").write_text("SECRET_OK", encoding="utf-8")
            tool = make_vault_read_tool(root)
            blocked = asyncio.run(tool.run({"path": "../note.md"}))
            self.assertIn("blocked", blocked)
            ok = asyncio.run(tool.run({"path": "note.md"}))
            self.assertEqual(ok, "SECRET_OK")


if __name__ == "__main__":
    unittest.main()
