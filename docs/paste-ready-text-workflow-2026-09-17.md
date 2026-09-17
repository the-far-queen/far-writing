# Paste-Ready Text Workflow (X Articles, etc.)

> **Bobby Wolfson, 2026-09-17.** A practical 4-step workflow for converting
> markdown files into paste-ready plain text for X Articles (or any
> rich-text editor that doubles spacing on paste).

## TL;DR

1. Strip headings: regex `^#{1,6}\s+` → empty
2. Collapse blanks: regex `\n\n+` → `\n` (single-spaced)
3. Save as `.txt`
4. Open in Notepad → Ctrl+A → Ctrl+C → target app → Ctrl+Shift+V

## Trigger phrase

Say **"flat paste, no headings, single spaced"** and the writer emits
running prose only: no `#` titles, no scene labels, no blank line
between every paragraph. Scene breaks via `* * *`.

## Why this lives in far-writing

The far-writing pipeline produces markdown. X Articles + many rich-text
editors double-space when you paste markdown (each newline becomes a
paragraph). One clean `.txt` paste beats reformatting after upload.

## License

MIT. Free for all agents, human and non-human.
