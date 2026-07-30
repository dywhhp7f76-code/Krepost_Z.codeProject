"""Пробник #58: L1 candidates + domain aliases + subset index (numpy)."""
from __future__ import annotations

from pathlib import Path

import numpy as np

from krepost.memory.candidates import (
    export_candidates,
    load_candidates,
    parse_frontmatter,
)
from krepost.memory.domains import domain_from_relpath, folder_domain_map, normalize_folder
from krepost.memory.faiss_subset import SubsetIndex


def test_parse_frontmatter_tags_and_date():
    text = "---\ntags: [energy, solar]\ndate: 2026-03-01\n---\nbody\n"
    fm = parse_frontmatter(text)
    assert "energy" in fm["tags"]
    assert fm["date"] == "2026-03-01"


def test_domain_aliases():
    assert normalize_folder("00_System") == "00-System"
    assert domain_from_relpath("00_System/Prompts/x.md") == "00-System"
    assert domain_from_relpath("05_Knowledge/foo.md") == "05_Knowledge_Base"
    assert domain_from_relpath("05_Knowledge_Base/Books_Extracts/a.md") == "05_Knowledge_Base"
    m = folder_domain_map()
    assert any(r["folder"] == "05_Knowledge_Base" for r in m)


def test_export_and_subset_index(tmp_path: Path):
    vault = tmp_path / "vault"
    note_dir = vault / "05_Knowledge_Base" / "Books_Extracts"
    note_dir.mkdir(parents=True)
    (note_dir / "a.md").write_text(
        "---\ntags: [energy]\ndate: 2026-02-01\n---\nsolar battery note\n",
        encoding="utf-8",
    )
    (note_dir / "b.md").write_text(
        "---\ntags: [weapons]\n---\nother\n",
        encoding="utf-8",
    )
    out = vault / "00-System" / "cache" / "candidates.json"
    doc = export_candidates(
        vault, out, folders=["05_Knowledge_Base"], tags=["energy"]
    )
    assert len(doc.items) == 1
    assert doc.items[0].domain == "05_Knowledge_Base"
    loaded = load_candidates(out)
    assert loaded.paths() == doc.paths()

    idx_dir = tmp_path / "faiss"
    idx = SubsetIndex(idx_dir)

    def encode(texts):
        # детерминированный fake-embed: hash → 8d
        rows = []
        for t in texts:
            rng = np.random.default_rng(abs(hash(t)) % (2**32))
            v = rng.standard_normal(8).astype(np.float32)
            v /= np.linalg.norm(v) + 1e-12
            rows.append(v)
        return np.stack(rows)

    stats = idx.upsert(vault, loaded.paths(), encode)
    assert stats["added"] == 1
    assert idx.load()
    # повторный upsert без изменений — kept
    stats2 = idx.upsert(vault, loaded.paths(), encode)
    assert stats2["added"] == 0
    assert stats2["kept"] == 1
    hits = idx.search(encode(["solar battery"]), top_k=1, vault=vault)
    assert hits and hits[0].path.endswith("a.md")
