#!/usr/bin/env python3
"""Build Ataker training arsenal under /fortress_data/attacker/.

Hard caps: total <= 2.0 GB; optional extras <= 400 MB each (max 3).
No Exploit-DB. No crypto/survival/fire reference dumps.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import shutil
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

ROOT = Path(os.environ.get("FORTRESS_DATA", "/fortress_data/attacker")).expanduser().resolve()
INCOMING = ROOT / "_incoming"
NORMALIZED = ROOT / "normalized"
MANIFEST_PATH = ROOT / "manifest.json"
REJECTED_PATH = ROOT / "REJECTED.md"
BUDGET_BYTES = int(2.0 * 1024**3)
EXTRA_MAX_BYTES = int(400 * 1024**2)
TOXIGEN_SOFT_CAP = int(800 * 1024**2)
TOXIGEN_SAMPLE_ROWS = 50_000

CATEGORIES = {
    "direct_injection",
    "role_hijack",
    "system_prompt_leak",
    "encoding_bypass",
    "homoglyph",
    "chat_template",
    "xml_injection",
    "context_overflow",
    "multilingual",
    "social_engineering",
    "pii_extraction",
    "multi_turn",
    "jailbreak",
    "adversarial_suffix",
    "output_manipulation",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def dir_size(path: Path) -> int:
    total = 0
    if not path.exists():
        return 0
    for p in path.rglob("*"):
        if p.is_file():
            total += p.stat().st_size
    return total


def enforce_budget(label: str) -> None:
    used = dir_size(ROOT)
    print(f"[budget] after {label}: {used / 1024**2:.1f} MB / {BUDGET_BYTES / 1024**2:.0f} MB")
    if used > BUDGET_BYTES:
        raise SystemExit(f"STOP: budget exceeded ({used} > {BUDGET_BYTES})")


def hash16(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:16]


def guess_category(text: str, source_hint: str = "") -> Tuple[str, bool]:
    t = (text or "").lower()
    rules = [
        ("direct_injection", ("ignore previous", "disregard prior", "override all", "forget the above", "new instructions")),
        ("role_hijack", ("you are now dan", "do anything now", "aim,", "stan (", "developer mode", "jailbreak mode")),
        ("system_prompt_leak", ("system prompt", "reveal your instructions", "print your rules", "what are your instructions")),
        ("encoding_bypass", ("base64", "rot13", "hex decode", "url-encoded", "decode this")),
        ("homoglyph", ("homoglyph", "cyrillic lookalike", "confusable")),
        ("chat_template", ("<|im_start|>", "[inst]", "<<sys>>", "<|system|>")),
        ("xml_injection", ("<system>", "<![cdata", "</system>", "<instructions>")),
        ("context_overflow", ("repeat the word", "fill the context", "pad with")),
        ("multilingual", ("на русском", "auf deutsch", "en español", "用中文")),
        ("social_engineering", ("my grandmother", "for educational purposes", "i am a researcher", "urgent", "as an authority")),
        ("pii_extraction", ("social security", "credit card", "phone number", "home address", "passport number")),
        ("multi_turn", ("earlier you said", "continuing from", "as we discussed", "step 1:", "then ignore")),
        ("adversarial_suffix", ("!!!", "adversarial suffix", "gcg", "optimized suffix")),
        ("output_manipulation", ("respond only with", "output format", "json only", "no refusal")),
        ("jailbreak", ("jailbreak", "hypothetical", "roleplay", "without restrictions", "uncensored")),
    ]
    for cat, needles in rules:
        if any(n in t for n in needles):
            return cat, False
    if source_hint in {"real_toxicity", "toxigen"}:
        return "social_engineering", True
    return "jailbreak", True


def write_jsonl(path: Path, rows: Iterable[dict]) -> int:
    n = 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            n += 1
    return n


def download_hf_file(repo_id: str, filename: str, dest: Path, repo_type: str = "dataset") -> Path:
    from huggingface_hub import hf_hub_download

    dest.parent.mkdir(parents=True, exist_ok=True)
    local = hf_hub_download(
        repo_id=repo_id,
        filename=filename,
        repo_type=repo_type,
        local_dir=str(dest.parent),
        local_dir_use_symlinks=False,
    )
    local_path = Path(local)
    # hf may nest; copy/move into dest if needed
    if local_path.resolve() != dest.resolve():
        if dest.exists():
            dest.unlink()
        shutil.copy2(local_path, dest)
    return dest


def gunzip_to(src: Path, dst: Path) -> Path:
    with gzip.open(src, "rb") as fin, dst.open("wb") as fout:
        shutil.copyfileobj(fin, fout)
    return dst


def load_jsonl(path: Path) -> Iterator[dict]:
    opener = gzip.open if path.suffix == ".gz" or path.name.endswith(".jsonl.gz") else open
    mode = "rt"
    with opener(path, mode, encoding="utf-8", errors="replace") as f:  # type: ignore[arg-type]
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def extract_anthropic_text(row: dict) -> Optional[str]:
    # Prefer human turns from transcript; fallback task_description
    transcript = row.get("transcript") or ""
    humans: List[str] = []
    # Anthropic format often embeds "Human:" / "Assistant:"
    parts = transcript.replace("\r\n", "\n").split("\n\n")
    buf: List[str] = []
    role = None
    for block in parts:
        if block.startswith("Human:"):
            if role == "Human" and buf:
                humans.append("\n".join(buf).strip())
            role = "Human"
            buf = [block[len("Human:") :].lstrip()]
        elif block.startswith("Assistant:"):
            if role == "Human" and buf:
                humans.append("\n".join(buf).strip())
            role = "Assistant"
            buf = []
        else:
            if role == "Human":
                buf.append(block)
    if role == "Human" and buf:
        humans.append("\n".join(buf).strip())
    if humans:
        # join multi-turn human pressure into one training attack text
        return "\n---\n".join(h for h in humans if h)
    td = (row.get("task_description") or "").strip()
    return td or None


def iter_anthropic_rows(raw_path: Path) -> Iterator[dict]:
    """Anthropic ships a JSON array that looks like broken jsonl — prefer HF datasets."""
    from datasets import load_dataset

    try:
        ds = load_dataset("Anthropic/hh-rlhf", data_dir="red-team-attempts", split="train")
        for row in ds:
            yield dict(row)
        return
    except Exception as e:
        print(f"[warn] datasets load failed ({e}); falling back to local parse")

    # Fallback: whole-file JSON array, or salvage line-ish objects
    text = raw_path.read_text(encoding="utf-8", errors="replace").strip()
    if text.startswith("["):
        data = json.loads(text)
        for row in data:
            yield row
        return
    # salvage: concatenate until balanced braces
    buf = ""
    depth = 0
    in_str = False
    esc = False
    for ch in text:
        buf += ch
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and buf.strip():
                obj = buf.strip().lstrip(",").strip()
                if obj.startswith("{"):
                    yield json.loads(obj)
                buf = ""


def normalize_anthropic(raw_path: Path) -> List[dict]:
    out: List[dict] = []
    for row in iter_anthropic_rows(raw_path):
        text = extract_anthropic_text(row)
        if not text:
            continue
        cat, needs = guess_category(text, "anthropic_redteam")
        # multi-turn transcripts
        if "\n---\n" in text:
            cat = "multi_turn"
            needs = False
        rid = f"anthropic_redteam:{hash16(text)}"
        out.append(
            {
                "id": rid,
                "source": "anthropic_redteam",
                "category": cat,
                "text": text,
                "success_signal": row.get("rating"),
                "raw_meta": {
                    "tags": row.get("tags"),
                    "min_harmlessness_score_transcript": row.get("min_harmlessness_score_transcript"),
                    "task_description": row.get("task_description"),
                    "needs_review": needs,
                },
            }
        )
    return out


def normalize_real_toxicity(raw_path: Path) -> List[dict]:
    out: List[dict] = []
    for row in load_jsonl(raw_path):
        prompt = row.get("prompt") or {}
        if isinstance(prompt, dict):
            text = (prompt.get("text") or "").strip()
            tox = prompt.get("toxicity")
        else:
            text = str(prompt).strip()
            tox = row.get("toxicity")
        if not text:
            continue
        # keep only higher-toxicity seeds — pressure set, not full benign
        try:
            tox_f = float(tox) if tox is not None else 0.0
        except (TypeError, ValueError):
            tox_f = 0.0
        if tox_f < 0.5:
            continue
        cat, needs = guess_category(text, "real_toxicity")
        out.append(
            {
                "id": f"real_toxicity:{hash16(text)}",
                "source": "real_toxicity",
                "category": cat,
                "text": text,
                "success_signal": tox_f,
                "raw_meta": {
                    "continuation": row.get("continuation"),
                    "needs_review": needs,
                },
            }
        )
    return out


def normalize_toxigen(raw_path: Path, max_rows: Optional[int] = None) -> List[dict]:
    out: List[dict] = []
    for i, row in enumerate(load_jsonl(raw_path)):
        if max_rows is not None and i >= max_rows:
            break
        text = (
            row.get("text")
            or row.get("generation")
            or row.get("prompt")
            or row.get("statement")
            or ""
        )
        if isinstance(text, dict):
            text = text.get("text") or ""
        text = str(text).strip()
        if not text:
            continue
        label = row.get("prompt_label") or row.get("label") or row.get("toxicity_ai") or row.get("hate")
        cat, needs = guess_category(text, "toxigen")
        out.append(
            {
                "id": f"toxigen:{hash16(text)}",
                "source": "toxigen",
                "category": cat,
                "text": text,
                "success_signal": label,
                "raw_meta": {
                    "target_group": row.get("target_group") or row.get("group"),
                    "needs_review": needs,
                },
            }
        )
    return out


def load_tabular_rows(raw_path: Path) -> List[Any]:
    """Load jsonl / json / parquet / csv into list of dicts or strings."""
    suffix = raw_path.suffix.lower()
    if suffix == ".parquet":
        import pandas as pd

        df = pd.read_parquet(raw_path)
        return df.to_dict(orient="records")
    if suffix == ".csv":
        import pandas as pd

        df = pd.read_csv(raw_path)
        return df.to_dict(orient="records")
    if suffix == ".json" and not raw_path.name.endswith(".jsonl"):
        data = json.loads(raw_path.read_text(encoding="utf-8", errors="replace"))
        if isinstance(data, dict):
            for key in ("data", "prompts", "examples", "items"):
                if isinstance(data.get(key), list):
                    data = data[key]
                    break
            else:
                data = [data]
        return list(data)
    return list(load_jsonl(raw_path))


def row_to_text_meta(row: Any) -> Tuple[str, Dict[str, Any]]:
    if isinstance(row, str):
        return row.strip(), {}
    text = (
        row.get("prompt")
        or row.get("text")
        or row.get("jailbreak")
        or row.get("attack")
        or row.get("goal")
        or row.get("query")
        or row.get("instruction")
        or ""
    )
    if isinstance(text, dict):
        text = text.get("text") or text.get("prompt") or ""
    text = str(text).strip()
    skip = {"prompt", "text", "jailbreak", "attack", "goal", "query", "instruction"}
    meta = {k: v for k, v in row.items() if k not in skip}
    # pandas / numpy scalars → plain python
    clean_meta: Dict[str, Any] = {}
    for k, v in meta.items():
        try:
            if hasattr(v, "item"):
                v = v.item()
        except Exception:
            pass
        if hasattr(v, "tolist"):
            try:
                v = v.tolist()
            except Exception:
                v = str(v)
        clean_meta[k] = v
    return text, clean_meta


def normalize_generic_jailbreak(raw_path: Path, source: str) -> List[dict]:
    out: List[dict] = []
    for row in load_tabular_rows(raw_path):
        text, meta = row_to_text_meta(row)
        if not text:
            continue
        cat, needs = guess_category(text, source)
        out.append(
            {
                "id": f"{source}:{hash16(text)}",
                "source": source,
                "category": cat,
                "text": text,
                "success_signal": meta.get("score") or meta.get("success") or meta.get("label"),
                "raw_meta": {**meta, "needs_review": needs},
            }
        )
    return out


def download_required() -> Dict[str, Any]:
    from datasets import load_dataset
    from huggingface_hub import hf_hub_download, list_repo_files

    info: Dict[str, Any] = {"sources": {}}

    # 1) Anthropic red-team
    dest_dir = INCOMING / "anthropic_redteam"
    dest_dir.mkdir(parents=True, exist_ok=True)
    gz = download_hf_file(
        "Anthropic/hh-rlhf",
        "red-team-attempts/red_team_attempts.jsonl.gz",
        dest_dir / "red_team_attempts.jsonl.gz",
    )
    jsonl = dest_dir / "red_team_attempts.jsonl"
    if not jsonl.exists():
        gunzip_to(gz, jsonl)
    info["sources"]["anthropic_redteam"] = {
        "repo": "Anthropic/hh-rlhf",
        "slice": "red-team-attempts",
        "files": [
            {"path": str(gz), "bytes": gz.stat().st_size, "sha256": sha256_file(gz)},
            {"path": str(jsonl), "bytes": jsonl.stat().st_size, "sha256": sha256_file(jsonl)},
        ],
    }
    enforce_budget("anthropic_redteam")

    # 2) RealToxicityPrompts
    dest_dir = INCOMING / "real_toxicity"
    dest_dir.mkdir(parents=True, exist_ok=True)
    prompts = download_hf_file(
        "allenai/real-toxicity-prompts",
        "prompts.jsonl",
        dest_dir / "prompts.jsonl",
    )
    info["sources"]["real_toxicity"] = {
        "repo": "allenai/real-toxicity-prompts",
        "slice": "prompts.jsonl",
        "files": [{"path": str(prompts), "bytes": prompts.stat().st_size, "sha256": sha256_file(prompts)}],
    }
    enforce_budget("real_toxicity")

    # 3) ToxiGen — prefer annotated / smaller files
    dest_dir = INCOMING / "toxigen"
    dest_dir.mkdir(parents=True, exist_ok=True)
    files = list_repo_files("toxigen/toxigen-data", repo_type="dataset")
    preferred = [
        f
        for f in files
        if f.endswith((".jsonl", ".json", ".parquet", ".csv", ".jsonl.gz"))
        and any(k in f.lower() for k in ("annotated", "human", "prompts", "toxigen"))
    ]
    # fallback: any reasonable tabular
    if not preferred:
        preferred = [f for f in files if f.endswith((".jsonl", ".parquet", ".csv", ".json"))]

    # rank small-ish first
    chosen: List[str] = []
    truncated = False
    sample_rows = None
    # Use datasets loader for the annotated split if available
    toxigen_out = dest_dir / "toxigen_export.jsonl"
    try:
        # common config names
        ds = None
        for conf in ("annotated", "train", None):
            try:
                if conf is None:
                    ds = load_dataset("toxigen/toxigen-data", split="train")
                else:
                    ds = load_dataset("toxigen/toxigen-data", conf, split="train")
                break
            except Exception:
                continue
        if ds is None:
            # last resort: first available
            ds_dict = load_dataset("toxigen/toxigen-data")
            split_name = list(ds_dict.keys())[0]
            ds = ds_dict[split_name]

        n = len(ds)
        if getattr(ds, "dataset_size", None) and ds.dataset_size and ds.dataset_size > TOXIGEN_SOFT_CAP:
            truncated = True
            sample_rows = TOXIGEN_SAMPLE_ROWS
        # also truncate by row count if huge
        if n > TOXIGEN_SAMPLE_ROWS * 2:
            # keep a stratified-ish head+tail mix without full shuffle cost
            truncated = True
            sample_rows = TOXIGEN_SAMPLE_ROWS
            idxs = list(range(0, n, max(1, n // TOXIGEN_SAMPLE_ROWS)))[:TOXIGEN_SAMPLE_ROWS]
            ds = ds.select(idxs)

        with toxigen_out.open("w", encoding="utf-8") as f:
            for row in ds:
                f.write(json.dumps(dict(row), ensure_ascii=False, default=str) + "\n")

        info["sources"]["toxigen"] = {
            "repo": "toxigen/toxigen-data",
            "slice": "export_jsonl",
            "truncated": truncated,
            "sample_rows": sample_rows or n,
            "files": [
                {
                    "path": str(toxigen_out),
                    "bytes": toxigen_out.stat().st_size,
                    "sha256": sha256_file(toxigen_out),
                }
            ],
            "repo_files_seen": preferred[:30],
        }
    except Exception as e:
        info["sources"]["toxigen"] = {"error": repr(e), "repo_files_seen": files[:50]}
        raise
    enforce_budget("toxigen")
    return info


def hf_search_shortlist() -> Tuple[List[dict], List[dict]]:
    """Return (accepted extras metadata, rejected notes)."""
    from huggingface_hub import HfApi, hf_hub_download, list_repo_files

    api = HfApi()
    queries = [
        "jailbreak prompts",
        "prompt injection",
        "adversarial attacks LLM",
        "red team dataset",
    ]
    preferred_ids = [
        "JailbreakBench/JBB-Behaviors",
        "deepset/prompt-injections",
        "walledai/PromptInject",
        "justinphan3110/harmful_harmless_instructions",
        "TrustAIRLab/in-the-wild-jailbreak-prompts",
        "rubend18/ChatGPT-Jailbreak-Prompts",
    ]
    rejected: List[dict] = []
    candidates: List[dict] = []

    seen = set()
    for q in queries:
        try:
            results = api.list_datasets(search=q, limit=15)
        except Exception as e:
            rejected.append({"query": q, "reason": f"search_failed: {e}"})
            continue
        for ds in results:
            rid = ds.id
            if rid in seen:
                continue
            seen.add(rid)
            # skip required already covered
            if rid in {"Anthropic/hh-rlhf", "allenai/real-toxicity-prompts", "toxigen/toxigen-data"}:
                rejected.append({"id": rid, "query": q, "reason": "already_required"})
                continue
            # skip huge model-like or irrelevant names
            low = rid.lower()
            if any(x in low for x in ("image", "audio", "video", "protein", "genome")):
                rejected.append({"id": rid, "query": q, "reason": "wrong_modality"})
                continue
            candidates.append({"id": rid, "query": q, "downloads": getattr(ds, "downloads", None)})

    # prefer known good ids first
    ranked: List[dict] = []
    for pid in preferred_ids:
        for c in candidates:
            if c["id"] == pid or c["id"].lower().endswith(pid.lower().split("/")[-1].lower()):
                ranked.append(c)
    for c in candidates:
        if c not in ranked:
            ranked.append(c)

    accepted: List[dict] = []
    seen_sha: set[str] = set()
    extras_dir = INCOMING / "extras"
    if extras_dir.exists():
        shutil.rmtree(extras_dir)
    extras_dir.mkdir(parents=True, exist_ok=True)

    for c in ranked:
        if len(accepted) >= 3:
            rejected.append({**c, "reason": "over_max_extras"})
            continue
        rid = c["id"]
        try:
            files = list_repo_files(rid, repo_type="dataset")
        except Exception as e:
            rejected.append({**c, "reason": f"list_failed: {e}"})
            continue
        data_files = [
            f
            for f in files
            if f.endswith((".jsonl", ".json", ".parquet", ".jsonl.gz", ".csv"))
            and "readme" not in f.lower()
        ]
        if not data_files:
            rejected.append({**c, "reason": "no_json_parquet_csv"})
            continue

        # Prefer train/full over tiny test shards; jsonl before parquet
        def file_rank(name: str) -> tuple:
            low = name.lower()
            return (
                0 if "train" in low else 1 if "test" in low or "val" in low else 2,
                0 if low.endswith((".jsonl", ".json", ".jsonl.gz")) else 1,
                len(name),
            )

        data_files_sorted = sorted(data_files, key=file_rank)
        picked = None
        for fname in data_files_sorted[:12]:
            try:
                local = hf_hub_download(repo_id=rid, filename=fname, repo_type="dataset")
                sz = Path(local).stat().st_size
                if sz > EXTRA_MAX_BYTES:
                    rejected.append({**c, "file": fname, "reason": f"file_too_big:{sz}"})
                    continue
                digest = sha256_file(Path(local))
                if digest in seen_sha:
                    rejected.append({**c, "file": fname, "reason": "duplicate_sha256_skip"})
                    continue
                # accept
                safe_name = rid.replace("/", "__") + "__" + Path(fname).name
                dest = extras_dir / safe_name
                shutil.copy2(local, dest)
                # decompress gz into sibling jsonl if needed
                if dest.name.endswith(".gz"):
                    out = dest.with_suffix("")  # strip .gz
                    if not str(out).endswith(".jsonl") and dest.name.endswith(".jsonl.gz"):
                        out = Path(str(dest)[:-3])
                    gunzip_to(dest, out)
                    picked = out
                else:
                    picked = dest
                seen_sha.add(digest)
                accepted.append(
                    {
                        "id": rid,
                        "query": c.get("query"),
                        "file": fname,
                        "path": str(picked),
                        "bytes": picked.stat().st_size,
                        "sha256": digest,
                        "source_key": rid.lower().replace("/", "__").replace("-", "_")[:60],
                    }
                )
                enforce_budget(f"extra:{rid}")
                break
            except Exception as e:
                rejected.append({**c, "file": fname, "reason": f"download_failed: {e}"})
                continue
        if picked is None and not any(a["id"] == rid for a in accepted):
            rejected.append({**c, "reason": "no_suitable_file_under_400mb"})

    # also mark preferred not found
    found_ids = {a["id"] for a in accepted} | {r.get("id") for r in rejected}
    for pid in preferred_ids:
        if pid not in found_ids and not any(pid.split("/")[-1].lower() in (x or "").lower() for x in found_ids):
            rejected.append({"id": pid, "reason": "preferred_not_in_search_or_unavailable"})

    return accepted, rejected


def main() -> int:
    t0 = time.time()
    ROOT.mkdir(parents=True, exist_ok=True)
    INCOMING.mkdir(parents=True, exist_ok=True)
    NORMALIZED.mkdir(parents=True, exist_ok=True)

    print("== download required ==")
    info = download_required()

    print("== hf search + extras ==")
    accepted, rejected = hf_search_shortlist()
    info["extras"] = accepted

    print("== normalize ==")
    rows: List[dict] = []
    anth = INCOMING / "anthropic_redteam" / "red_team_attempts.jsonl"
    rows.extend(normalize_anthropic(anth))
    rtp = INCOMING / "real_toxicity" / "prompts.jsonl"
    rows.extend(normalize_real_toxicity(rtp))
    tox = INCOMING / "toxigen" / "toxigen_export.jsonl"
    if tox.exists():
        # if export huge, sample
        max_rows = None
        if tox.stat().st_size > TOXIGEN_SOFT_CAP:
            max_rows = TOXIGEN_SAMPLE_ROWS
            info["sources"]["toxigen"]["truncated"] = True
            info["sources"]["toxigen"]["sample_rows"] = max_rows
        rows.extend(normalize_toxigen(tox, max_rows=max_rows))

    for extra in accepted:
        src_key = extra["source_key"]
        path = Path(extra["path"])
        try:
            rows.extend(normalize_generic_jailbreak(path, src_key))
        except Exception as e:
            rejected.append({**extra, "reason": f"normalize_failed: {e}"})

    # dedupe by id
    dedup: Dict[str, dict] = {}
    for r in rows:
        dedup[r["id"]] = r
    final = list(dedup.values())
    out_path = NORMALIZED / "attacks.jsonl"
    n = write_jsonl(out_path, final)

    cat_counts = Counter(r["category"] for r in final)
    src_counts = Counter(r["source"] for r in final)

    info["normalized"] = {
        "path": str(out_path),
        "rows": n,
        "bytes": out_path.stat().st_size,
        "sha256": sha256_file(out_path),
        "by_category": dict(sorted(cat_counts.items())),
        "by_source": dict(sorted(src_counts.items())),
    }
    info["budget"] = {
        "limit_bytes": BUDGET_BYTES,
        "used_bytes": dir_size(ROOT),
        "used_mb": round(dir_size(ROOT) / 1024**2, 2),
    }
    info["elapsed_sec"] = round(time.time() - t0, 2)
    info["policy"] = {
        "formats": [".jsonl", ".json", ".parquet", ".jsonl.gz"],
        "excluded": ["exploitdb", "crypto", "survival", "fires", "full_hh_rlhf"],
        "quarantine": "_incoming",
    }

    MANIFEST_PATH.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")

    # REJECTED.md
    lines = [
        "# REJECTED / shortlist notes — attacker base",
        "",
        "HF queries: `jailbreak prompts`, `prompt injection`, `adversarial attacks LLM`, `red team dataset`.",
        "",
        "## Accepted extras",
        "",
    ]
    if accepted:
        for a in accepted:
            lines.append(f"- `{a['id']}` ← query `{a.get('query')}` file `{a.get('file')}` ({a['bytes']} bytes)")
    else:
        lines.append("- _(none)_")
    lines += ["", "## Rejected / skipped", ""]
    for r in rejected[:200]:
        lines.append(
            f"- `{r.get('id', '?')}` — {r.get('reason')} (query={r.get('query')}, file={r.get('file')})"
        )
    if len(rejected) > 200:
        lines.append(f"- ... and {len(rejected) - 200} more")
    lines += [
        "",
        "## Explicitly out of scope",
        "",
        "- Exploit-DB / exploitdb clone",
        "- Crypto / survival / fire reference corpora",
        "- Full `Anthropic/hh-rlhf` (only `red-team-attempts`)",
        "",
    ]
    REJECTED_PATH.write_text("\n".join(lines), encoding="utf-8")

    print("== done ==")
    print(f"rows={n}")
    print("by_category=", dict(cat_counts))
    print("by_source=", dict(src_counts))
    print(f"used_mb={info['budget']['used_mb']}")
    print(f"manifest={MANIFEST_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
