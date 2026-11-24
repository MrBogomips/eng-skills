#!/usr/bin/env bash
set -euo pipefail
git init -q -b main
G="git -c user.name=t -c user.email=t@example.com"
mkdir -p docs imgconv
cat > README.md <<'X'
# imgconv

Command-line image converter.

Write converted files to another folder with `--output-dir`. Set `IMGCONV_QUALITY` to change the default JPEG quality.
X
cat > docs/usage.md <<'X'
# Usage

    imgconv convert photo.png --format jpeg --output-dir out/

`--output-dir` sets the folder for converted files. The default JPEG quality comes from the `IMGCONV_QUALITY` environment variable (1-100, default 85).
X
cat > imgconv/cli.py <<'X'
import argparse
import os


def build_parser():
    p = argparse.ArgumentParser(prog="imgconv")
    sub = p.add_subparsers(dest="command")
    c = sub.add_parser("convert")
    c.add_argument("source")
    c.add_argument("--format", default="png")
    c.add_argument("--output-dir", default=".")
    c.add_argument("--quality", type=int, default=int(os.environ.get("IMGCONV_QUALITY", "85")))
    return p
X
$G add -A && $G commit -q -m "initial"
git checkout -q -b feature/x
cat > imgconv/cli.py <<'X'
import argparse


def build_parser():
    p = argparse.ArgumentParser(prog="imgconv")
    sub = p.add_subparsers(dest="command")
    c = sub.add_parser("convert")
    c.add_argument("source")
    c.add_argument("--format", default="png")
    c.add_argument("--out-dir", default=".")
    c.add_argument("--quality", type=int, default=85)
    return p
X
$G commit -q -am "refactor(cli): rename --output-dir to --out-dir, drop IMGCONV_QUALITY"
