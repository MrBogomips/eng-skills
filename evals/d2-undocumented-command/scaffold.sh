#!/usr/bin/env bash
set -euo pipefail
git init -q -b main
G="git -c user.name=t -c user.email=t@example.com"
mkdir -p docs imgconv
cat > README.md <<'X'
# imgconv

Command-line image converter. See docs/usage.md.
X
cat > docs/usage.md <<'X'
# Usage

    imgconv convert photo.png --format jpeg

Converts one image to the given format.
X
cat > imgconv/cli.py <<'X'
import argparse


def convert(source, fmt):
    print(f"converting {source} to {fmt}")


def build_parser():
    p = argparse.ArgumentParser(prog="imgconv")
    sub = p.add_subparsers(dest="command")
    c = sub.add_parser("convert")
    c.add_argument("source")
    c.add_argument("--format", default="png")
    return p
X
$G add -A && $G commit -q -m "initial"
git checkout -q -b feature/x
cat > imgconv/cli.py <<'X'
import argparse
from pathlib import Path


def convert(source, fmt):
    print(f"converting {source} to {fmt}")


def batch(folder, fmt):
    for path in sorted(Path(folder).iterdir()):
        if path.is_file():
            convert(str(path), fmt)


def build_parser():
    p = argparse.ArgumentParser(prog="imgconv")
    sub = p.add_subparsers(dest="command")
    c = sub.add_parser("convert")
    c.add_argument("source")
    c.add_argument("--format", default="png")
    b = sub.add_parser("batch")
    b.add_argument("folder")
    b.add_argument("--format", default="png")
    return p
X
$G commit -q -am "feat(cli): add batch subcommand"
