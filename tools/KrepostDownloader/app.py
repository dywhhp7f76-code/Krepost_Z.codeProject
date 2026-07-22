#!/usr/bin/env python3
"""KrepostDownloader — GUI download manager with resume (no terminal required).

macOS: avoids ttk 'aqua' + custom colors (blank dark window in Dark Mode).
Uses clam theme + explicit colors so controls stay visible.
"""
from __future__ import annotations

import os
import queue
import sys
import traceback
import webbrowser
from pathlib import Path
from tkinter import (
    BOTH,
    END,
    LEFT,
    RIGHT,
    X,
    Y,
    BooleanVar,
    Button,
    Entry,
    Frame,
    Label,
    Scrollbar,
    StringVar,
    Tk,
    filedialog,
    messagebox,
    ttk,
)
from typing import Optional

# Ensure sibling imports work when launched from .app Resources
_APP_DIR = Path(__file__).resolve().parent
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

from downloader_core import DownloadJob, DownloadManager, JobState, looks_like_url

DEFAULT_DEST = Path.home() / "Downloads"
LOG_PATH = Path.home() / "Library" / "Logs" / "KrepostDownloader.log"

# Light palette — forced, independent of system Dark Mode
BG = "#E8EEF2"
CARD = "#F4F7FA"
FG = "#0F2A3D"
MUTED = "#3D5A6C"
ACCENT = "#0B6E4F"
ACCENT_FG = "#FFFFFF"
BORDER = "#C5D0D8"


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


def _log(msg: str) -> None:
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(msg.rstrip() + "\n")
    except Exception:
        pass


