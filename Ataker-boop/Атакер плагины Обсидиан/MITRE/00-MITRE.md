---
tags: [атакер, mitre, atlas]
---

# MITRE — ATLAS + ATT&CK

## ATLAS (для AI — приоритет)

- Хаб: https://atlas.mitre.org/
- Data repo: https://github.com/mitre-atlas/atlas-data
- **Локально:**
  - `ATLAS-2026.06.yaml` — актуальный matrix dump
  - `../_raw/atlas-data-main.zip` — полный архив репо
  - `atlas-data-README.md`, `atlas-data-LICENSE`
  - снимок хаба: `../_raw/html/atlas-home.html` (тонкий SPA)

На ATLAS: 16 tactics · 173 techniques · 35 mitigations · 63 case studies.

## ATT&CK (enterprise)

- https://attack.mitre.org/
- Matrix: https://attack.mitre.org/matrices/enterprise/
- Снимки: `../_raw/html/mitre-attack.html`, `mitre-enterprise.html`

**Старт:** ATLAS matrix / YAML → 5–10 Technique ID в карточки KB. ATT&CK — для цепочек (Discovery, Defense Evasion, Impact).
