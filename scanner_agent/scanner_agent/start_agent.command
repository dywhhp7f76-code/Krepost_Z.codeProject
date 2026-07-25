#!/bin/bash
# Открывает VS Code с проектом И запускает сканер в окне Terminal
PROJECT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT" || exit 1

# GUI/.app запускают скрипт без Homebrew в PATH — добавляем вручную
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

PYTHON="$PROJECT/venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON="$(command -v python3 || echo /usr/bin/python3)"
fi

CODE_BIN=""
for candidate in \
  "/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code" \
  "/opt/homebrew/bin/code" \
  "$(command -v code 2>/dev/null)"
do
  if [[ -n "$candidate" && -x "$candidate" ]]; then
    CODE_BIN="$candidate"
    break
  fi
done

# 1) VS Code — сначала open -a (надёжно из .app), потом CLI
opened=0
if [[ -d "/Applications/Visual Studio Code.app" ]]; then
  open -a "Visual Studio Code" --args "$PROJECT" "$PROJECT/darknet_agent.py" && opened=1
fi
if [[ "$opened" -eq 0 && -n "$CODE_BIN" ]]; then
  "$CODE_BIN" -n "$PROJECT" "$PROJECT/darknet_agent.py" && opened=1
fi
if [[ "$opened" -eq 0 ]]; then
  osascript -e 'display dialog "VS Code не найден в /Applications.\nСкан всё равно запущу в Terminal." buttons {"OK"} default button 1' || true
else
  # Вернуть фокус на Code (Terminal ниже его перебьёт — это ок)
  osascript -e 'tell application "Visual Studio Code" to activate' >/dev/null 2>&1 || true
fi

# 2) Скан в Terminal
osascript <<EOF
tell application "Terminal"
  do script "cd $(printf %q "$PROJECT") && clear && echo 'Darknet Agent — VS Code открыт. Здесь скан.' && echo && exec $(printf %q "$PYTHON") $(printf %q "$PROJECT/darknet_agent.py")"
  activate
end tell
EOF

exit 0
