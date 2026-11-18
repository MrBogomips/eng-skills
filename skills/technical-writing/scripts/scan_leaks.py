#!/usr/bin/env python3
"""Find project references in text that reaches a product's users.

Scans only the parts of each file that end up in published documentation:
documentation comments (Go comments above exported names, ///, ''', /** */,
Python docstrings of public scopes), the string values of API metadata
(WithSummary, @Operation, summary=/description=), and whole files that are
published as they are (OpenAPI/AsyncAPI documents, GraphQL schemas, proto
files, and any file matched by --whole). Implementation comments (//, #,
/* */) are internal and are never scanned.

Exit status: 0 when nothing is found, 1 when something is found, 2 on usage
or input errors. Warnings (files skipped or only partly scanned) go to stderr
and do not change the exit status.
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
from typing import List, Optional, Sequence


@dataclass(frozen=True)
class Rule:
    name: str
    regex: re.Pattern


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    match: str
    rule: str


@dataclass(frozen=True)
class Snippet:
    """Text that reaches published docs, with the line it comes from."""

    line: int
    text: str


BUILTIN_RULES = (
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
DEFAULT_ALLOW = (
    r"(?:SHA|UTF|ISO|RFC|IEC|IEEE|AES|CVE|ECMA|PKCS|TLS|HTTP|IPV|MD|BS|EN|DIN|PEP|JSR|ES|WCAG)-\d+",
)

NAMED_PATTERN = re.compile(r"^([a-z][a-z0-9-]*)=(.+)$", re.DOTALL)
STRING_LITERAL = re.compile(r'"(?:\\.|[^"\\\n])*"|\'(?:\\.|[^\'\\\n])*\'|`(?:\\.|[^`\\\n])*`')
LINE_COMMENT = re.compile(r"//.*$|(?<!\S)#.*$")

DOC_BLOCK_OPEN = re.compile(r"^\s*/\*(?:\*(?![*/])|!)")
SLASH_DOC = re.compile(r"^\s*///(?!/)")
BANG_DOC = re.compile(r"^\s*//!")
VB_DOC = re.compile(r"^\s*'''")
API_METADATA = re.compile(
    r"\.With(?:Summary|Description|Tags|DisplayName)\s*\("
    r"|@(?:Operation|Schema|ApiOperation|ApiProperty|ApiResponse|ApiParam|Parameter|Tag)\s*\("
    r"|\[(?:Description|Display|SwaggerOperation)\s*\("
    r"|\b(?:summary|description)[\"']?\s*(?::|=(?!=))"
)
SPEC_YAML = re.compile(r"^(?:openapi|swagger|asyncapi)\s*:", re.MULTILINE)
SPEC_JSON = re.compile(r'"(?:openapi|swagger|asyncapi)"\s*:')

GO_FUNC = re.compile(r"^func\s+(?:\((?P<recv>[^)]*)\)\s*)?(?P<name>\w+)")
GO_DECL = re.compile(r"^(?:type|var|const)\s+([A-Z]\w*)")
GO_STRUCT_OPEN = re.compile(r"^type\s+(\w+)(?:\[[^\]]*\])?\s+(?:struct|interface)\s*\{\s*$")
GO_PAREN_OPEN = re.compile(r"^(?:const|var|type)\s*\(\s*$")
GO_MEMBER = re.compile(r"^\s+([A-Z]\w*)\b")
GO_RECEIVER_TYPE = re.compile(r"(?:\w+\s+)?\*?\s*([A-Za-z_]\w*)")

C_FAMILY_EXT = {".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".hh", ".m", ".mm"}
SLASH_DOC_EXT = {".cs", ".fs", ".fsx", ".swift", ".dart", ".rs"} | C_FAMILY_EXT
BANG_DOC_EXT = {".rs"} | C_FAMILY_EXT
VB_EXT = {".vb"}
DOC_BLOCK_EXT = {
    ".java", ".kt", ".kts", ".scala", ".groovy", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs",
    ".php", ".swift", ".dart", ".rs", ".cs",
} | C_FAMILY_EXT
METADATA_EXT = (DOC_BLOCK_EXT | SLASH_DOC_EXT | VB_EXT) - {".rs"}
WHOLE_EXT = {".graphql", ".gql", ".proto"}
SPEC_EXT = {".yaml", ".yml", ".json"}
KNOWN_EXT = DOC_BLOCK_EXT | SLASH_DOC_EXT | VB_EXT | WHOLE_EXT | SPEC_EXT | {".py", ".go"}
METADATA_KEYS = {"summary", "description"}


# --- rules -----------------------------------------------------------------


def build_rules(patterns: Sequence[str]) -> List[Rule]:
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


def build_allowlist(patterns: Sequence[str]) -> List[re.Pattern]:
    return [_compile(p) for p in (*DEFAULT_ALLOW, *patterns)]


def _compile(expr: str) -> re.Pattern:
    try:
        return re.compile(expr)
    except re.error as exc:
        raise ValueError(f"invalid pattern {expr!r}: {exc}") from exc


# --- what gets published -----------------------------------------------------


def published_snippets(
    name: str, text: str, whole: bool = False, warnings: Optional[List[str]] = None
) -> Optional[List[Snippet]]:
    """Return the published text of a file, or None if its type is unknown."""
    warnings = [] if warnings is None else warnings
    lines = text.split("\n")
    ext = Path(name).suffix.lower()
    if whole or ext in WHOLE_EXT or _is_api_spec(ext, text):
        return [Snippet(i, line) for i, line in enumerate(lines, 1)]
    if ext not in KNOWN_EXT:
        return None
    if ext == ".py":
        return _python_snippets(name, text, lines, warnings)
    found: List[Snippet] = []
    if ext == ".go":
        found += _full_lines(lines, _go_doc_lines(lines))
    if ext in SLASH_DOC_EXT:
        found += _full_lines(lines, _matching_lines(lines, SLASH_DOC))
    if ext in BANG_DOC_EXT:
        found += _full_lines(lines, _matching_lines(lines, BANG_DOC))
    if ext in VB_EXT:
        found += _full_lines(lines, _matching_lines(lines, VB_DOC))
    if ext in DOC_BLOCK_EXT:
        found += _full_lines(lines, _doc_block_lines(lines))
    if ext in METADATA_EXT:
        found += _metadata_snippets(lines)
    return found


def _is_api_spec(ext: str, text: str) -> bool:
    if ext not in SPEC_EXT:
        return False
    pattern = SPEC_JSON if ext == ".json" else SPEC_YAML
    return bool(pattern.search(text))


def _full_lines(lines: Sequence[str], numbers: set) -> List[Snippet]:
    return [Snippet(n, lines[n - 1]) for n in sorted(numbers)]


def _matching_lines(lines: Sequence[str], pattern: re.Pattern) -> set:
    return {i for i, line in enumerate(lines, 1) if pattern.match(line)}


def _doc_block_lines(lines: Sequence[str]) -> set:
    """Lines of /** */ and /*! */ blocks whose opener starts a line."""
    found: set = set()
    i = 0
    while i < len(lines):
        opener = DOC_BLOCK_OPEN.match(lines[i])
        if not opener:
            i += 1
            continue
        j, rest = i, lines[i][opener.end():]
        while "*/" not in rest and j + 1 < len(lines):
            j += 1
            rest = lines[j]
        found.update(range(i + 1, j + 2))
        i = j + 1
    return found


# --- Go --------------------------------------------------------------------------


def _go_doc_lines(lines: Sequence[str]) -> set:
    """Comments directly above exported declarations, exported fields and the package clause."""
    found: set = set()
    group: Optional[bool] = None  # None outside a group, else whether its members are published
    for i, line in enumerate(lines):
        if group is not None and line[:1] in ("}", ")"):
            group = None
        if _go_is_documented(line, group):
            found |= _go_comment_above(lines, i)
        group = _go_group_after(line, group)
    return found


def _go_is_documented(line: str, group: Optional[bool]) -> bool:
    func = GO_FUNC.match(line)
    if func:
        return _go_exported(func.group("name")) and _go_receiver_exported(func.group("recv"))
    if GO_DECL.match(line) or line.startswith("package "):
        return True
    return bool(group and GO_MEMBER.match(line))


def _go_group_after(line: str, group: Optional[bool]) -> Optional[bool]:
    struct = GO_STRUCT_OPEN.match(line)
    if struct:
        return _go_exported(struct.group(1))
    if GO_PAREN_OPEN.match(line):
        return True
    return group


def _go_exported(name: str) -> bool:
    return name[:1].isupper()


def _go_receiver_exported(receiver: Optional[str]) -> bool:
    if receiver is None:
        return True
    match = GO_RECEIVER_TYPE.match(receiver.strip())
    return bool(match and _go_exported(match.group(1)))


def _go_comment_above(lines: Sequence[str], index: int) -> set:
    run: set = set()
    j = index - 1
    if j >= 0 and lines[j].rstrip().endswith("*/"):
        while j >= 0:
            run.add(j + 1)
            if "/*" in lines[j]:
                return run
            j -= 1
        return run
    while j >= 0 and lines[j].lstrip().startswith("//"):
        run.add(j + 1)
        j -= 1
    return run


# --- API metadata in languages other than Python -------------------------------


def _metadata_snippets(lines: Sequence[str], max_span: int = 50) -> List[Snippet]:
    """String literals of API metadata calls, following open parentheses across lines."""
    found: List[Snippet] = []
    for i, line in enumerate(lines):
        trigger = API_METADATA.search(line)
        if not trigger:
            continue
        depth = 0
        for j in range(i, min(i + max_span, len(lines))):
            segment = lines[j][trigger.start():] if j == i else lines[j]
            found.append(Snippet(j + 1, _string_contents(segment)))
            code = LINE_COMMENT.sub("", STRING_LITERAL.sub('""', segment))
            depth += code.count("(") - code.count(")")
            if depth <= 0:
                break
    return found


def _string_contents(segment: str) -> str:
    return " ".join(m.group(0)[1:-1] for m in STRING_LITERAL.finditer(segment))


# --- Python --------------------------------------------------------------------


def _python_snippets(name: str, text: str, lines: Sequence[str], warnings: List[str]) -> List[Snippet]:
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError) as exc:
        warnings.append(f"cannot parse {name} ({exc.__class__.__name__}); docstrings not scanned")
        return _metadata_snippets(lines)
    found: List[Snippet] = []
    _python_docstrings(tree, lines, found)
    for node in ast.walk(tree):
        for value in _python_metadata_values(node):
            found += _python_string_snippets(value, lines)
    return found


def _python_docstrings(scope: ast.AST, lines: Sequence[str], found: List[Snippet]) -> None:
    """Docstrings of the module, public classes and their public methods; never inside functions."""
    body = getattr(scope, "body", [])
    if body and _is_string(body[0]):
        found += _python_string_snippets(body[0].value, lines)
    for node in body:
        if isinstance(node, ast.ClassDef) and not _is_private(node.name):
            _python_docstrings(node, lines, found)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not _is_private(node.name):
            if node.body and _is_string(node.body[0]):
                found += _python_string_snippets(node.body[0].value, lines)


def _python_metadata_values(node: ast.AST) -> List[ast.AST]:
    if isinstance(node, ast.keyword) and node.arg in METADATA_KEYS:
        return [node.value]
    if isinstance(node, ast.Dict):
        return [
            value
            for key, value in zip(node.keys, node.values)
            if isinstance(key, ast.Constant) and key.value in METADATA_KEYS
        ]
    return []


def _python_string_snippets(value: ast.AST, lines: Sequence[str]) -> List[Snippet]:
    first, last = value.lineno, value.end_lineno or value.lineno
    if isinstance(value, ast.Constant) and isinstance(value.value, str):
        parts = value.value.split("\n")
        if len(parts) == last - first + 1:
            return [Snippet(first + k, part) for k, part in enumerate(parts)]
    return [Snippet(n, _string_contents(lines[n - 1])) for n in range(first, last + 1)]


def _is_string(stmt: ast.stmt) -> bool:
    return isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str)


def _is_private(name: str) -> bool:
    return name.startswith("_") and not (name.startswith("__") and name.endswith("__"))


# --- matching ----------------------------------------------------------------------


def scan_text(
    name: str,
    text: str,
    rules: Sequence[Rule],
    allow: Sequence[re.Pattern],
    whole: bool = False,
    warnings: Optional[List[str]] = None,
) -> List[Finding]:
    warnings = [] if warnings is None else warnings
    snippets = published_snippets(name, text, whole, warnings)
    if snippets is None:
        warnings.append(f"skipped {name}: no published regions known for this file type (use --whole if it is published)")
        return []
    findings = {}
    for snippet in snippets:
        for match, rule in _snippet_matches(snippet.text, rules, allow):
            findings.setdefault((snippet.line, match, rule), Finding(name, snippet.line, match, rule))
    return sorted(findings.values(), key=lambda f: f.line)


def _snippet_matches(text: str, rules: Sequence[Rule], allow: Sequence[re.Pattern]) -> List[tuple]:
    """Non-overlapping matches in position order; on overlap the earlier rule wins."""
    candidates = []
    for priority, rule in enumerate(rules):
        for m in rule.regex.finditer(text):
            if m.group(0) and not any(a.fullmatch(m.group(0)) for a in allow):
                candidates.append((priority, m.start(), m.end(), m.group(0), rule.name))
    kept, taken = [], []
    for _, start, end, matched, rule in sorted(candidates):
        if all(end <= s or start >= e for s, e in taken):
            taken.append((start, end))
            kept.append((start, matched, rule))
    return [(matched, rule) for _, matched, rule in sorted(kept)]


# --- command line ------------------------------------------------------------------


def changed_files(base: str) -> List[str]:
    """Files changed since BASE plus untracked files, relative to the current directory."""
    top = _git("rev-parse", "--show-toplevel").strip()
    names = _git("-C", top, "diff", "--name-only", "-z", "--diff-filter=ACMR", base).split("\0")
    names += _git("-C", top, "ls-files", "--others", "--exclude-standard", "-z").split("\0")
    return [os.path.relpath(os.path.join(top, n)) for n in dict.fromkeys(names) if n]


def _git(*args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-c", "core.quotePath=false", *args], capture_output=True, text=True, encoding="utf-8"
        )
    except FileNotFoundError as exc:
        raise RuntimeError("git is not installed") from exc
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def _matches_glob(path: str, glob: str) -> bool:
    candidates = {path, os.path.relpath(path), os.path.abspath(path)}
    globs = {glob, glob[3:]} if glob.startswith("**/") else {glob}
    return any(fnmatch.fnmatch(c, g) for c in candidates for g in globs)


def _unique_files(paths: Sequence[str]) -> List[str]:
    seen, unique = set(), []
    for path in paths:
        key = os.path.realpath(path)
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


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


def _scan_files(files: Sequence[str], args: argparse.Namespace, rules, allow, warnings: List[str]) -> List[Finding]:
    findings: List[Finding] = []
    used_globs: set = set()
    for path in files:
        if not os.path.isfile(path):
            if not os.path.exists(path):
                raise OSError(f"cannot read {path}: no such file")
            warnings.append(f"skipped {path}: not a file")
            continue
        text = Path(path).read_text(encoding="utf-8-sig", errors="replace")
        globs = {g for g in args.whole if _matches_glob(path, g)}
        used_globs |= globs
        findings.extend(scan_text(path, text, rules, allow, whole=bool(globs), warnings=warnings))
    warnings.extend(f"--whole {g!r} matched no file" for g in args.whole if g not in used_globs)
    return findings


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    warnings: List[str] = []
    try:
        rules = build_rules(args.pattern)
        allow = build_allowlist(args.allow)
        files = _unique_files(list(args.files) + (changed_files(args.git_diff) if args.git_diff else []))
        if not files:
            print("scan_leaks: no files to scan (pass files or --git-diff BASE)", file=sys.stderr)
            return 2
        findings = _scan_files(files, args, rules, allow, warnings)
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"scan_leaks: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # report, never let a crash read as "findings" (exit 1)
        print(f"scan_leaks: unexpected error: {exc.__class__.__name__}: {exc}", file=sys.stderr)
        return 2
    for warning in warnings:
        print(f"scan_leaks: warning: {warning}", file=sys.stderr)
    for f in findings:
        print(f"{f.path}:{f.line}: {f.match} [{f.rule}]")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
