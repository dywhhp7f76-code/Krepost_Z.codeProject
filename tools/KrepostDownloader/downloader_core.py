"""HTTP download engine with resume, retries, and progress callbacks.

Uses Range requests + .part files so unstable networks do not lose progress.
Stdlib only (urllib) — no pip deps for the core.
"""
from __future__ import annotations

import os
import re
import tempfile
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import unquote, urlparse


class JobState(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    DONE = "done"
    ERROR = "error"
    CANCELLED = "cancelled"


ProgressCb = Callable[["DownloadJob"], None]


@dataclass
class DownloadJob:
    url: str
    dest_dir: Path
    filename: Optional[str] = None
    state: JobState = JobState.QUEUED
    bytes_done: int = 0
    bytes_total: Optional[int] = None  # None = unknown
    speed_bps: float = 0.0
    error: str = ""
    id: str = field(default_factory=lambda: f"{time.time_ns()}")
    _stop: threading.Event = field(default_factory=threading.Event, repr=False)
    _pause: threading.Event = field(default_factory=threading.Event, repr=False)

    def part_path(self) -> Path:
        name = self.resolved_name()
        return self.dest_dir / f"{name}.part"

    def final_path(self) -> Path:
        return self.dest_dir / self.resolved_name()

    def resolved_name(self) -> str:
        if self.filename:
            return self.filename
        path = unquote(urlparse(self.url).path)
        base = Path(path).name or "download.bin"
        return _safe_filename(base)

    @property
    def progress_pct(self) -> Optional[float]:
        if not self.bytes_total or self.bytes_total <= 0:
            return None
        return min(100.0, 100.0 * self.bytes_done / self.bytes_total)


def _safe_filename(name: str) -> str:
    name = name.strip().replace("\x00", "")
    # Drop any path components (../../etc/passwd → passwd)
    name = Path(name).name
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    name = name.replace("..", "_")
    return name[:200] or "download.bin"


def _filename_from_headers(headers, fallback: str) -> str:
    cd = headers.get("Content-Disposition") or headers.get("content-disposition") or ""
    m = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)"?', cd, re.I)
    if m:
        return _safe_filename(unquote(m.group(1).strip()))
    return fallback


