#!/usr/bin/env bash
set -euo pipefail
git init -q -b main
G="git -c user.name=t -c user.email=t@example.com"
mkdir -p docs/guides pixkit
cat > mkdocs.yml <<'X'
site_name: pixkit
site_url: https://example.github.io/pixkit/
nav:
  - Home: index.md
  - Guides:
      - Getting started: guides/getting-started.md
X
cat > docs/index.md <<'X'
# pixkit

A small toolkit for converting images.
X
cat > docs/guides/getting-started.md <<'X'
# Getting started

Install pixkit and run `pixkit convert photo.png`.
X
cat > pixkit/__init__.py <<'X'
def convert(path):
    return path
X
$G add -A && $G commit -q -m "initial"
git checkout -q -b feature/x
cat > docs/guides/batch.md <<'X'
# Converting a folder

Run `pixkit batch ./photos` to convert every image in a folder.
X
cat >> pixkit/__init__.py <<'X'


def batch(folder):
    return folder
X
$G add -A && $G commit -q -m "docs: add batch guide"
