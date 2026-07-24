#!/usr/bin/env python3
"""Krepost Chat — отдельная программа оператора (пароль → чат → загрузка личных данных).

    python3 app.py
    # или KrepostChat.app на Mac

Env / UI:
  API URL  — http://10.0.0.1:8000 (Studio) или http://127.0.0.1:8000
  Password — KREPOST_OPERATOR_PASSWORD на сервере
"""
from __future__ import annotations

import json
import os
import sys
import threading
import traceback
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from tkinter import (
    BOTH,
    END,
    LEFT,
    RIGHT,
    WORD,
    X,
    Y,
    Button,
    Entry,
    Frame,
    Label,
    Scrollbar,
    StringVar,
    Text,
    Tk,
    filedialog,
    messagebox,
    ttk,
)

_APP_DIR = Path(__file__).resolve().parent
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

from bridge import (  # noqa: E402
    bridge_report,
    default_api_url,
    guess_studio_peer,
    save_config,
    url_for_host,
)

BG = "#E8EEF2"
CARD = "#F4F7FA"
FG = "#0F2A3D"
MUTED = "#3D5A6C"
ACCENT = "#0B6E4F"
ACCENT_FG = "#FFFFFF"
BORDER = "#C5D0D8"
LOG_PATH = Path.home() / "Library" / "Logs" / "KrepostChat.log"

DEFAULT_API = default_api_url()


def _log(msg: str) -> None:
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(msg.rstrip() + "\n")
    except Exception:
        pass


class ApiClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.token = ""

    def _req(
        self,
        method: str,
        path: str,
        body: dict | None = None,
        *,
        auth: bool = True,
        timeout: float = 180,
    ) -> dict:
        data = None
        headers = {"Accept": "application/json"}
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if auth and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        req = urllib.request.Request(
            self.base_url + path,
            data=data,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            try:
                payload = json.loads(detail)
            except Exception:
                payload = {"detail": detail}
            raise RuntimeError(f"HTTP {e.code}: {payload.get('detail', detail)}") from e

    def login(self, password: str) -> None:
        r = self._req(
            "POST",
            "/v1/login",
            {"password": password, "totp": ""},
            auth=False,
            timeout=30,
        )
        self.token = r["token"]

    def query(self, text: str, session_id: str, use_memory: bool) -> dict:
        return self._req(
            "POST",
            "/v1/query",
            {"text": text, "session_id": session_id, "use_memory": use_memory},
        )

    def agent(self, text: str, session_id: str) -> dict:
        return self._req(
            "POST",
            "/v1/agent",
            {"text": text, "session_id": session_id, "use_memory": True},
        )

    def ingest(self, filename: str, content: str, private: bool = True) -> dict:
        return self._req(
            "POST",
            "/v1/ingest",
            {"filename": filename, "content": content, "private": private},
            timeout=120,
        )

    def health(self) -> dict:
        return self._req("GET", "/health", auth=False, timeout=10)


class KrepostChatApp(Tk):
    def __init__(self):
        super().__init__()
        self.title("Krepost Chat")
        self.geometry("900x640")
        self.minsize(720, 520)
        self.configure(bg=BG)
        try:
            self.tk.call("set", "::tk::mac::useDarkAppearance", "0")
        except Exception:
            pass

        self.api_var = StringVar(value=DEFAULT_API)
        self.password_var = StringVar()
        self.mode_var = StringVar(value="vault")
        self.session_id = f"op-{uuid.uuid4().hex[:12]}"
        self.client = ApiClient(DEFAULT_API)
        self._busy = False

        self._build_login()
        self._build_chat()
        self._show_login()

    def _btn(self, parent, text, cmd, primary=False):
        if primary:
            return Button(
                parent,
                text=text,
                command=cmd,
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
            command=cmd,
            font=("Helvetica", 12),
            bg="#FFFFFF",
            fg=FG,
            relief="solid",
            bd=1,
            padx=10,
            pady=3,
        )

    def _build_login(self):
        self.login_frame = Frame(self, bg=BG)
        Label(
            self.login_frame,
            text="Krepost Chat",
            bg=BG,
            fg=FG,
            font=("Helvetica", 24, "bold"),
        ).pack(anchor="w", padx=24, pady=(32, 4))
        Label(
            self.login_frame,
            text="Только для оператора. Пароль на Studio (KREPOST_OPERATOR_PASSWORD).\n"
            "Другая сеть / не тот же Wi‑Fi → мост Tailscale (порты наружу не открываем).\n"
            "TOTP / ключ — позже.",
            bg=BG,
            fg=MUTED,
            font=("Helvetica", 12),
            justify="left",
        ).pack(anchor="w", padx=24, pady=(0, 16))

        card = Frame(
            self.login_frame, bg=CARD, highlightbackground=BORDER, highlightthickness=1
        )
        card.pack(fill=X, padx=24, pady=8)

        row = Frame(card, bg=CARD)
        row.pack(fill=X, padx=14, pady=(14, 6))
        Label(row, text="API", bg=CARD, fg=FG, width=10, anchor="w").pack(side=LEFT)
        Entry(row, textvariable=self.api_var, font=("Menlo", 12), bg="#FFF", fg=FG).pack(
            side=LEFT, fill=X, expand=True, ipady=3
        )

        bridges = Frame(card, bg=CARD)
        bridges.pack(fill=X, padx=14, pady=(0, 6))
        self._btn(bridges, "Мост Tailscale", self._use_tailscale).pack(side=LEFT, padx=2)
        self._btn(bridges, "Домашний Wi‑Fi", self._use_lan).pack(side=LEFT, padx=2)
        self._btn(bridges, "Статус моста", self._show_bridge_status).pack(side=LEFT, padx=2)

        row2 = Frame(card, bg=CARD)
        row2.pack(fill=X, padx=14, pady=(6, 14))
        Label(row2, text="Пароль", bg=CARD, fg=FG, width=10, anchor="w").pack(side=LEFT)
        Entry(
            row2,
            textvariable=self.password_var,
            show="•",
            font=("Helvetica", 12),
            bg="#FFF",
            fg=FG,
        ).pack(side=LEFT, fill=X, expand=True, ipady=3)

        self._btn(self.login_frame, "Войти", self._do_login, primary=True).pack(
            anchor="w", padx=24, pady=12
        )

    def _build_chat(self):
        self.chat_frame = Frame(self, bg=BG)

        top = Frame(self.chat_frame, bg=BG)
        top.pack(fill=X, padx=16, pady=(12, 4))
        Label(
            top,
            text="Krepost Chat",
            bg=BG,
            fg=FG,
            font=("Helvetica", 18, "bold"),
        ).pack(side=LEFT)
        self._btn(top, "Выйти", self._logout).pack(side=RIGHT, padx=4)
        self._btn(top, "Загрузить файл…", self._upload_file).pack(side=RIGHT, padx=4)

        modes = Frame(self.chat_frame, bg=BG)
        modes.pack(fill=X, padx=16, pady=4)
        Label(modes, text="Режим:", bg=BG, fg=MUTED).pack(side=LEFT)
        for val, label in (
            ("fast", "Быстрый"),
            ("vault", "Vault / RAG"),
            ("agent", "Агент"),
        ):
            ttk.Radiobutton(modes, text=label, value=val, variable=self.mode_var).pack(
                side=LEFT, padx=6
            )

        wrap = Frame(self.chat_frame, bg=BG)
        wrap.pack(fill=BOTH, expand=True, padx=16, pady=8)
        self.transcript = Text(
            wrap,
            wrap=WORD,
            font=("Helvetica", 12),
            bg="#FFFFFF",
            fg=FG,
            relief="solid",
            bd=1,
            state="disabled",
        )
        scroll = Scrollbar(wrap, command=self.transcript.yview)
        self.transcript.configure(yscrollcommand=scroll.set)
        self.transcript.pack(side=LEFT, fill=BOTH, expand=True)
        scroll.pack(side=RIGHT, fill=Y)

        bottom = Frame(self.chat_frame, bg=BG)
        bottom.pack(fill=X, padx=16, pady=(0, 14))
        self.input = Text(
            bottom, height=3, wrap=WORD, font=("Helvetica", 12), bg="#FFF", fg=FG, bd=1, relief="solid"
        )
        self.input.pack(side=LEFT, fill=X, expand=True, padx=(0, 8))
        self._btn(bottom, "Отправить", self._send, primary=True).pack(side=RIGHT)
        self.bind("<Command-Return>", lambda e: self._send())
        self.bind("<Control-Return>", lambda e: self._send())

    def _show_login(self):
        self.chat_frame.pack_forget()
        self.login_frame.pack(fill=BOTH, expand=True)

    def _show_chat(self):
        self.login_frame.pack_forget()
        self.chat_frame.pack(fill=BOTH, expand=True)
        self._append("system", "Сессия открыта. Можно писать и загружать личные .md/.txt в vault/personal/.")

    def _append(self, who: str, text: str):
        self.transcript.configure(state="normal")
        self.transcript.insert(END, f"\n[{who}]\n{text}\n")
        self.transcript.see(END)
        self.transcript.configure(state="disabled")

    def _use_lan(self):
        url = os.environ.get("KREPOST_LAN_URL", "http://10.0.0.1:8000")
        self.api_var.set(url)
        save_config({"studio_url": url, "preferred": "lan"})

    def _use_tailscale(self):
        def work():
            peer = guess_studio_peer()
            if not peer:
                self.after(
                    0,
                    lambda: messagebox.showwarning(
                        "Мост Tailscale",
                        "Studio не найден.\n\n"
                        "1) Поставь Tailscale на Studio и Air (один аккаунт)\n"
                        "2) На Studio: ./scripts/krepost_bridge_studio.sh\n"
                        "3) На Air: ./scripts/krepost_bridge_air.sh\n"
                        "или впиши http://100.x.x.x:8000 вручную",
                    ),
                )
                return
            url = url_for_host(peer["ip"])
            save_config(
                {
                    "studio_tailscale_ip": peer["ip"],
                    "studio_url": url,
                    "preferred": "tailscale",
                }
            )
            self.after(0, lambda: self.api_var.set(url))
            self.after(
                0,
                lambda: messagebox.showinfo(
                    "Мост Tailscale",
                    f"Studio: {peer['hostname']}\n{url}\n\nРаботает даже не в том же Wi‑Fi.",
                ),
            )

        threading.Thread(target=work, daemon=True).start()

    def _show_bridge_status(self):
        def work():
            report = bridge_report()
            self.after(0, lambda: messagebox.showinfo("Статус моста", report))

        threading.Thread(target=work, daemon=True).start()

    def _do_login(self):
        url = self.api_var.get().strip()
        pw = self.password_var.get()
        if not url or not pw:
            messagebox.showwarning("Вход", "Укажите API и пароль")
            return
        save_config({"studio_url": url})

        def work():
            try:
                self.client = ApiClient(url)
                try:
                    h = self.client.health()
                    if h.get("auth_required") is False:
                        _log("warning: server auth_required=false")
                except Exception as e:
                    _log(f"health: {e}")
                self.client.login(pw)
                self.after(0, self._show_chat)
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Вход", str(e)))

        threading.Thread(target=work, daemon=True).start()

    def _logout(self):
        self.client.token = ""
        self.password_var.set("")
        self.transcript.configure(state="normal")
        self.transcript.delete("1.0", END)
        self.transcript.configure(state="disabled")
        self._show_login()

    def _send(self):
        if self._busy:
            return
        text = self.input.get("1.0", END).strip()
        if not text:
            return
        self.input.delete("1.0", END)
        self._append("вы", text)
        mode = self.mode_var.get()
        self._busy = True

        def work():
            try:
                if mode == "agent":
                    r = self.client.agent(text, self.session_id)
                else:
                    r = self.client.query(
                        text, self.session_id, use_memory=(mode == "vault")
                    )
                out = r.get("output") or r.get("detail") or json.dumps(r, ensure_ascii=False)
                status = r.get("status", "?")
                verdict = r.get("verdict", "")
                self.after(
                    0,
                    lambda: self._append(
                        "крепость", f"({status}/{verdict})\n{out}"
                    ),
                )
            except Exception as e:
                self.after(0, lambda: self._append("ошибка", str(e)))
            finally:
                self.after(0, self._clear_busy)

        threading.Thread(target=work, daemon=True).start()

    def _clear_busy(self):
        self._busy = False

    def _upload_file(self):
        path = filedialog.askopenfilename(
            title="Личный / закрытый файл",
            filetypes=[
                ("Текст", "*.md *.txt"),
                ("Markdown", "*.md"),
                ("Все", "*.*"),
            ],
        )
        if not path:
            return
        p = Path(path)
        try:
            content = p.read_text(encoding="utf-8")
        except Exception as e:
            messagebox.showerror("Файл", str(e))
            return

        def work():
            try:
                r = self.client.ingest(p.name, content, private=True)
                msg = (
                    f"Загружено: {r.get('doc_id')} → {r.get('path')}\n"
                    f"chunks={r.get('chunks')} blocked={r.get('blocked')}"
                )
                self.after(0, lambda: self._append("загрузка", msg))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Загрузка", str(e)))

        threading.Thread(target=work, daemon=True).start()


def main():
    try:
        app = KrepostChatApp()
        app.mainloop()
    except Exception:
        err = traceback.format_exc()
        _log(err)
        try:
            root = Tk()
            root.withdraw()
            messagebox.showerror("Krepost Chat", err[:800])
            root.destroy()
        except Exception:
            pass
        raise


if __name__ == "__main__":
    main()
