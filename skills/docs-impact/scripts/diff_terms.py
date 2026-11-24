"""Extract public terms (symbols, flags, env vars, config keys, routes, paths) from a git diff.

Requires git 2.28 or later (``--end-of-options``, ``git init -b`` in the tests).
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

STOPLIST = frozenset(
    {"main", "init", "test", "data", "name", "value", "self", "args", "none", "true", "false"}
)
MIN_LENGTH = 4
GIT_TIMEOUT = 120
# Generic words that say nothing about a public contract when they are config keys.
CONFIG_KEY_STOPLIST = frozenset(
    {"version", "description", "resolved", "integrity", "dependencies", "type"}
)
DOC_EXTENSIONS = frozenset(
    {".md", ".mdx", ".markdown", ".rst", ".adoc", ".asciidoc", ".html", ".htm"}
)
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
_HUNK_HEADER = re.compile(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@")


class GitError(Exception):
    """A git command failed."""


@dataclass(frozen=True)
class Term:
    """A public term found in the diff.

    ``line`` is the line in the new file for ``added`` and ``changed`` terms and the line in
    the old file for ``removed`` ones. Path terms (renames) carry ``line=0``.
    """

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


def is_generated_file(path: str) -> bool:
    name = PurePosixPath(path).name.lower()
    return name.endswith(".lock") or "-lock." in name or ".min." in name


def is_ignored(path: str) -> bool:
    """Files that yield no terms: tests, documentation, lockfiles and minified output."""
    return (
        is_test_file(path)
        or is_generated_file(path)
        or PurePosixPath(path).suffix.lower() in DOC_EXTENSIONS
    )


def _keep(text: str, kind: str) -> bool:
    if len(text) < MIN_LENGTH or text.lower() in STOPLIST:
        return False
    return not (kind == "config_key" and text.lower() in CONFIG_KEY_STOPLIST)


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
    return [(t, k) for t, k in found if _keep(t, k)]


class _FileState:
    """Terms collected for one file of the diff."""

    def __init__(self, path: str) -> None:
        self.path = path
        self.skip = is_ignored(path)
        # (text, kind) -> {side: first line on that side}
        self.seen: dict[tuple[str, str], dict[str, int]] = {}
        self.extra: list[Term] = []

    def add(self, side: str, content: str, line: int) -> None:
        if self.skip:
            return
        for key in _line_terms(self.path, content):
            self.seen.setdefault(key, {}).setdefault(side, line)

    def add_rename(self, old: str, new: str) -> None:
        if is_ignored(old) and is_ignored(new):
            return
        self.extra.append(Term(old, "path", "removed", new, 0))
        self.extra.append(Term(new, "path", "added", new, 0))

    def terms(self) -> list[Term]:
        out = list(self.extra)
        for (text, kind), lines in self.seen.items():
            change = "changed" if len(lines) == 2 else ("added" if "+" in lines else "removed")
            out.append(Term(text, kind, change, self.path, lines.get("+", lines.get("-", 0))))
        return out


def parse_diff(diff_text: str) -> list[Term]:
    """Parse the output of ``git diff --unified=0 -M`` into public terms."""
    terms: list[Term] = []
    state: _FileState | None = None
    rename_from: str | None = None
    in_hunk = binary = False
    old_line = new_line = 0
    for raw in diff_text.splitlines():
        if raw.startswith("diff --git "):
            if state:
                terms += state.terms()
            header = _DIFF_HEADER.match(raw)
            # A header git quoted (odd characters in the path) is skipped, not misparsed.
            state = _FileState(header.group(2)) if header else None
            rename_from, in_hunk, binary = None, False, False
            continue
        if state is None or binary:
            continue
        if raw.startswith("Binary files") or raw.startswith("GIT binary patch"):
            binary = True
            continue
        hunk = _HUNK_HEADER.match(raw)
        if hunk:
            in_hunk, old_line, new_line = True, int(hunk.group(1)), int(hunk.group(2))
        elif in_hunk and raw[:1] in ("+", "-"):
            if raw[0] == "+":
                state.add("+", raw[1:], new_line)
                new_line += 1
            else:
                state.add("-", raw[1:], old_line)
                old_line += 1
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
        state.skip = is_ignored(state.path)
    return rename_from


def run_git(repo: Path, *args: str) -> str:
    """Stdout of a git command in repo; GitError on failure or timeout."""
    cmd = ["git", "-c", "core.quotepath=off", *args]
    try:
        proc = subprocess.run(
            cmd, cwd=str(repo), capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=GIT_TIMEOUT,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise GitError(f"cannot run git: {exc}") from exc
    if proc.returncode != 0:
        raise GitError(proc.stderr.strip() or f"git exited with {proc.returncode}")
    return proc.stdout


def extract_terms(repo: Path, base: str, head: str = "HEAD") -> list[Term]:
    out = run_git(
        repo, "diff", "--unified=0", "-M", "--no-color", "--no-ext-diff", "--no-textconv",
        "--src-prefix=a/", "--dst-prefix=b/", "--end-of-options", f"{base}...{head}",
    )
    return parse_diff(out)


def changed_files(
    repo: Path, base: str, head: str = "HEAD"
) -> list[tuple[str, str, str | None]]:
    """Return (status, path, old_path) per changed file; old_path only for renames and copies."""
    out = run_git(repo, "diff", "--name-status", "-M", "--end-of-options", f"{base}...{head}")
    files: list[tuple[str, str, str | None]] = []
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) >= 3 and parts[0][:1] in ("R", "C"):
            files.append((parts[0][0], parts[2], parts[1]))
        elif len(parts) >= 2:
            files.append((parts[0][:1], parts[1], None))
    return files
