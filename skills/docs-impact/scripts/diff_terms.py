"""Extract public terms (symbols, flags, env vars, config keys, routes, paths) from a git diff."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

STOPLIST = frozenset(
    {"main", "init", "test", "data", "name", "value", "self", "args", "none", "true", "false"}
)
MIN_LENGTH = 4
CONFIG_EXTENSIONS = frozenset({".yaml", ".yml", ".toml", ".json", ".ini"})

_ROUTE_SEGMENT = r"[A-Za-z0-9_{}<>:.-]+"

# Symbol rules are language specific: (extensions, compiled regex with the name in group 1).
SYMBOL_RULES = (
    (frozenset({".py"}), re.compile(r"^\s*(?:async\s+)?(?:def|class)\s+([A-Za-z][A-Za-z0-9_]*)")),
    (
        frozenset({".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}),
        re.compile(
            r"^\s*export\s+(?:default\s+)?(?:async\s+)?"
            r"(?:function\*?|class|const|let|var|interface|type|enum)\s+(\w+)"
        ),
    ),
    (frozenset({".go"}), re.compile(r"^func\s+(?:\([^)]*\)\s*)?([A-Z]\w*)")),
    (frozenset({".go"}), re.compile(r"^type\s+([A-Z]\w*)")),
    (
        frozenset({".java", ".cs", ".kt", ".kts"}),
        re.compile(
            r"\bpublic\s+(?:(?:static|final|abstract|sealed|partial|data|open)\s+)*"
            r"(?:class|interface|enum|record|struct|object)\s+(\w+)"
        ),
    ),
    (
        frozenset({".java", ".cs", ".kt", ".kts"}),
        re.compile(r"\bpublic\s+(?:[\w<>\[\],.?]+\s+)+?(\w+)\s*\("),
    ),
    (frozenset({".rs"}), re.compile(r"\bpub(?:\([^)]*\))?\s+(?:async\s+)?(?:fn|struct|enum)\s+(\w+)")),
)

# Language independent rules, keyed by kind.
PATTERNS = {
    "flag": (re.compile(r"(?<![\w-])(--[a-z][a-z0-9-]+)"),),
    "env": (
        re.compile(r"(?:getenv|environ(?:\.get)?|process\.env)\W{0,4}([A-Z][A-Z0-9_]{3,})"),
        re.compile(r"[\"'`]([A-Z][A-Z0-9_]{3,})[\"'`]"),
    ),
    "config_key": (re.compile(r"^\s*(?:-\s+)?[\"']?([A-Za-z_][\w.-]*)[\"']?\s*[:=]"),),
    "route": (
        re.compile(rf"[\"'`](/{_ROUTE_SEGMENT}(?:/{_ROUTE_SEGMENT})*)[\"'`]"),
    ),
}

_DIFF_HEADER = re.compile(r"^diff --git a/(.*) b/(.*)$")
_HUNK_HEADER = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


class GitError(Exception):
    """A git command failed."""


@dataclass(frozen=True)
class Term:
    text: str
    kind: str
    change: str
    file: str
    line: int


def is_test_file(path: str) -> bool:
    parts = PurePosixPath(path).parts
    name = parts[-1] if parts else path
    if name.startswith("test_") or re.search(r"_test\.[^.]+$", name):
        return True
    return any(p in ("tests", "__tests__") for p in parts[:-1])


def _keep(text: str) -> bool:
    return len(text) >= MIN_LENGTH and text.lower() not in STOPLIST


def _line_terms(path: str, content: str) -> list[tuple[str, str]]:
    """Return (text, kind) pairs found in one changed line."""
    ext = PurePosixPath(path).suffix.lower()
    found: list[tuple[str, str]] = []
    for exts, rx in SYMBOL_RULES:
        if ext in exts:
            found += [(m.group(1), "symbol") for m in rx.finditer(content)]
    for kind, rxs in PATTERNS.items():
        if kind == "config_key" and ext not in CONFIG_EXTENSIONS:
            continue
        for rx in rxs:
            for m in rx.finditer(content):
                text = m.group(1).rstrip("-") if kind == "flag" else m.group(1)
                found.append((text, kind))
    return [(t, k) for t, k in found if _keep(t)]


class _FileState:
    """Terms collected for one file of the diff."""

    def __init__(self, path: str) -> None:
        self.path = path
        self.skip = is_test_file(path)
        self.seen: dict[tuple[str, str], list] = {}  # (text, kind) -> [sides, first line]
        self.extra: list[Term] = []

    def add(self, side: str, content: str, line: int) -> None:
        if self.skip:
            return
        for key in _line_terms(self.path, content):
            entry = self.seen.setdefault(key, [set(), line])
            entry[0].add(side)

    def add_rename(self, old: str, new: str) -> None:
        if is_test_file(old) and is_test_file(new):
            return
        self.extra.append(Term(old, "path", "removed", new, 0))
        self.extra.append(Term(new, "path", "added", new, 0))

    def terms(self) -> list[Term]:
        out = list(self.extra)
        for (text, kind), (sides, line) in self.seen.items():
            change = "changed" if len(sides) == 2 else ("added" if "+" in sides else "removed")
            out.append(Term(text, kind, change, self.path, line))
        return out


def parse_diff(diff_text: str) -> list[Term]:
    """Parse the output of ``git diff --unified=0 -M`` into public terms."""
    terms: list[Term] = []
    state: _FileState | None = None
    rename_from: str | None = None
    in_hunk = binary = False
    new_line = 0
    for raw in diff_text.splitlines():
        header = _DIFF_HEADER.match(raw)
        if header:
            if state:
                terms += state.terms()
            state, rename_from, in_hunk, binary = _FileState(header.group(2)), None, False, False
            continue
        if state is None or binary:
            continue
        if raw.startswith("Binary files") or raw.startswith("GIT binary patch"):
            binary = True
            continue
        hunk = _HUNK_HEADER.match(raw)
        if hunk:
            in_hunk, new_line = True, int(hunk.group(1))
        elif in_hunk and raw[:1] in ("+", "-"):
            state.add(raw[0], raw[1:], new_line)
            new_line += raw[0] == "+"
        elif not in_hunk:
            rename_from = _header_line(state, raw, rename_from)
    if state:
        terms += state.terms()
    return terms


def _header_line(state: _FileState, raw: str, rename_from: str | None) -> str | None:
    if raw.startswith("rename from "):
        return raw[len("rename from "):]
    if raw.startswith("rename to ") and rename_from is not None:
        state.add_rename(rename_from, raw[len("rename to "):])
    elif raw.startswith("+++ b/"):
        state.path = raw[len("+++ b/"):].split("\t")[0]
        state.skip = is_test_file(state.path)
    return rename_from


def _git(repo: Path, *args: str) -> str:
    cmd = ["git", "-c", "core.quotepath=off", *args]
    try:
        proc = subprocess.run(
            cmd, cwd=str(repo), capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
    except OSError as exc:
        raise GitError(f"cannot run git: {exc}") from exc
    if proc.returncode != 0:
        raise GitError(proc.stderr.strip() or f"git exited with {proc.returncode}")
    return proc.stdout


def extract_terms(repo: Path, base: str, head: str = "HEAD") -> list[Term]:
    return parse_diff(_git(repo, "diff", "--unified=0", "-M", f"{base}...{head}"))


def changed_files(
    repo: Path, base: str, head: str = "HEAD"
) -> list[tuple[str, str, str | None]]:
    """Return (status, path, old_path) per changed file; old_path only for renames and copies."""
    out = _git(repo, "diff", "--name-status", "-M", f"{base}...{head}")
    files: list[tuple[str, str, str | None]] = []
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) >= 3 and parts[0][:1] in ("R", "C"):
            files.append((parts[0][0], parts[2], parts[1]))
        elif len(parts) >= 2:
            files.append((parts[0][:1], parts[1], None))
    return files
