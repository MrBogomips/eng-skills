#!/usr/bin/env bash
set -euo pipefail
git init -q -b main
G="git -c user.name=t -c user.email=t@example.com"
mkdir -p docs imgconv tests
cat > docs/usage.md <<'X'
# Usage

    imgconv convert photo.png --format jpeg

Converts one image to the given format.
X
cat > imgconv/resize.py <<'X'
def _resize_kernel(pixels, factor):
    out = []
    for p in pixels:
        out.append(p * factor)
    return out


def resize(pixels, factor):
    return _resize_kernel(pixels, factor)
X
cat > tests/test_resize.py <<'X'
from imgconv.resize import resize


def test_resize():
    assert resize([1, 2], 2) == [2, 4]
X
$G add -A && $G commit -q -m "initial"
git checkout -q -b feature/x
cat > imgconv/resize.py <<'X'
def _resize_kernel(pixels, factor):
    return [p * factor for p in pixels]


def resize(pixels, factor):
    return _resize_kernel(pixels, factor)
X
cat >> tests/test_resize.py <<'X'


def test_resize_empty():
    assert resize([], 3) == []
X
$G commit -q -am "refactor(resize): simplify _resize_kernel, add test"