class DownloadManager:
    """Queue of resumable downloads; each job runs on its own thread."""

    def __init__(
        self,
        on_progress: Optional[ProgressCb] = None,
        max_retries: int = 50,
        chunk_size: int = 256 * 1024,
        user_agent: str = (
            "KrepostDownloader/1.0 (+https://github.com/dywhhp7f76-code/Krepost_Z.codeProject)"
        ),
    ):
        self.on_progress = on_progress
        self.max_retries = max_retries
        self.chunk_size = chunk_size
        self.user_agent = user_agent
        self._jobs: dict[str, DownloadJob] = {}
        self._lock = threading.Lock()

    def jobs(self) -> list[DownloadJob]:
        with self._lock:
            return list(self._jobs.values())

    def add(self, url: str, dest_dir: str | Path, filename: Optional[str] = None) -> DownloadJob:
        url = (url or "").strip()
        if not url.startswith(("http://", "https://")):
            raise ValueError("Нужен http:// или https:// URL")
        dest = Path(dest_dir).expanduser().resolve()
        dest.mkdir(parents=True, exist_ok=True)
        job = DownloadJob(url=url, dest_dir=dest, filename=filename)
        with self._lock:
            self._jobs[job.id] = job
        self._emit(job)
        return job

    def start(self, job_id: str) -> None:
        job = self._get(job_id)
        if job.state in (JobState.RUNNING, JobState.DONE):
            return
        job._stop.clear()
        job._pause.clear()
        job.state = JobState.RUNNING
        job.error = ""
        self._emit(job)
        t = threading.Thread(target=self._run_job, args=(job,), daemon=True)
        t.start()

    def pause(self, job_id: str) -> None:
        job = self._get(job_id)
        if job.state == JobState.RUNNING:
            job._pause.set()
            job.state = JobState.PAUSED
            self._emit(job)

    def resume(self, job_id: str) -> None:
        job = self._get(job_id)
        if job.state in (JobState.PAUSED, JobState.ERROR, JobState.QUEUED):
            self.start(job_id)

    def cancel(self, job_id: str) -> None:
        job = self._get(job_id)
        job._stop.set()
        job._pause.clear()
        job.state = JobState.CANCELLED
        self._emit(job)

    def _get(self, job_id: str) -> DownloadJob:
        with self._lock:
            if job_id not in self._jobs:
                raise KeyError(job_id)
            return self._jobs[job_id]

    def _emit(self, job: DownloadJob) -> None:
        if self.on_progress:
            try:
                self.on_progress(job)
            except Exception:
                pass

    def _run_job(self, job: DownloadJob) -> None:
        retries = 0
        while not job._stop.is_set():
            if job._pause.is_set():
                job.state = JobState.PAUSED
                self._emit(job)
                return
            try:
                self._download_once(job)
                if job.state == JobState.DONE:
                    return
            except Exception as e:
                retries += 1
                job.error = str(e)
                job.speed_bps = 0.0
                if retries > self.max_retries or job._stop.is_set():
                    job.state = JobState.ERROR
                    self._emit(job)
                    return
                # Unstable net: wait and continue from .part — do not cancel
                job.state = JobState.RUNNING
                job.error = f"обрыв, повтор {retries}/{self.max_retries}: {e}"
                self._emit(job)
                time.sleep(min(30.0, 1.5 * retries))

    def _download_once(self, job: DownloadJob) -> None:
        part = job.part_path()
        existing = part.stat().st_size if part.exists() else 0
        job.bytes_done = existing

        headers = {"User-Agent": self.user_agent, "Accept": "*/*"}
        if existing > 0:
            headers["Range"] = f"bytes={existing}-"

        req = urllib.request.Request(job.url, headers=headers, method="GET")
        try:
            resp = urllib.request.urlopen(req, timeout=60)
        except urllib.error.HTTPError as e:
            if e.code == 416 and existing > 0:
                # Already complete according to server
                self._finalize(job, part)
                return
            raise

        with resp:
            status = getattr(resp, "status", None) or resp.getcode()
            hdrs = resp.headers
            if not job.filename:
                job.filename = _filename_from_headers(hdrs, job.resolved_name())

            # If server ignored Range and sent 200, restart file
            if existing > 0 and status == 200:
                existing = 0
                job.bytes_done = 0
                part.write_bytes(b"")

            total_from_len = _parse_int(hdrs.get("Content-Length"))
            content_range = hdrs.get("Content-Range") or ""
            if content_range:
                # bytes start-end/total
                m = re.search(r"/(\d+)\s*$", content_range)
                if m:
                    job.bytes_total = int(m.group(1))
                elif total_from_len is not None:
                    job.bytes_total = existing + total_from_len
            elif status == 200 and total_from_len is not None:
                job.bytes_total = total_from_len
            elif total_from_len is not None and existing > 0:
                job.bytes_total = existing + total_from_len

            mode = "ab" if existing > 0 and status == 206 else "wb"
            if mode == "wb" and existing == 0 and part.exists():
                part.unlink(missing_ok=True)

            last_t = time.monotonic()
            last_b = job.bytes_done
            with open(part, mode) as out:
                while not job._stop.is_set():
                    if job._pause.is_set():
                        job.state = JobState.PAUSED
                        job.speed_bps = 0.0
                        self._emit(job)
                        return
                    chunk = resp.read(self.chunk_size)
                    if not chunk:
                        break
                    out.write(chunk)
                    job.bytes_done += len(chunk)
                    now = time.monotonic()
                    dt = now - last_t
                    if dt >= 0.25:
                        job.speed_bps = (job.bytes_done - last_b) / dt
                        last_t = now
                        last_b = job.bytes_done
                        self._emit(job)

            if job._stop.is_set():
                job.state = JobState.CANCELLED
                self._emit(job)
                return
            if job._pause.is_set():
                return

            self._finalize(job, part)

    def _finalize(self, job: DownloadJob, part: Path) -> None:
        final = job.final_path()
        if final.exists():
            # Avoid overwrite: add suffix
            stem, suf = final.stem, final.suffix
            n = 1
            while final.exists():
                final = job.dest_dir / f"{stem} ({n}){suf}"
                n += 1
        # Atomic-ish replace
        os.replace(part, final)
        job.filename = final.name
        job.bytes_done = final.stat().st_size
        if job.bytes_total is None:
            job.bytes_total = job.bytes_done
        job.speed_bps = 0.0
        job.state = JobState.DONE
        job.error = ""
        self._emit(job)


def _parse_int(v: Optional[str]) -> Optional[int]:
    if v is None:
        return None
    try:
        return int(v)
    except ValueError:
        return None


def looks_like_url(text: str) -> bool:
    t = (text or "").strip()
    return t.startswith("http://") or t.startswith("https://")
