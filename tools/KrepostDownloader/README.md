# Krepost Downloader

Обычная программа с окном (не терминал): качает файлы по URL с **докачкой** при нестабильном интернете.

## Возможности

- Вставить ссылку (`Вставить` / ⌘V) или вписать URL → **Скачать**
- Передать URL при открытии («Открыть с помощью» / аргумент)
- Пауза / Продолжить / Отмена
- Обрыв сети **не сбрасывает** прогресс: файл `имя.part` + HTTP `Range`, авто-повтор
- Выбор папки (по умолчанию `~/Downloads`; для Атакера — `/Volumes/AtakerDirty/Ataker/models/`)

## Установка на MacBook Air

Программа **не** ставится сама в «Программы» — сначала код из git, потом установщик.

```bash
cd /path/to/Krepost_Z.codeProject
git fetch origin
git checkout cursor/gui-download-manager-e5ae   # пока PR не в main
chmod +x tools/KrepostDownloader/install_mac.sh
./tools/KrepostDownloader/install_mac.sh
```

Установщик кладёт ярлык сюда (его ищет Spotlight):

`~/Applications/Krepost Downloader.app`

Открыть: `open ~/Applications/Krepost\ Downloader.app`  
Или Finder → ваша домашняя папка → **Applications** (не системные «Программы»).

Нужен **Python 3 с Tkinter** (установщик с [python.org](https://www.python.org/downloads/) — галочка Tcl/Tk, или `brew install python-tk`).

**Ярлык / иконка:** папка, залетающая в магнит (`assets/AppIcon.icns`).

## Запуск из Cursor / отладка

```bash
cd tools/KrepostDownloader
python3 app.py
python3 app.py 'https://example.com/file.gguf'
```

## Зависимости

Только стандартная библиотека Python (`tkinter`, `urllib`). Опционально `tkinterdnd2` для drag-and-drop ссылок в окно.

## Для GGUF Атакера

1. Смонтировать `AtakerDirty`
2. В программе выбрать папку `/Volumes/AtakerDirty/Ataker/models/`
3. Вставить URL GGUF с Hugging Face → Скачать
4. Дождаться «готово» (можно свернуть; при обрыве нажать **Продолжить** или подождать авто-повтор)
