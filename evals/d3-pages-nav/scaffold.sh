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
cat > pixkit/cli.py <<'X'
import argparse


def convert(path):
    print(f"converting {path}")


def main(argv=None):
    p = argparse.ArgumentParser(prog="pixkit")
    sub = p.add_subparsers(dest="command", required=True)
    c = sub.add_parser("convert")
    c.add_argument("path")
    args = p.parse_args(argv)
    if args.command == "convert":
        convert(args.path)
X
$G add -A && $G commit -q -m "initial"
git checkout -q -b feature/x
cat > docs/guides/batch.md <<'X'
# Converting a folder

Run `pixkit batch ./photos` to convert every image in a folder.
X
cat > pixkit/cli.py <<'X'
import argparse
from pathlib import Path


def convert(path):
    print(f"converting {path}")


def batch(folder):
    for path in sorted(Path(folder).iterdir()):
        if path.is_file():
            convert(str(path))


def main(argv=None):
    p = argparse.ArgumentParser(prog="pixkit")
    sub = p.add_subparsers(dest="command", required=True)
    c = sub.add_parser("convert")
    c.add_argument("path")
    b = sub.add_parser("batch")
    b.add_argument("folder")
    args = p.parse_args(argv)
    if args.command == "convert":
        convert(args.path)
    else:
        batch(args.folder)
X
$G add -A && $G commit -q -m "docs: add batch guide"
