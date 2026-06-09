#!/usr/bin/env python3
"""Converts project markdown files to epub for Kobo reading.

Reads projects.local.json (gitignored — never committed) for the list of
project directories to process. For each project, gathers all .md files,
bundles them into a single dated epub via pandoc, and writes it to
library/documents/. The library/ folder is also gitignored — output stays
local, never hits any repo.

Usage:
    python3 docs_to_epub.py              # convert all listed projects
    python3 docs_to_epub.py kobo-pi      # convert one project by name

projects.local.json shape:
    [
      {"name": "kobo-newspaper", "path": "/Users/.../kobo/kobo-newspaper"},
      {"name": "kobo-pi",        "path": "/Users/.../kobo-pi"}
    ]
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).parent
CONFIG_PATH = HERE / "projects.local.json"
OUTPUT_DIR = HERE / "library" / "documents"
MIN_FILE_BYTES = 100  # skip near-empty .md files (READMEs with one line, etc.)


def find_md_files(project_path: Path) -> list[Path]:
    skip_dirs = {".git", "venv", "node_modules", "__pycache__"}
    files = []
    for f in sorted(project_path.rglob("*.md")):
        if any(part in skip_dirs for part in f.parts):
            continue
        if f.stat().st_size < MIN_FILE_BYTES:
            continue
        files.append(f)
    return files


def build_epub(name: str, project_path: Path, date_str: str) -> Path:
    md_files = find_md_files(project_path)
    if not md_files:
        print(f"  {name}: no .md files found, skipping")
        return None

    output_path = OUTPUT_DIR / f"{name}_{date_str}.epub"
    print(f"  {name}: {len(md_files)} files → {output_path.name}")

    cmd = [
        "pandoc",
        *[str(f) for f in md_files],
        "--to", "epub",
        "--output", str(output_path),
        "--toc",
        "--toc-depth=2",
        "--metadata", f"title={name}",
        "--metadata", f"date={date_str}",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  {name}: pandoc error — {result.stderr.strip()}")
        return None
    return output_path


def main():
    if not CONFIG_PATH.exists():
        print(f"No projects.local.json found at {CONFIG_PATH}")
        print("Create it with a list of project paths — see the docstring for the shape.")
        return

    projects = json.loads(CONFIG_PATH.read_text())
    filter_name = sys.argv[1] if len(sys.argv) == 2 else None
    if filter_name:
        projects = [p for p in projects if p["name"] == filter_name]
        if not projects:
            print(f"No project named '{filter_name}' in projects.local.json")
            return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")

    print(f"Building epubs — {date_str}")
    built = []
    for entry in projects:
        path = Path(entry["path"]).expanduser()
        if not path.exists():
            print(f"  {entry['name']}: path not found ({path}), skipping")
            continue
        result = build_epub(entry["name"], path, date_str)
        if result:
            built.append(result)

    print(f"\n{len(built)} epub(s) written to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
