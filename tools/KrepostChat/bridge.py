"""Tailscale / LAN bridge helpers for Krepost Chat.

Threat model: no public port-forward. Only devices in the operator Tailscale
account can reach Studio. Password auth still required on the API.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

CONFIG_DIR = Path.home() / ".krepost"
CONFIG_PATH = CONFIG_DIR / "chat_bridge.json"
DEFAULT_PORT = int(os.environ.get("KREPOST_API_PORT", "8000"))


def _run(cmd: List[str], timeout: float = 8.0) -> str:
    try:
        r = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return (r.stdout or "").strip()
    except Exception:
        return ""


def tailscale_bin() -> Optional[str]:
    for c in (
        "/Applications/Tailscale.app/Contents/MacOS/Tailscale",
        "/usr/local/bin/tailscale",
        "/opt/homebrew/bin/tailscale",
        shutil.which("tailscale") or "",
    ):
        if c and Path(c).exists():
            return c
    return None


def self_tailscale_ip() -> Optional[str]:
    bin_ = tailscale_bin()
    if not bin_:
        return None
    out = _run([bin_, "ip", "-4"])
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("100."):
            return line
    return None


def status_json() -> Dict[str, Any]:
    bin_ = tailscale_bin()
    if not bin_:
        return {}
    raw = _run([bin_, "status", "--json"], timeout=12)
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def list_peers() -> List[Dict[str, str]]:
    """Peers with Tailscale IPv4 — for picking Studio."""
    st = status_json()
    peers: List[Dict[str, str]] = []
    # Self
    self_name = (st.get("Self") or {}).get("HostName") or ""
    self_ips = (st.get("Self") or {}).get("TailscaleIPs") or []
    for ip in self_ips:
        if isinstance(ip, str) and ip.startswith("100."):
            peers.append({"hostname": self_name or "self", "ip": ip, "online": "true"})
    peer_map = st.get("Peer") or {}
    for _id, p in peer_map.items():
        if not isinstance(p, dict):
            continue
        host = p.get("HostName") or p.get("DNSName") or _id
        online = bool(p.get("Online", False))
        for ip in p.get("TailscaleIPs") or []:
            if isinstance(ip, str) and ip.startswith("100."):
                peers.append(
                    {
                        "hostname": str(host).split(".")[0],
                        "ip": ip,
                        "online": "true" if online else "false",
                    }
                )
    return peers


def guess_studio_peer(
    prefer_names: Optional[List[str]] = None,
) -> Optional[Dict[str, str]]:
    prefer = [n.lower() for n in (prefer_names or ["studio", "krepost", "mac-studio", "macstudio"])]
    peers = [p for p in list_peers() if p.get("online") == "true"]
    # Prefer configured
    cfg = load_config()
    saved = cfg.get("studio_tailscale_ip")
    if saved:
        for p in peers:
            if p["ip"] == saved:
                return p
    for p in peers:
        h = p.get("hostname", "").lower()
        if any(x in h for x in prefer):
            return p
    # Fallback: first online peer that is not self
    me = self_tailscale_ip()
    for p in peers:
        if p["ip"] != me:
            return p
    return None


def url_for_host(host: str, port: int = DEFAULT_PORT) -> str:
    host = host.strip().rstrip("/")
    if host.startswith("http://") or host.startswith("https://"):
        return host
    return f"http://{host}:{port}"


def load_config() -> Dict[str, Any]:
    if not CONFIG_PATH.is_file():
        return {}
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_config(data: Dict[str, Any]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    cur = load_config()
    cur.update(data)
    CONFIG_PATH.write_text(json.dumps(cur, ensure_ascii=False, indent=2), encoding="utf-8")


def default_api_url() -> str:
    """Env > saved Tailscale > LAN guess > localhost."""
    env = os.environ.get("KREPOST_CHAT_URL", "").strip()
    if env:
        return env
    cfg = load_config()
    if cfg.get("studio_url"):
        return str(cfg["studio_url"])
    if cfg.get("studio_tailscale_ip"):
        return url_for_host(str(cfg["studio_tailscale_ip"]))
    peer = guess_studio_peer()
    if peer:
        return url_for_host(peer["ip"])
    lan = os.environ.get("KREPOST_LAN_URL", "http://10.0.0.1:8000")
    return lan


def bridge_report() -> str:
    lines = []
    bin_ = tailscale_bin()
    if not bin_:
        lines.append("Tailscale: не установлен (скачай с https://tailscale.com/download)")
        return "\n".join(lines)
    lines.append(f"Tailscale: {bin_}")
    me = self_tailscale_ip()
    lines.append(f"Этот Mac (Tailscale IP): {me or '—'}")
    peers = list_peers()
    if not peers:
        lines.append("Пиры: нет (войди в тот же аккаунт Tailscale, что на Studio)")
    else:
        lines.append("Пиры:")
        for p in peers:
            mark = "✓" if p["online"] == "true" else "✗"
            lines.append(f"  {mark} {p['hostname']}  {p['ip']}")
    studio = guess_studio_peer()
    if studio:
        lines.append(f"Угаданный Studio: {studio['hostname']} → {url_for_host(studio['ip'])}")
    else:
        lines.append("Studio не найден автоматически — впиши 100.x.x.x вручную")
    return "\n".join(lines)
