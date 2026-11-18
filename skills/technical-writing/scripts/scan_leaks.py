#!/usr/bin/env python3
"""Find project references in text that reaches a product's users.

Scans only the parts of each file that end up in published documentation:
documentation comments (Go comments above exported names, ///, /** */,
Python docstrings), API metadata strings (WithSummary, @Operation,
summary=/description=), and whole files that are published as they are
(OpenAPI/AsyncAPI documents, GraphQL schemas, proto files, and any file
matched by --whole). Implementation comments (//, #, /* */) are internal and
are never scanned.

Exit status: 0 when nothing is found, 1 when something is found, 2 on usage
or input errors.
"""

from __future__ import annotations

import argparse
import ast
import fnmatch
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


@dataclass(frozen=True)
class Rule:
    name: str
    regex: re.Pattern[str]


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    match: str
    rule: str


BUILTIN_RULES: tuple[tuple[str, str], ...] = (
    ("requirement-id", r"\b(?:N?FR|BFR|US|REQ|OQ|AD)[-_]?\d+(?:\.\d+)*\b|\bADR[-_ ]?\d+\b"),
    ("tracker-key", r"\b[A-Z][A-Z0-9]{1,9}-\d+\b"),
    ("issue-ref", r"(?<![\w&#])#\d{2,}\b"),
    ("internal-host", r"\b[\w-]+(?:\.[\w-]+)*\.(?:internal|local|corp|lan|intranet)\b"),
    (
        "private-ip",
        r"\b(?:10(?:\.\d{1,3}){3}|172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2}|192\.168(?:\.\d{1,3}){2})\b",
    ),
    ("work-marker", r"\b(?:TODO|FIXME|HACK|XXX)\b"),
)

# Standard names shaped like identifiers (SHA-256, RFC-9457, CVE-2024-1234).
DEFAULT_ALLOW: tuple[str, ...] = (
    r"(?:SHA|UTF|ISO|RFC|IEC|IEEE|AES|CVE|ECMA|PKCS|TLS|HTTP|IPV|MD|BS|EN|DIN|PEP|JSR|ES|WCAG)-\d+",
)

NAMED_PATTERN = re.compile(r"^([a-z][a-z0-9-]*)=(.+)$", re.DOTALL)

DOC_BLOCK = re.compile(r"/\*[*!](?!/).*?\*/", re.DOTALL)
API_METADATA = re.compile(
    r"\.With(?:Summary|Description|Tags|DisplayName)\s*\("
    r"|@(?:Operation|Schema|ApiOperation|ApiProperty|ApiResponse|ApiParam|Parameter|Tag)\s*\("
    r"|\[(?:Description|Display|SwaggerOperation)\s*\("
    r"|\b(?:summary|description)[\"']?\s*[=:]"
)
SPEC_YAML = re.compile(r"^(?:openapi|swagger|asyncapi)\s*:", re.MULTILINE)
SPEC_JSON = re.compile(r'"(?:openapi|swagger|asyncapi)"\s*:')

GO_TOP_DECL = re.compile(r"^(?:func\s+(?:\([^)]*\)\s*)?|type\s+|var\s+|const\s+)([A-Z]\w*)")
GO_GROUP_OPEN = re.compile(r"^(?:type\s+\w+\s+(?:struct|interface)\s*\{|const\s*\(|var\s*\()\s*$")
GO_GROUP_MEMBER = re.compile(r"^\s+([A-Z]\w*)\b")

TRIPLE_SLASH_EXT = {".cs", ".fs", ".fsx", ".vb", ".swift"}
RUST_EXT = {".rs"}
DOC_BLOCK_EXT = {".java", ".kt", ".kts", ".scala", ".groovy", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".php", ".swift"}
METADATA_EXT = DOC_BLOCK_EXT | TRIPLE_SLASH_EXT | RUST_EXT | {".py", ".go"}
WHOLE_EXT = {".graphql", ".gql", ".proto"}
SPEC_EXT = {".yaml", ".yml", ".json"}


