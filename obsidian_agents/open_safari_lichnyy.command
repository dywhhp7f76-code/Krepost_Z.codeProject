#!/bin/bash
# Все чаты → одна Safari-группа «Личный»
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if ! curl -sf --max-time 1 "http://127.0.0.1:8765/api/config" >/dev/null; then
  nohup "$ROOT/.venv/bin/python" "$ROOT/app.py" >>"$ROOT/run.log" 2>&1 &
  for _ in $(seq 1 20); do
    curl -sf --max-time 1 "http://127.0.0.1:8765/api/config" >/dev/null && break
    sleep 0.4
  done
fi

osascript <<'APPLESCRIPT'
on urlPresent(existingList, needle)
  repeat with e in existingList
    set eText to e as text
    if eText contains needle then return true
  end repeat
  return false
end urlPresent

tell application "Safari" to activate
delay 0.35

tell application "Safari"
  set personalWin to missing value
  repeat with w in windows
    try
      if (name of w as text) starts with "Личный" then
        set personalWin to w
        exit repeat
      end if
    end try
  end repeat

  set createdNew to false
  if personalWin is missing value then
    make new document with properties {URL:"http://127.0.0.1:8765/hub"}
    set personalWin to front window
    set createdNew to true
  else
    set index of personalWin to 1
  end if

  tell personalWin
    set existing to {}
    repeat with t in tabs
      try
        set end of existing to (URL of t as text)
      end try
    end repeat

    if not (my urlPresent(existing, "8765/hub")) then
      make new tab with properties {URL:"http://127.0.0.1:8765/hub"}
    end if
    if not (my urlPresent(existing, "8000/chat")) then
      make new tab with properties {URL:"http://10.0.0.1:8000/chat"}
    end if
    set hasAgentsRoot to false
    repeat with e in existing
      set eText to e as text
      if eText is "http://127.0.0.1:8765/" or eText is "http://127.0.0.1:8765" then
        set hasAgentsRoot to true
      end if
    end repeat
    if not hasAgentsRoot then
      make new tab with properties {URL:"http://127.0.0.1:8765/"}
    end if
    if not (my urlPresent(existing, "claude.ai")) then
      make new tab with properties {URL:"https://claude.ai/chats"}
    end if

    repeat with t in tabs
      try
        if (URL of t as text) contains "8765/hub" then
          set current tab to t
          exit repeat
        end if
      end try
    end repeat
  end tell
end tell

-- новое окно ещё не в группе → «Новая группа вкладок…» → имя «Личный»
if createdNew then
  delay 0.5
  tell application "System Events"
    tell process "Safari"
      set frontmost to true
      delay 0.3
      set clicked to false
      repeat with menuTitle in {"Файл", "File"}
        try
          set fileMenu to menu 1 of menu bar item (menuTitle as text) of menu bar 1
          repeat with mi in menu items of fileMenu
            try
              set n to name of mi as text
              if n contains "группу вкладок" or n contains "Tab Group" then
                click mi
                set clicked to true
                exit repeat
              end if
            end try
          end repeat
        end try
        if clicked then exit repeat
      end repeat
      if clicked then
        delay 0.45
        keystroke "a" using command down
        delay 0.08
        keystroke "Личный"
        delay 0.08
        key code 36
      end if
    end tell
  end tell
end if

return "ok"
APPLESCRIPT

echo "Готово: Safari → группа «Личный» (хаб, Крепость, Agents, Claude)"
