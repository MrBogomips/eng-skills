"""Find documentation files and split them into sections.

All paths are POSIX and relative to the docs root.
"""

from __future__ import annotations

import functools
import html
import os
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from diff_terms import DOC_EXTENSIONS

DEFAULT_DOC_GLOBS = ["README*", "docs/**", "doc/**", "*.md"]
DEFAULT_EXCLUDES = [
    "CHANGELOG*", "node_modules/**", "_site/**", "site/**", "build/**", ".docusaurus/**",
]
PRUNED_DIRS = frozenset({".git", ".hg", ".svn"})


@dataclass(frozen=True)
class Section:
    path: str
    anchor: str
    title: str
    start_line: int
    end_line: int
    text: str


# ---------------------------------------------------------------- file discovery

@functools.lru_cache(maxsize=None)
def _glob_regex(glob: str) -> re.Pattern:
    out, i = [], 0
    while i < len(glob):
        if glob.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif glob.startswith("**", i):
            out.append(".*")
            i += 2
        elif glob[i] == "*":
            out.append("[^/]*")
            i += 1
        elif glob[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(glob[i]))
            i += 1
    return re.compile("".join(out) + r"\Z")


def _matches(rel: str, glob: str, anywhere: bool) -> bool:
    if _glob_regex(glob).match(rel):
        return True
    if not anywhere:
        return False
    if "/" not in glob:
        return bool(_glob_regex(glob).match(PurePosixPath(rel).name))
    return bool(_glob_regex("**/" + glob).match(rel))


def _dir_excluded(parent: str, name: str, excludes: list[str]) -> bool:
    """True when a `dir/**` exclude covers everything below this directory."""
    rel = name if parent == "." else f"{parent}/{name}"
    return any(g.endswith("/**") and _matches(rel + "/_", g, True) for g in excludes)


def find_doc_files(root: Path, globs: list[str], excludes: list[str]) -> list[Path]:
    """Doc files under root matching any glob and no exclude, sorted by POSIX path.

    Includes match from the root; excludes match at any depth.
    """
    found: list[tuple[str, Path]] = []
    for dirpath, dirnames, filenames in os.walk(root):
        here = Path(dirpath).relative_to(root).as_posix()
        dirnames[:] = sorted(
            d for d in dirnames
            if d not in PRUNED_DIRS and not _dir_excluded(here, d, excludes)
        )
        for name in filenames:
            path = Path(dirpath) / name
            if path.suffix.lower() not in DOC_EXTENSIONS:
                continue
            rel = path.relative_to(root).as_posix()
            if any(_matches(rel, g, False) for g in globs) and not any(
                _matches(rel, g, True) for g in excludes
            ):
                found.append((rel, path))
    return [p for _, p in sorted(found)]


def read_doc(path: Path) -> str | None:
    """File text decoded as UTF-8 (BOM dropped) with replacement; None for binaries and unreadable files."""
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if b"\x00" in data[:8192]:
        return None
    return data.decode("utf-8-sig", errors="replace")


# ---------------------------------------------------------------- headings

Heading = tuple  # (zero-based line index, title)

_ATX = re.compile(r"^ {0,3}#{1,6}(?:[ \t]+(.*?))?(?:[ \t]+#+)?[ \t]*$")
_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
_RST_ADORN = re.compile(r"^([=\-`:.'\"~^_*+#])\1{2,}\s*$")
_ADOC = re.compile(r"^={1,6}[ \t]+(\S.*?)[ \t]*$")
_HTML_H = re.compile(r"<h([1-6])\b[^>]*>(.*?)</h\1\s*>", re.IGNORECASE | re.DOTALL)
_TAG = re.compile(r"<[^>]+>")


def _markdown_headings(lines: list[str]) -> list[Heading]:
    found, fence = [], None
    for i, line in enumerate(lines):
        m = _FENCE.match(line)
        if m:
            marker = m.group(1)
            if fence is None:
                fence = marker
            elif marker[0] == fence[0] and len(marker) >= len(fence):
                fence = None
            continue
        if fence is None:
            h = _ATX.match(line)
            if h:
                found.append((i, (h.group(1) or "").strip()))
    return found


def _rst_headings(lines: list[str]) -> list[Heading]:
    found, i = [], 0
    while i < len(lines):
        cur = lines[i].rstrip()
        nxt = lines[i + 1].rstrip() if i + 1 < len(lines) else ""
        after = lines[i + 2].rstrip() if i + 2 < len(lines) else ""
        if _RST_ADORN.match(cur) and nxt.strip() and not _RST_ADORN.match(nxt) \
                and after[:1] == cur[:1] and _RST_ADORN.match(after):
            found.append((i, nxt.strip()))
            i += 3
        elif cur.strip() and not _RST_ADORN.match(cur) and _RST_ADORN.match(nxt) \
                and len(nxt) >= len(cur.strip()):
            found.append((i, cur.strip()))
            i += 2
        else:
            i += 1
    return found


def _adoc_headings(lines: list[str]) -> list[Heading]:
    found, in_block = [], False
    for i, line in enumerate(lines):
        if re.match(r"^(-{4,}|\.{4,})\s*$", line):
            in_block = not in_block
        elif not in_block:
            m = _ADOC.match(line)
            if m:
                found.append((i, m.group(1)))
    return found


def _html_headings(text: str) -> list[Heading]:
    found = []
    for m in _HTML_H.finditer(text):
        title = html.unescape(_TAG.sub("", m.group(2)))
        found.append((text.count("\n", 0, m.start()), " ".join(title.split())))
    return found


def _headings(suffix: str, text: str, lines: list[str]) -> list[Heading]:
    if suffix in (".html", ".htm"):
        return _html_headings(text)
    if suffix == ".rst":
        return _rst_headings(lines)
    if suffix in (".adoc", ".asciidoc"):
        return _adoc_headings(lines)
    return _markdown_headings(lines)


def slugify(title: str) -> str:
    kept = "".join(c for c in title.lower() if c.isalnum() or c in " -")
    return kept.replace(" ", "-")


def split_sections(rel_path: str, text: str) -> list[Section]:
    """Split a document into sections; text before the first heading has anchor ''."""
    lines = text.splitlines()
    suffix = PurePosixPath(rel_path).suffix.lower()
    heads = _headings(suffix, text, lines)
    starts = [(0, "")] if (not heads or heads[0][0] > 0) else []
    bounds = starts + heads
    sections, seen = [], {}
    for n, (idx, title) in enumerate(bounds):
        end = bounds[n + 1][0] if n + 1 < len(bounds) else len(lines)
        end = max(end, idx + 1)
        body = "\n".join(lines[idx:end])
        if not title and idx == 0 and starts and not body.strip():
            continue
        anchor = ""
        if title or (idx, title) in heads:
            base = slugify(title)
            count = seen.get(base, 0)
            seen[base] = count + 1
            anchor = base if count == 0 else f"{base}-{count}"
        sections.append(Section(rel_path, anchor, title, idx + 1, end, body))
    return sections