class App(Tk):
    def __init__(self, initial_urls: Optional[list[str]] = None):
        super().__init__()
        self.title("Krepost Downloader")
        self.geometry("820x540")
        self.minsize(680, 440)
        self.configure(bg=BG)

        # Hint macOS / Tk to keep a light canvas when possible
        try:
            self.tk.call("set", "::tk::mac::useDarkAppearance", "0")
        except Exception:
            pass

        self._ui_q: queue.Queue = queue.Queue()
        self.dest_var = StringVar(value=str(DEFAULT_DEST))
        self.url_var = StringVar()

        self.manager = DownloadManager(on_progress=self._on_progress)

        self._build_style()
        self._build_ui()
        self._poll_ui()
        self._bind_shortcuts()

        for u in initial_urls or []:
            if looks_like_url(u):
                self._enqueue(u, auto_start=True)

        self._last_clip = ""
        self.after(2000, self._watch_clipboard)

    def _build_style(self) -> None:
        style = ttk.Style(self)
        # Never use 'aqua' here — custom colors vanish in Dark Mode → blank window
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure(
            "Treeview",
            background=CARD,
            fieldbackground=CARD,
            foreground=FG,
            rowheight=26,
            font=("Helvetica", 12),
            bordercolor=BORDER,
        )
        style.configure(
            "Treeview.Heading",
            background=BG,
            foreground=FG,
            font=("Helvetica", 12, "bold"),
            relief="flat",
        )
        style.map("Treeview", background=[("selected", "#B8D4C8")], foreground=[("selected", FG)])

    def _build_ui(self) -> None:
        head = Frame(self, bg=BG)
        head.pack(fill=X, padx=18, pady=(16, 6))
        Label(
            head,
            text="Krepost Downloader",
            bg=BG,
            fg=FG,
            font=("Helvetica", 22, "bold"),
        ).pack(anchor="w")
        Label(
            head,
            text="Докачка при обрыве сети · вставьте URL · Скачать",
            bg=BG,
            fg=MUTED,
            font=("Helvetica", 12),
        ).pack(anchor="w", pady=(2, 0))

        card = Frame(self, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill=X, padx=18, pady=8)

        row1 = Frame(card, bg=CARD)
        row1.pack(fill=X, padx=12, pady=(12, 6))
        Label(row1, text="Ссылка", bg=CARD, fg=FG, font=("Helvetica", 12)).pack(side=LEFT)
        self.url_entry = Entry(
            row1,
            textvariable=self.url_var,
            font=("Menlo", 12),
            bg="#FFFFFF",
            fg=FG,
            insertbackground=FG,
            relief="solid",
            bd=1,
        )
        self.url_entry.pack(side=LEFT, fill=X, expand=True, padx=8, ipady=4)
        self.url_entry.focus_set()
        self._btn(row1, "Вставить", self._paste_url).pack(side=LEFT, padx=2)
        self._btn(row1, "Скачать", self._add_from_field, primary=True).pack(side=LEFT, padx=2)

        row2 = Frame(card, bg=CARD)
        row2.pack(fill=X, padx=12, pady=(0, 12))
        Label(row2, text="Папка", bg=CARD, fg=FG, font=("Helvetica", 12)).pack(side=LEFT)
        Entry(
            row2,
            textvariable=self.dest_var,
            font=("Helvetica", 12),
            bg="#FFFFFF",
            fg=FG,
            insertbackground=FG,
            relief="solid",
            bd=1,
        ).pack(side=LEFT, fill=X, expand=True, padx=8, ipady=4)
        self._btn(row2, "Выбрать…", self._pick_dest).pack(side=LEFT)

        Label(
            self,
            text="Обрыв сети не отменяет загрузку — продолжит с .part файла.",
            bg=BG,
            fg=MUTED,
            font=("Helvetica", 11),
        ).pack(anchor="w", padx=18)

        list_frame = Frame(self, bg=BG)
        list_frame.pack(fill=BOTH, expand=True, padx=18, pady=8)

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
        self.tree.column("progress", width=180, anchor="w")
        self.tree.column("speed", width=100, anchor="center")
        self.tree.column("status", width=200, anchor="w")
        scroll = Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side=LEFT, fill=BOTH, expand=True)
        scroll.pack(side=RIGHT, fill=Y)

        btns = Frame(self, bg=BG)
        btns.pack(fill=X, padx=18, pady=(0, 14))
        self._btn(btns, "Пауза", self._pause_sel).pack(side=LEFT, padx=2)
        self._btn(btns, "Продолжить", self._resume_sel).pack(side=LEFT, padx=2)
        self._btn(btns, "Отмена", self._cancel_sel).pack(side=LEFT, padx=2)
        self._btn(btns, "Открыть папку", self._open_dest).pack(side=RIGHT, padx=2)

    def _btn(self, parent, text, command, primary: bool = False) -> Button:
        if primary:
            return Button(
                parent,
                text=text,
                command=command,
                font=("Helvetica", 12, "bold"),
                bg=ACCENT,
                fg=ACCENT_FG,
                activebackground="#095C42",
                activeforeground=ACCENT_FG,
                relief="flat",
                padx=12,
                pady=4,
            )
        return Button(
            parent,
            text=text,
            command=command,
            font=("Helvetica", 12),
            bg="#FFFFFF",
            fg=FG,
            activebackground=BORDER,
            relief="solid",
            bd=1,
            padx=10,
            pady=3,
        )

    def _bind_shortcuts(self) -> None:
        self.bind("<Command-v>", lambda e: self._paste_url())
        self.bind("<Control-v>", lambda e: self._paste_url())
        self.bind("<Return>", lambda e: self._add_from_field())

    def _watch_clipboard(self) -> None:
        try:
            clip = self.clipboard_get().strip()
            if (
                clip
                and clip != self._last_clip
                and looks_like_url(clip)
                and self.focus_displayof() is not None
            ):
                self._last_clip = clip
                if not self.url_var.get().strip():
                    self.url_var.set(clip)
        except Exception:
            pass
        self.after(2000, self._watch_clipboard)

    def _paste_url(self) -> None:
        try:
            text = self.clipboard_get().strip()
        except Exception:
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
        return sel[0] if sel else None

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
            os.startfile(str(path))  # type: ignore[attr-defined]
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
            END,
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


def _show_fatal(err: str) -> None:
    _log(err)
    try:
        root = Tk()
        root.withdraw()
        messagebox.showerror(
            "Krepost Downloader",
            f"Не удалось запустить интерфейс.\n\n{err[:800]}\n\nЛог: {LOG_PATH}",
        )
        root.destroy()
    except Exception:
        if sys.platform == "darwin":
            import subprocess

            subprocess.run(
                [
                    "osascript",
                    "-e",
                    f'display dialog "Krepost Downloader ошибка:\\n{err[:400]}" buttons {{"OK"}}',
                ],
                check=False,
            )


def main() -> None:
    urls = [a for a in sys.argv[1:] if looks_like_url(a)]
    try:
        app = App(initial_urls=urls)
        app.mainloop()
    except Exception:
        _show_fatal(traceback.format_exc())
        raise


if __name__ == "__main__":
    main()
