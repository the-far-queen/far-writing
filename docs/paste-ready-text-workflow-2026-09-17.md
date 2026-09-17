# Paste-Ready Text Workflow (X Articles, etc.)

> **Bobby Wolfson, 2026-09-17.** Source: `C:\Users\Admin\Downloads\1h.txt`.
> Vault mirror: `vault/50-index/notes/paste-ready-text-workflow-2026-09-17.md`.

Practical 4-step workflow for converting a markdown file into paste-ready
plain text for X Articles (or any rich-text editor that doubles spacing).

## TL;DR

1. Strip headings: regex `^#{1,6}\s+` → empty
2. Collapse blanks: regex `\n\n+` → `\n` (single-spaced)
3. Save as `.txt`
4. Open in Notepad → Ctrl+A → Ctrl+C → target app → Ctrl+Shift+V

## Trigger phrase

Say **"flat paste, no headings, single spaced"** and the writer emits
running prose only: no `#` titles, no scene labels, no blank line
between every paragraph. Scene breaks can be a single `* * *` line.

## Why this matters

The far-writing pipeline produces markdown. X Articles + many rich-text
editors double-space when you paste markdown (each newline becomes a
paragraph). One clean `.txt` paste beats reformatting the article body
after upload.

## Full text

```text
That extra blank line is almost always **the editor treating every newline as a paragraph**. Markdown (and many rich-text boxes) turn each hard return into a new block, so a file that already has a blank line between paragraphs becomes *double*-spaced when pasted.

## Fastest fix on PC (no heading-stripping by hand)

**1. Paste as plain text**  
- Windows: `Ctrl+Shift+V` (works in Chrome/Edge and many apps)  
- Or right-click → **Paste as plain text**  
That stops hidden HTML from adding extra `<p>` tags.

**2. Don’t copy from a rendered preview**  
Copy from the **raw `.md` source** in Notepad / VS Code, not from a preview pane or this chat’s formatted view. Previews inject paragraph tags; source is just characters.

**3. Collapse double line-breaks in one shot**  
Open the file in VS Code or Notepad++:

- VS Code: `Ctrl+H` → turn on regex (`.*` icon)  
  - Find: `\n\n+`  
  - Replace: `\n`  
  - Replace All  
That turns “paragraph / blank / paragraph” into single-spaced paragraphs.

To **strip markdown headings** in the same pass:

- Find: `^#{1,6}\s+`  
- Replace: *(empty)*  
- Replace All  

Then save as `.txt` and paste that.

**4. Insert a file instead of paste (Windows)**  
Depends where you’re publishing:

| Destination | How to insert a file |
|---|---|
| Word / Google Docs | **Insert → File / Upload**, or drag the `.txt` onto the window |
| X Articles | No reliable “attach manuscript” — it wants paste or the article editor. Use a `.txt` with **single** newlines, paste once. |
| Notion / Obsidian | Drag the file into the page |
| Email | Attach the file; don’t paste the body unless you must |

X Articles still expect you to paste into their box. The win is preparing a **clean `.txt`** first so one paste is enough.

## Make a “paste-ready” file once

Save this workflow:

1. Put the whole tale in one `.md` or `.txt`.  
2. Regex: remove `^#{1,6}\s+` (headings).  
3. Regex: `\n\n+` → `\n` (or `\n\n` if you want *one* visual gap, not two).  
4. Save as `star-rider-paste.txt`.  
5. Open in Notepad → `Ctrl+A` → `Ctrl+C` → target app → `Ctrl+Shift+V`.

If X still doubles spacing, the article editor is adding a paragraph after every line. Then use **only single newlines** in the file (no blank lines at all). You can add space back with the editor’s own “paragraph” button after upload.

## If you want me to emit “paste-ready” text next time

Say **“flat paste, no headings, single spaced”** and I’ll output running prose only: no `#` titles, no scene labels, no blank line between every paragraph. Scene breaks can be a single line like `* * *` if you want a seam without markdown headers.
```

## Sister

- `method-book-the-signed-plan-2026-09-17.md` — the larger process book
  for how titles get made.
- `AGENTS.md` — the writing pipeline contract (voice, axes, gate).

## License

MIT. Free for all agents, human and non-human.