def build_rules(patterns: Sequence[str]) -> list[Rule]:
    """Project patterns first (most specific), then the built-in rules.

    A pattern is either REGEX or NAME=REGEX, with NAME in lower case.
    Raises ValueError on an invalid regular expression.
    """
    rules = []
    for raw in patterns:
        named = NAMED_PATTERN.match(raw)
        name, expr = (named.group(1), named.group(2)) if named else ("project", raw)
        rules.append(Rule(name, _compile(expr)))
    rules.extend(Rule(name, re.compile(expr)) for name, expr in BUILTIN_RULES)
    return rules


def build_allowlist(patterns: Sequence[str]) -> list[re.Pattern[str]]:
    return [_compile(p) for p in (*DEFAULT_ALLOW, *patterns)]


def _compile(expr: str) -> re.Pattern[str]:
    try:
        return re.compile(expr)
    except re.error as exc:
        raise ValueError(f"invalid pattern {expr!r}: {exc}") from exc


def published_lines(name: str, text: str, whole: bool = False) -> set[int]:
    """Return the 1-based numbers of the lines that reach published docs."""
    lines = text.splitlines()
    ext = Path(name).suffix.lower()
    if whole or ext in WHOLE_EXT or _is_api_spec(ext, text):
        return set(range(1, len(lines) + 1))
    found: set[int] = set()
    if ext == ".go":
        found |= _go_doc_lines(lines)
    if ext in TRIPLE_SLASH_EXT:
        found |= _prefixed_lines(lines, ("///",))
    if ext in RUST_EXT:
        found |= _prefixed_lines(lines, ("///", "//!"))
    if ext in DOC_BLOCK_EXT or ext in RUST_EXT:
        found |= _doc_block_lines(text)
    if ext == ".py":
        found |= _python_docstring_lines(text)
    if ext in METADATA_EXT:
        found |= _metadata_lines(lines)
    return found


def _is_api_spec(ext: str, text: str) -> bool:
    if ext not in SPEC_EXT:
        return False
    pattern = SPEC_JSON if ext == ".json" else SPEC_YAML
    return bool(pattern.search(text))


def _prefixed_lines(lines: Sequence[str], prefixes: tuple[str, ...]) -> set[int]:
    return {i for i, line in enumerate(lines, 1) if line.lstrip().startswith(prefixes)}


def _doc_block_lines(text: str) -> set[int]:
    found: set[int] = set()
    for block in DOC_BLOCK.finditer(text):
        first = text.count("\n", 0, block.start()) + 1
        last = first + block.group(0).count("\n")
        found.update(range(first, last + 1))
    return found


def _go_doc_lines(lines: Sequence[str]) -> set[int]:
    """Comment runs directly above exported declarations, fields and the package clause."""
    found: set[int] = set()
    in_group = False
    for i, line in enumerate(lines):
        if in_group and line[:1] in ("}", ")"):
            in_group = False
        documented = bool(
            GO_TOP_DECL.match(line)
            or line.startswith("package ")
            or (in_group and GO_GROUP_MEMBER.match(line))
        )
        if documented:
            found |= _comment_run_above(lines, i)
        if GO_GROUP_OPEN.match(line):
            in_group = True
    return found


def _comment_run_above(lines: Sequence[str], index: int) -> set[int]:
    run: set[int] = set()
    j = index - 1
    while j >= 0 and lines[j].lstrip().startswith("//"):
        run.add(j + 1)
        j -= 1
    return run


def _python_docstring_lines(text: str) -> set[int]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return set()
    found: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if _is_private(getattr(node, "name", "")):
            continue
        first = node.body[0] if node.body else None
        if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
            found.update(range(first.lineno, (first.end_lineno or first.lineno) + 1))
    return found


def _is_private(name: str) -> bool:
    return name.startswith("_") and not (name.startswith("__") and name.endswith("__"))


