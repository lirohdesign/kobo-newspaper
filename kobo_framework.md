# Framework — Kobo library and epub pipeline

This describes the shape of the local reading library: what generates
epubs, what stays private, how content reaches the Kobo, and what's
planned but not yet built. The daily newspaper digest is a separate
pipeline (`framework.md`); this covers everything else that ends up on
the device.

## Design principles

**The library folder is the source of truth, not Calibre.** Epubs live in
`library/` on this machine. Calibre is available as a conversion tool
(`ebook-convert`) if a source file needs format work, but it holds no
database and owns nothing. The Kobo sync is a file copy, not a library
sync.

**Output is local-only.** `library/` and `projects.local.json` are both
gitignored — neither epub files nor the list of which projects are
approved for processing ever touch the repo. A sensitive project can't
escape into a public commit by accident; adding it to the epub workflow
requires a deliberate local edit.

**Opt-in, not opt-out.** Projects must be explicitly listed in
`projects.local.json` to be processed. The default for any project is
exclusion.

## The library folder

```
library/
├── documents/    epubs generated from local project markdown files
├── gutenberg/    epubs downloaded from Project Gutenberg  (planned)
└── newspaper/    epub snapshots of the daily digest        (planned)
```

All three subdirectories are gitignored. The folder is created
automatically the first time `docs_to_epub.py` runs.

## Generating project epubs

`docs_to_epub.py` handles the documents pipeline. It reads
`projects.local.json` for the approved project list, finds all `.md`
files in each project directory (skipping `.git/`, `venv/`,
`node_modules/`, and files under ~100 bytes), bundles them into a single
epub per project via pandoc, and writes a dated file to
`library/documents/`.

```bash
python3 docs_to_epub.py              # rebuild all listed projects
python3 docs_to_epub.py kobo-pi      # rebuild one project by name
```

Output files are named `{project}_{YYYY-MM-DD}.epub`. The date is
intentional: when reading a spec and something feels out of sync with
what the project actually became, the date on the file tells you how
stale the snapshot might be.

**Adding a project** — edit `projects.local.json` locally:

```json
[
  {"name": "kobo-newspaper", "path": "/Users/B/Documents/kobo/kobo-newspaper"},
  {"name": "kobo-pi",        "path": "/Users/B/Documents/kobo-pi"},
  {"name": "hocket",         "path": "/Users/B/Documents/hocket"}
]
```

Then run `docs_to_epub.py`. The config file is gitignored and never
leaves the machine.

## Syncing to the Kobo

When the Kobo is connected over USB it mounts as a standard volume. Copy
epubs directly to its `eBooks/` folder — the device discovers new files
on the next library refresh (usually automatic on disconnect, or via
Menu → Sync).

```bash
cp library/documents/*.epub /Volumes/KOBOeReader/eBooks/
```

A `kobo_sync.py` script to handle mount detection and copy in one
command is planned for after the device arrives.

## Gutenberg pipeline (planned)

A `gutenberg_add.py` script will download an epub by Project Gutenberg
ID into `library/gutenberg/` and record it in a local `gutenberg.json`
catalog to prevent re-downloads. Usage intent:

```bash
python3 gutenberg_add.py 1342    # Pride and Prejudice
```

## What lives where

| Concern | Lives in |
| :--- | :--- |
| Approved project list | `projects.local.json` (gitignored, local only) |
| Project markdown → epub conversion | `docs_to_epub.py` |
| Generated epubs | `library/` (gitignored, local only) |
| Kobo sync (planned) | `kobo_sync.py` |
| Gutenberg catalog (planned) | `gutenberg.json` (gitignored) + `gutenberg_add.py` |
