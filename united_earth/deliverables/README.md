# United Earth Foundation Masterplan — Deliverables

This folder contains the final publication-ready deliverables for the United Earth Foundation Masterplan.

## Files

| File | Format | Description |
|------|--------|-------------|
| `masterplan.pdf` | PDF (A4 Landscape, 1.4 MB, 173 pages) | Print-ready document with title page, table of contents, all 26 sections, abbreviations reference (A-Z), and sources appendix. Optimized for wide tables. |
| `masterplan_site.html` | HTML (708 KB) | Interactive, searchable single-file website with: fixed sidebar TOC (338 entries), real-time search filtering, deep linking (hash URLs), heading anchors (¶), dark mode, mobile responsive, print styles, active section highlighting, back-to-top button, keyboard shortcuts (`/` = search, `Escape` = close). |

## Build Pipeline

```powershell
# 1. Build combined markdown from source sections
C:/.venv/Scripts/python.exe d:/Dev/PlannedEducation/united_earth/build_final.py

# 2. Generate PDF (Playwright Chromium, landscape A4)
C:/.venv/Scripts/python.exe d:/Dev/PlannedEducation/united_earth/build_pdf_final.py

# 3. Generate HTML site (Python-Markdown + BeautifulSoup)
C:/.venv/Scripts/python.exe d:/Dev/PlannedEducation/united_earth/build_html_site.py
```

## Source Files

Located in `../same in parts/`:
- `MASTERPLAN_COMBINED.md` — Combined markdown source (432 KB)
- `ABBREVIATIONS.md` — Complete A-Z abbreviations (40 KB)
- `sources_appendix.md` — 73+ clickable source URLs
- `section_XX_expanded_part1.md` — 26 expanded section sources

## Authorship

This document was created by:
- **ezixen** — Architect & Systems Designer
- **Nemotron 3.0 Ultra** — NVIDIA Large Language Model
- **Nemotron 3.5 Super** — NVIDIA Large Language Model

*United Earth Foundation Masterplan — Full Specification for Planetary Regeneration*
*Version 1.0 | October 2026*