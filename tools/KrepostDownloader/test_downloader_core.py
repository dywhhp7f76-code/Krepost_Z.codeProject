"""Unit tests for resume helpers (no tkinter)."""
from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from downloader_core import DownloadManager, JobState, _safe_filename, looks_like_url


def test_safe_filename():
    assert ".." not in _safe_filename("../../etc/passwd")
    assert _safe_filename('a<b>.gguf') == "a_b_.gguf"


def test_looks_like_url():
    assert looks_like_url("https://hf.co/x.gguf")
    assert not looks_like_url("ftp://x")


class _Handler(BaseHTTPRequestHandler):
    DATA = b"ABCDEFGHIJ" * 1000  # 10_000 bytes

    def log_message(self, *args):
        pass

    def do_GET(self):
        data = self.DATA
        range_h = self.headers.get("Range")
        if range_h and range_h.startswith("bytes="):
            start = int(range_h.split("=")[1].split("-")[0])
            chunk = data[start:]
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{len(data)-1}/{len(data)}")
            self.send_header("Content-Length", str(len(chunk)))
            self.send_header("Accept-Ranges", "bytes")
            self.end_headers()
            self.wfile.write(chunk)
        else:
            self.send_response(200)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Disposition", 'attachment; filename="blob.bin"')
            self.end_headers()
            self.wfile.write(data)


@pytest.fixture()
def http_server():
    server = HTTPServer(("127.0.0.1", 0), _Handler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    port = server.server_address[1]
    yield f"http://127.0.0.1:{port}/file.bin"
    server.shutdown()


def test_full_download(http_server, tmp_path: Path):
    done = threading.Event()
    states = []

    def on_p(job):
        states.append(job.state)
        if job.state in (JobState.DONE, JobState.ERROR):
            done.set()

    mgr = DownloadManager(on_progress=on_p, max_retries=3)
    job = mgr.add(http_server, tmp_path)
    mgr.start(job.id)
    assert done.wait(10)
    final = tmp_path / "blob.bin"
    assert final.exists()
    assert final.stat().st_size == 10_000
    assert JobState.DONE in states


def test_resume_from_part(http_server, tmp_path: Path):
    # Pre-create partial file (first 3000 bytes)
    part = tmp_path / "blob.bin.part"
    part.write_bytes(_Handler.DATA[:3000])

    done = threading.Event()

    def on_p(job):
        if job.state in (JobState.DONE, JobState.ERROR):
            done.set()

    mgr = DownloadManager(on_progress=on_p, max_retries=3)
    job = mgr.add(http_server, tmp_path, filename="blob.bin")
    mgr.start(job.id)
    assert done.wait(10)
    assert (tmp_path / "blob.bin").read_bytes() == _Handler.DATA
