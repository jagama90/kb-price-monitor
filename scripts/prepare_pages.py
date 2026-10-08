#!/usr/bin/env python3
"""Prepare a GitHub Pages artifact with cache-safe asset and HTML URLs.

JS/CSS URLs are stamped with the deployment commit. The dashboard HTML itself is
also published under a commit-specific filename and the stable market.html becomes
a tiny no-cache redirect. This prevents mobile/browser/CDN caches from pinning an
older dashboard body after a successful Pages deployment.
"""
from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path

ASSET_VERSION_RE = re.compile(r'(?P<asset>[A-Za-z0-9._-]+\.(?:js|css))(?:\?v=[^"\'<>\s]+)?')


def redirect_html(target: str) -> str:
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
  <meta http-equiv="Pragma" content="no-cache">
  <meta http-equiv="Expires" content="0">
  <meta http-equiv="refresh" content="0;url={target}">
  <link rel="canonical" href="{target}">
  <title>부동산 시장 상황판</title>
  <script>location.replace({target!r} + location.search + location.hash);</script>
</head>
<body><p>최신 상황판으로 이동합니다. <a href="{target}">바로 열기</a></p></body>
</html>
"""


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

    market = output / "market.html"
    if not market.exists():
        raise SystemExit("market.html missing from deploy artifact")
    versioned_name = f"market.{version}.html"
    versioned = output / versioned_name
    versioned.write_text(market.read_text(encoding="utf-8"), encoding="utf-8")

    # Stable dashboard URL must never serve a potentially cached old body.
    market.write_text(redirect_html(f"./{versioned_name}"), encoding="utf-8")

    index = output / "index.html"
    if index.exists():
        index.write_text(redirect_html(f"./{versioned_name}"), encoding="utf-8")

    print({
        "status": "ok",
        "version": version,
        "html_files_stamped": changed,
        "versioned_dashboard": versioned_name,
        "stable_market_redirect": True,
        "output": str(output),
    })


if __name__ == "__main__":
    main()