def _metadata_lines(lines: Sequence[str], max_span: int = 50) -> set[int]:
    """Lines holding API metadata strings, following open parentheses across lines."""
    found: set[int] = set()
    for i, line in enumerate(lines):
        trigger = API_METADATA.search(line)
        if not trigger:
            continue
        depth = 0
        for j in range(i, min(i + max_span, len(lines))):
            segment = lines[j][trigger.start():] if j == i else lines[j]
            depth += segment.count("(") - segment.count(")")
            found.add(j + 1)
            if depth <= 0:
                break
    return found


def scan_text(
    name: str,
    text: str,
    rules: Sequence[Rule],
    allow: Sequence[re.Pattern[str]],
    whole: bool = False,
) -> list[Finding]:
    lines = text.splitlines()
    findings: list[Finding] = []
    for number in sorted(published_lines(name, text, whole)):
        line = lines[number - 1]
        for _, match, rule in _line_matches(line, rules, allow):
            findings.append(Finding(name, number, match, rule))
    return findings


def _line_matches(
    line: str, rules: Sequence[Rule], allow: Sequence[re.Pattern[str]]
) -> list[tuple[int, str, str]]:
    """Non-overlapping matches in position order; on overlap the earlier rule wins."""
    candidates = []
    for priority, rule in enumerate(rules):
        for m in rule.regex.finditer(line):
            if m.group(0) and not any(a.fullmatch(m.group(0)) for a in allow):
                candidates.append((m.start(), priority, m.end(), m.group(0), rule.name))
    kept: list[tuple[int, str, str]] = []
    taken: list[tuple[int, int]] = []
    for start, _, end, text, rule in sorted(candidates, key=lambda c: (c[1], c[0])):
        if all(end <= s or start >= e for s, e in taken):
            taken.append((start, end))
            kept.append((start, text, rule))
    return sorted(kept)


def changed_files(base: str) -> list[str]:
    """Files changed since BASE plus untracked files, relative to the current directory."""
    top = _git("rev-parse", "--show-toplevel").strip()
    names = _git("-C", top, "diff", "--name-only", "--diff-filter=ACMR", base).splitlines()
    names += _git("-C", top, "ls-files", "--others", "--exclude-standard").splitlines()
    return [os.path.relpath(os.path.join(top, n)) for n in dict.fromkeys(names) if n]


def _git(*args: str) -> str:
    result = subprocess.run(["git", *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="scan_leaks",
        description="Report project references in the published parts of files.",
    )
    parser.add_argument("files", nargs="*", help="files to scan")
    parser.add_argument("--git-diff", metavar="BASE", help="also scan files changed since BASE, and untracked files")
    parser.add_argument(
        "--whole", action="append", default=[], metavar="GLOB",
        help="treat matching files as published in full (manuals, release notes); repeatable",
    )
    parser.add_argument(
        "--pattern", action="append", default=[], metavar="[NAME=]REGEX",
        help="project reference pattern, e.g. 'story=PRJ-[A-Z]{3}-\\d+'; repeatable",
    )
    parser.add_argument(
        "--allow", action="append", default=[], metavar="REGEX",
        help="matches that are fine in public text, e.g. 'EU-27'; repeatable",
    )
    return parser.parse_intermixed_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    try:
        rules = build_rules(args.pattern)
        allow = build_allowlist(args.allow)
        files = list(args.files) + (changed_files(args.git_diff) if args.git_diff else [])
    except (ValueError, RuntimeError) as exc:
        print(f"scan_leaks: {exc}", file=sys.stderr)
        return 2
    if not files:
        print("scan_leaks: no files to scan (pass files or --git-diff BASE)", file=sys.stderr)
        return 2
    findings = []
    for path in files:
        try:
            text = Path(path).read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            print(f"scan_leaks: cannot read {path}: {exc.strerror}", file=sys.stderr)
            return 2
        whole = any(fnmatch.fnmatch(path, glob) for glob in args.whole)
        findings.extend(scan_text(path, text, rules, allow, whole=whole))
    for f in findings:
        print(f"{f.path}:{f.line}: {f.match} [{f.rule}]")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
