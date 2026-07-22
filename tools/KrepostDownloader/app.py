#!/usr/bin/env python3
"""KrepostDownloader — GUI download manager with resume (no terminal required).

Double-click KrepostDownloader.app on Mac, or run:
  python3 app.py
  python3 app.py 'https://example.com/file.gguf'
"""
from __future__ import annotations

import queue
import sys
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Optional

from downloader_core import DownloadJob, DownloadManager, JobState, looks_like_url

APP_DIR = Path(__file__).resolve().parent
DEFAULT_DEST = Path.home() / "Downloads"


def _fmt_bytes(n: Optional[float]) -> str:
    if n is None:
        return "?"
    n = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024:
            return f"{n:.1f} {unit}" if unit != "B" else f"{int(n)} B"
        n /= 1024
    return f"{n:.1f} PB"


def _fmt_speed(bps: float) -> str:
    if bps <= 0:
        return "—"
    return f"{_fmt_bytes(bps)}/s"


class App(tk.Tk):
    def __init__(self, initial_urls: Optional[list[str]] = None):
        super().__init__()
        self.title("Krepost Downloader")
        self.geometry("780x520")
        self.minsize(640, 420)
        self.configure(bg="#E8EEF2")

        self._ui_q: queue.Queue = queue.Queue()
        self.dest_var = tk.StringVar(value=str(DEFAULT_DEST))
        self.url_var = tk.StringVar()
        self._row_widgets: dict[str, dict] = {}

        self.manager = DownloadManager(on_progress=self._on_progress)

        self._build_style()
        self._build_ui()
        self._poll_ui()
        self._bind_shortcuts()

        for u in initial_urls or []:
            if looks_like_url(u):
                self._enqueue(u, auto_start=True)

        # Accept drops of text URLs on the window (best-effort)
        self._setup_drop()

    def _build_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("aqua" if sys.platform == "darwin" else "clam")
        except tk.TclError:
            pass
        style.configure("Title.TLabel", font=("Avenir Next", 22, "bold"), background="#E8EEF2", foreground="#0F2A3D")
        style.configure("Sub.TLabel", font=("Avenir Next", 11), background="#E8EEF2", foreground="#3D5A6C")
        style.configure("Card.TFrame", background="#F7FAFC")
        style.configure("TFrame", background="#E8EEF2")
        style.configure("TLabel", background="#E8EEF2", foreground="#0F2A3D", font=("Avenir Next", 11))
        style.configure("Accent.TButton", font=("Avenir Next", 12, "bold"))

    def _build_ui(self) -> None:
        pad = {"padx": 16, "pady": 8}
        head = ttk.Frame(self)
        head.pack(fill="x", **pad)
        ttk.Label(head, text="Krepost Downloader", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            head,
            text="Докачка при обрыве сети · URL · вставка · перетаскивание ссылки",
            style="Sub.TLabel",
        ).pack(anchor="w")

        card = ttk.Frame(self, style="Card.TFrame")
        card.pack(fill="x", padx=16, pady=4)

        row1 = ttk.Frame(card, style="Card.TFrame")
        row1.pack(fill="x", padx=12, pady=(12, 4))
        ttk.Label(row1, text="Ссылка", background="#F7FAFC").pack(side="left")
        url_entry = ttk.Entry(row1, textvariable=self.url_var, font=("Menlo", 12))
        url_entry.pack(side="left", fill="x", expand=True, padx=8)
        url_entry.focus_set()
        ttk.Button(row1, text="Вставить", command=self._paste_url).pack(side="left", padx=2)
        ttk.Button(row1, text="Скачать", style="Accent.TButton", command=self._add_from_field).pack(side="left", padx=2)

        row2 = ttk.Frame(card, style="Card.TFrame")
        row2.pack(fill="x", padx=12, pady=(4, 12))
        ttk.Label(row2, text="Папка", background="#F7FAFC").pack(side="left")
        ttk.Entry(row2, textvariable=self.dest_var, font=("Avenir Next", 11)).pack(
            side="left", fill="x", expand=True, padx=8
        )
        ttk.Button(row2, text="Выбрать…", command=self._pick_dest).pack(side="left")

        hint = ttk.Label(
            self,
            text="Обрыв интернета не отменяет загрузку — программа сама продолжит с .part файла.",
            style="Sub.TLabel",
        )
        hint.pack(anchor="w", padx=16)

        list_frame = ttk.Frame(self)
        list_frame.pack(fill="both", expand=True, padx=16, pady=8)

        cols = ("name", "progress", "speed", "status")
        self.tree = ttk.Treeview(
            list_frame,
            columns=cols,
            show="headings",
            selectmode="browse",
            height=12,
        )
        self.tree.heading("name", text="Файл")
        self.tree.heading("progress", text="Прогресс")
        self.tree.heading("speed", text="Скорость")
        self.tree.heading("status", text="Статус")
        self.tree.column("name", width=280, anchor="w")
        self.tree.column("progress", width=160, anchor="w")
        self.tree.column("speed", width=100, anchor="center")
        self.tree.column("status", width=180, anchor="w")
        scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        btns = ttk.Frame(self)
        btns.pack(fill="x", padx=16, pady=(0, 12))
        ttk.Button(btns, text="Пауза", command=self._pause_sel).pack(side="left", padx=2)
        ttk.Button(btns, text="Продолжить", command=self._resume_sel).pack(side="left", padx=2)
        ttk.Button(btns, text="Отмена", command=self._cancel_sel).pack(side="left", padx=2)
        ttk.Button(btns, text="Открыть папку", command=self._open_dest).pack(side="right", padx=2)

    def _bind_shortcuts(self) -> None:
        self.bind("<Command-v>", lambda e: self._paste_url())
        self.bind("<Control-v>", lambda e: self._paste_url())
        self.bind("<Return>", lambda e: self._add_from_field())
        self.bind("<Command-l>", lambda e: self.focus_get())

    def _setup_drop(self) -> None:
        """Best-effort: tkinterdnd2 if installed; else ignore."""
        try:
            from tkinterdnd2 import DND_TEXT, DND_FILES, TkinterDnD  # type: ignore

            # Re-init not possible; register on self if mixin available
            if hasattr(self, "drop_target_register"):
                self.drop_target_register(DND_TEXT, DND_FILES)
                self.dnd_bind("<<Drop>>", self._on_drop)
        except Exception:
            # Fallback: poll clipboard for new http URLs when window focused
            self._last_clip = ""
            self.after(1500, self._watch_clipboard)

    def _watch_clipboard(self) -> None:
        try:
            clip = self.clipboard_get().strip()
            if (
                clip
                and clip != getattr(self, "_last_clip", "")
                and looks_like_url(clip)
                and self.focus_displayof() is not None
            ):
                self._last_clip = clip
                # Only prefill field — don't auto-download from silent clipboard
                if not self.url_var.get().strip():
                    self.url_var.set(clip)
        except tk.TclError:
            pass
        self.after(2000, self._watch_clipboard)

    def _on_drop(self, event) -> None:
        data = (event.data or "").strip().strip("{}")
        for line in data.replace("\r", "\n").split("\n"):
            line = line.strip()
            if looks_like_url(line):
                self._enqueue(line, auto_start=True)

    def _paste_url(self) -> None:
        try:
            text = self.clipboard_get().strip()
        except tk.TclError:
            return
        if looks_like_url(text):
            self.url_var.set(text)
        else:
            messagebox.showinfo("Вставка", "В буфере нет http(s) ссылки.")

    def _pick_dest(self) -> None:
        path = filedialog.askdirectory(initialdir=self.dest_var.get() or str(DEFAULT_DEST))
        if path:
            self.dest_var.set(path)

    def _add_from_field(self) -> None:
        url = self.url_var.get().strip()
        if not looks_like_url(url):
            messagebox.showwarning("URL", "Вставьте ссылку вида https://…")
            return
        self._enqueue(url, auto_start=True)
        self.url_var.set("")

    def _enqueue(self, url: str, auto_start: bool = True) -> None:
        try:
            job = self.manager.add(url, self.dest_var.get())
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))
            return
        self._ensure_row(job)
        if auto_start:
            self.manager.start(job.id)

    def _selected_job_id(self) -> Optional[str]:
        sel = self.tree.selection()
        if not sel:
            return None
        return sel[0]

    def _pause_sel(self) -> None:
        jid = self._selected_job_id()
        if jid:
            self.manager.pause(jid)

    def _resume_sel(self) -> None:
        jid = self._selected_job_id()
        if jid:
            self.manager.resume(jid)

    def _cancel_sel(self) -> None:
        jid = self._selected_job_id()
        if jid:
            self.manager.cancel(jid)

    def _open_dest(self) -> None:
        path = Path(self.dest_var.get())
        path.mkdir(parents=True, exist_ok=True)
        if sys.platform == "darwin":
            import subprocess

            subprocess.Popen(["open", str(path)])
        elif sys.platform.startswith("win"):
            import os

            os.startfile(str(path))  # type: ignore
        else:
            webbrowser.open(path.as_uri())

    def _on_progress(self, job: DownloadJob) -> None:
        self._ui_q.put(job)

    def _poll_ui(self) -> None:
        try:
            while True:
                job = self._ui_q.get_nowait()
                self._ensure_row(job)
                self._update_row(job)
        except queue.Empty:
            pass
        self.after(200, self._poll_ui)

    def _ensure_row(self, job: DownloadJob) -> None:
        if self.tree.exists(job.id):
            return
        self.tree.insert(
            "",
            "end",
            iid=job.id,
            values=(job.resolved_name(), "0%", "—", job.state.value),
        )

    def _update_row(self, job: DownloadJob) -> None:
        if not self.tree.exists(job.id):
            self._ensure_row(job)
        pct = job.progress_pct
        if pct is not None:
            prog = f"{pct:.1f}%  ({_fmt_bytes(job.bytes_done)} / {_fmt_bytes(job.bytes_total)})"
        else:
            prog = f"{_fmt_bytes(job.bytes_done)} / ?"
        status = job.state.value
        if job.state == JobState.ERROR:
            status = f"ошибка: {job.error[:60]}"
        elif job.state == JobState.RUNNING and job.error:
            status = job.error[:70]
        elif job.state == JobState.DONE:
            status = "готово"
        elif job.state == JobState.PAUSED:
            status = "пауза (можно продолжить)"
        self.tree.item(
            job.id,
            values=(job.resolved_name(), prog, _fmt_speed(job.speed_bps), status),
        )


def main() -> None:
    urls = [a for a in sys.argv[1:] if looks_like_url(a)]
    # Also accept file:// lists from some browsers (ignore non-http)
    app = App(initial_urls=urls)
    app.mainloop()


if __name__ == "__main__":
    main()
