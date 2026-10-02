#!/usr/bin/env python3
"""Prepare a GitHub Pages artifact with cache-safe static asset URLs.

The repository keeps readable/stable asset URLs. At deploy time this script copies
the site and stamps local JS/CSS query strings with the current commit SHA, so UI
changes need one commit instead of a second cache-bust commit.
"""
from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path

ASSET_VERSION_RE = re.compile(r'(?P<asset>[A-Za-z0-9._-]+\.(?:js|css))(?:\?v=[^"\'<>\s]+)?')


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="dist")
    parser.add_argument("--output", default="site")
    parser.add_argument("--version", required=True)
    args = parser.parse_args()

    source = Path(args.source)
    output = Path(args.output)
    version = re.sub(r"[^A-Za-z0-9._-]", "", args.version)[:16] or "deploy"

    if output.exists():
        shutil.rmtree(output)
    shutil.copytree(source, output)

    changed = 0
    for path in output.rglob("*.html"):
        text = path.read_text(encoding="utf-8")
        stamped = ASSET_VERSION_RE.sub(lambda m: f"{m.group('asset')}?v={version}", text)
        if stamped != text:
            path.write_text(stamped, encoding="utf-8")
            changed += 1

    print({"status": "ok", "version": version, "html_files_stamped": changed, "output": str(output)})


if __name__ == "__main__":
    main()
