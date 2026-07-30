# плагины обсидиан (офлайн)

Готовые Community Plugins для vault Атакера.  
Скачано с GitHub releases (не весь каталог Obsidian — там 6000+).

## Состав

| id | Плагин |
|----|--------|
| `dataview` | Dataview |
| `omnisearch` | Omnisearch |
| `pdf-plus` | PDF++ |
| `templater-obsidian` | Templater |
| `obsidian-local-rest-api` | Local REST API |
| `obsidian-git` | Git |
| `table-editor-obsidian` | Advanced Tables |

Файлы: `plugins/<id>/{main.js,manifest.json,styles.css}`  
Зипы (если были в релизе): `_zips/`

## На SSD (Mac / AtakerDirty)

Из Cloud на диск не пишется. На **Air** после `git pull`:

```bash
# пример: том AtakerDirty
SSD="/Volumes/AtakerDirty/Ataker/плагины обсидиан"
mkdir -p "$SSD"
rsync -a "Ataker-boop/плагины обсидиан/" "$SSD/"
```

Или: `bash Ataker-boop/плагины\ обсидиан/install_to_ssd.sh`

## Поставить в vault Obsidian

1. Open folder as vault → `Атакер плагины Обсидиан` (или vault на SSD)
2. Скопируй плагины:

```bash
VAULT="…/Атакер плагины Обсидиан"   # путь к vault
SRC="…/плагины обсидиан/plugins"
mkdir -p "$VAULT/.obsidian/plugins"
rsync -a "$SRC/" "$VAULT/.obsidian/plugins/"
# включить:
cp community-plugins.json "$VAULT/.obsidian/" 2>/dev/null || true
```

3. Obsidian → Settings → Community plugins → включи Restricted mode OFF → Enable каждый плагин.

Не ставь облачные AI-плагины в dirty-zone без карантина.
