#!/usr/bin/env python3
"""Check that a rewritten Markdown text keeps the technical content of the original.

Compares the items a rewrite, a translation or a delegated edit must not lose or
invent: inline code, fenced code blocks, link and image targets, image captions,
environment variables written in prose, numbers (with their units) in prose, table
cells, table shapes and admonitions. A fact counts as kept when its value still
appears anywhere in AFTER, in any form (prose, table cell, code block), so a rewrite
may drop repetitions and reshape the page; --strict-count compares occurrences.
Table shapes and admonitions are always counted. Heading anchors are compared too,
as warnings by default, because other pages may link to them.

Exit status: 0 when nothing was lost or added, 1 when something was, 2 on usage or
input errors. Warnings go to stderr and do not change the exit status.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class Item:
    kind: str
    value: str
    line: int


@dataclass(frozen=True)
class Finding:
    change: str  # "missing" (in BEFORE only) or "added" (in AFTER only)
    kind: str
    value: str
    line: int


FENCE_OPEN = re.compile(r"^\s*(`{3,}|~{3,})(.*)$")
TEXT = r"\[(?:[^\[\]]|\[[^\[\]]*\])*\]"  # link text, one level of nested brackets
TARGET = r"\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)"
INLINE_CODE = re.compile(r"(?<!`)(`+)(?!`)([\s\S]+?)(?<!`)\1(?!`)")
IMAGE = re.compile(r"!(" + TEXT + r")" + TARGET)
LINK = re.compile(r"(?<!!)" + TEXT + TARGET)
AUTOLINK = re.compile(r"<(https?://[^>\s]+)>")
REF_DEF = re.compile(r"^\s{0,3}\[[^\]]+\]:\s*<?(\S+?)>?(?:\s+\"[^\"]*\")?\s*$")
ENV_VAR = re.compile(r"\b[A-Z][A-Z0-9]*_[A-Z0-9_]*[A-Z0-9]\b")
UNITS = r"(?:ms|s|sec|min|h|d|KiB|MiB|GiB|TiB|KB|MB|GB|TB|B|%|x|px|m)"
NUMBER = re.compile(r"(?<![\w.,])(\d+(?:[.,]\d+)*)(?:\s?(" + UNITS + r"))?(?![\w])")
LIST_MARKER = re.compile(r"^\s*(?:\d+[.)]|[-*+])\s+", re.MULTILINE)
HEADING = re.compile(r"^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$")
HTML_COMMENT = re.compile(r"<!--[\s\S]*?-->")
META_LINE = re.compile(r"^([A-Za-z_][\w-]*)\s*:\s*(.*)$")
CALLOUT = re.compile(r"^\s*>\s*\*\*[^*\n]+\*\*")  # "> **Note:**", "> **Nota:**": label may be translated
ADMONITION = (
    re.compile(r"^\s*>\s*\[!(\w+)\]"),
    re.compile(r"^\s*(?:!!!|\?\?\?)\s*(\w+)"),
    re.compile(r"^\s*:::\s*(\w+)"),
)
TABLE_RULE = re.compile(r"^\s*(?=.*\|)\|?\s*:?-+:?\s*(?:\|\s*:?-+:?\s*)*\|?\s*$")
CELL_SPLIT = re.compile(r"(?<!\\)\|(?=(?:[^`]*`[^`]*`)*[^`]*$)")
LIST_START = re.compile(r"^\s*(?:\d+[.)]|[-*+])\s+")


# --- extraction ---------------------------------------------------------------------


def extract(text: str) -> List[Item]:
    """Every item of TEXT that a rewrite must keep, in document order."""
    text = HTML_COMMENT.sub(lambda m: "\n" * m.group(0).count("\n"), text)
    lines = text.splitlines()
    found: List[Item] = []
    i = _front_matter(lines, found)
    paragraph: List[Tuple[int, str]] = []
    while i < len(lines):
        line = lines[i]
        if _fence_opener(line) or _table_start(lines, i) or HEADING.match(line) or not line.strip() \
                or LIST_START.match(line) or CALLOUT.match(line):
            found.extend(_paragraph(paragraph))
            paragraph = []
        if _fence_opener(line):
            i = _fenced_block(lines, i, found)
            continue
        if _table_start(lines, i):
            i = _table(lines, i, found)
            continue
        heading = HEADING.match(line)
        if heading:
            found.append(Item("anchor", _slug(heading.group(2)), i + 1))
            found.extend(_spans(heading.group(2), i + 1))
        elif REF_DEF.match(line):
            found.append(Item("link", REF_DEF.match(line).group(1), i + 1))
        elif line.strip():
            found.extend(_admonition(line, i + 1))
            paragraph.append((i + 1, line))
        i += 1
    found.extend(_paragraph(paragraph))
    return found


def _front_matter(lines: List[str], found: List[Item]) -> int:
    """YAML front matter: keys are kept as they are, values are read like prose."""
    if not lines or lines[0].strip() != "---" or len(lines) < 2 or not META_LINE.match(lines[1]):
        return 0
    for end in range(1, len(lines)):
        if lines[end].strip() == "---":
            for number in range(1, end):
                meta = META_LINE.match(lines[number])
                if meta:
                    found.append(Item("key", meta.group(1), number + 1))
                    found.extend(_spans(meta.group(2), number + 1))
            return end + 1
    return 0


def _fence_opener(line: str) -> Optional[re.Match]:
    match = FENCE_OPEN.match(line)
    if match and match.group(1)[0] == "`" and "`" in match.group(2):
        return None  # "```make``` builds" is an inline span, not a fence
    return match


def _fenced_block(lines: List[str], start: int, found: List[Item]) -> int:
    fence = _fence_opener(lines[start]).group(1)
    closer = re.compile(r"^\s*" + re.escape(fence[0]) + "{" + str(len(fence)) + r",}\s*$")
    end = start + 1
    while end < len(lines) and not closer.match(lines[end]):
        end += 1
    found.append(Item("block", _normalize(lines[start + 1:end]), start + 1))
    return end + 1


def _table_start(lines: List[str], i: int) -> bool:
    return "|" in lines[i] and i + 1 < len(lines) and bool(TABLE_RULE.match(lines[i + 1]))


def _table(lines: List[str], start: int, found: List[Item]) -> int:
    header = _cells(lines[start])
    found.append(Item("table", f"{len(header)} cols", start + 1))
    found.extend(i for c in header for i in _spans(c, start + 1))  # header labels are prose
    end, rows = start + 2, 0
    while end < len(lines) and "|" in lines[end] and lines[end].strip():
        rows += 1
        found.extend(_cell_items(_cells(lines[end]), end + 1))
        end += 1
    found.append(Item("row", f"{rows} rows", start + 1))
    return end


def _cells(row: str) -> List[str]:
    body = row.strip()
    body = body[1:] if body.startswith("|") else body
    body = body[:-1] if body.endswith("|") and not body.endswith("\\|") else body
    return [c.strip() for c in CELL_SPLIT.split(body)]


def _cell_items(cells: List[str], number: int) -> Iterator[Item]:
    """Technical items inside each cell; a cell with none counts only when it is a single token."""
    for cell in cells:
        items = list(_spans(cell, number))
        if items:
            yield from items
        elif cell and not any(ch.isspace() for ch in cell):
            yield Item("cell", cell, number)


def _admonition(line: str, number: int) -> Iterator[Item]:
    if CALLOUT.match(line):
        yield Item("admonition", "callout", number)
        return
    for pattern in ADMONITION:
        match = pattern.match(line)
        if match:
            yield Item("admonition", match.group(1).lower(), number)
            return


def _paragraph(lines: List[Tuple[int, str]]) -> Iterator[Item]:
    """Items of consecutive prose lines read as one text, so wrapped spans and links are whole."""
    if lines:
        yield from _spans("\n".join(text for _, text in lines), lines[0][0])


def _spans(text: str, first_line: int) -> Iterator[Item]:
    """Code, images, links, env vars and numbers of TEXT, with the line each one starts on."""
    found: List[Item] = []

    def at(offset: int) -> int:
        return first_line + text.count("\n", 0, offset)

    def blank(match: re.Match) -> str:
        return re.sub(r"[^\n]", " ", match.group(0))

    prose = text
    for match in INLINE_CODE.finditer(prose):
        found.append(Item("code", " ".join(match.group(2).split()), at(match.start())))
    prose = INLINE_CODE.sub(blank, prose)
    for match in IMAGE.finditer(prose):
        found.append(Item("image", match.group(2), at(match.start())))
        caption = " ".join(match.group(1)[1:-1].split())
        if caption:
            found.append(Item("caption", caption, at(match.start())))
    prose = IMAGE.sub(blank, prose)
    for pattern in (LINK, AUTOLINK):
        for match in pattern.finditer(prose):
            found.append(Item("link", match.group(1), at(match.start())))
        prose = pattern.sub(blank, prose)
    for match in ENV_VAR.finditer(prose):
        found.append(Item("env", match.group(0), at(match.start())))
    prose = LIST_MARKER.sub(blank, prose)
    for match in NUMBER.finditer(prose):
        value = match.group(1).replace(",", ".") + (match.group(2) or "")
        found.append(Item("number", value, at(match.start())))
    return iter(sorted(found, key=lambda item: item.line))


def _normalize(block: Sequence[str]) -> str:
    return " ".join(" ".join(block).split())


def _slug(title: str) -> str:
    plain = INLINE_CODE.sub(lambda m: m.group(2), title).lower()
    plain = re.sub(r"[^\w\- ]", "", plain)
    return plain.strip().replace(" ", "-")


# --- comparison ---------------------------------------------------------------------


# Kinds whose value counts as present wherever it appears again: in prose, a table cell or a code block.
FACT_KINDS = {"code", "block", "cell", "env", "number", "link", "image", "caption"}  # "key" and the rest are counted


def compare(
    before: str, after: str, allow: Sequence[str] = (), anchors: str = "warn", strict: bool = False
) -> Tuple[List[Finding], List[str]]:
    """Findings (missing and added items) and warnings for a BEFORE → AFTER rewrite.

    By default a fact is missing only when its value no longer appears anywhere in AFTER, in any form, so a
    rewrite may drop repetitions and move a command from prose into a code block. STRICT compares counts per kind.
    """
    allowed = [re.compile(a) for a in allow]
    old, new = extract(before), extract(after)
    findings: List[Finding] = []
    warnings: List[str] = []
    for change, items, other in (("missing", old, new), ("added", new, old)):
        lost = _difference(items, other) if strict else _absent(items, other)
        for item in lost:
            if any(a.search(item.value) for a in allowed) or anchors == "off" and item.kind == "anchor":
                continue
            if item.kind == "anchor" and anchors == "warn":
                warnings.append(f"{change} anchor #{item.value} (line {item.line}): links to it may break")
            else:
                findings.append(Finding(change, item.kind, item.value, item.line))
    return findings, warnings


def _absent(items: List[Item], other: List[Item]) -> List[Item]:
    """Facts of ITEMS found nowhere in OTHER, one per value; structural kinds compared by count."""
    values = {i.value.strip("`") for i in other if i.kind in FACT_KINDS}
    texts = [i.value.replace("`", "") for i in other if i.kind in ("block", "cell")]
    facts, seen = [], set()
    for item in items:
        if item.kind not in FACT_KINDS or (item.kind, item.value) in seen:
            continue
        seen.add((item.kind, item.value))
        value = item.value.strip("`")
        if value not in values and (item.kind == "block" or not _inside(value, texts)):
            facts.append(item)
    structural = _difference([i for i in items if i.kind not in FACT_KINDS],
                             [i for i in other if i.kind not in FACT_KINDS])
    return sorted(facts + structural, key=lambda i: i.line)


def _inside(value: str, texts: List[str]) -> bool:
    token = re.compile(r"(?<![\w.,])" + re.escape(value) + r"(?![\w])")
    return any(token.search(t) for t in texts)


def _difference(items: List[Item], other: List[Item]) -> List[Item]:
    """Items of ITEMS beyond their count in OTHER; the last occurrences are reported."""
    surplus: Dict[Tuple[str, str], int] = Counter((i.kind, i.value) for i in items)
    surplus.subtract(Counter((i.kind, i.value) for i in other))
    result: List[Item] = []
    for item in reversed(items):
        key = (item.kind, item.value)
        if surplus[key] > 0:
            surplus[key] -= 1
            result.append(item)
    return list(reversed(result))


# --- command line -------------------------------------------------------------------


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="check_fidelity",
        description="Report technical content lost or added by a rewrite of a Markdown file.",
    )
    parser.add_argument("before", help="the original text")
    parser.add_argument("after", help="the rewritten or translated text")
    parser.add_argument(
        "--allow", action="append", default=[], metavar="REGEX",
        help="ignore items whose value matches, for a change you can justify; repeatable",
    )
    parser.add_argument(
        "--anchors", choices=("warn", "error", "off"), default="warn",
        help="how to treat changed heading anchors (default: warn)",
    )
    parser.add_argument(
        "--strict-count", action="store_true",
        help="report a repeated value dropped even when another occurrence remains",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    try:
        for pattern in args.allow:
            re.compile(pattern)
    except re.error as exc:
        print(f"check_fidelity: invalid --allow regex: {exc}", file=sys.stderr)
        return 2
    try:
        before = Path(args.before).read_text(encoding="utf-8-sig")
        after = Path(args.after).read_text(encoding="utf-8-sig")
    except OSError as exc:
        print(f"check_fidelity: cannot read {exc.filename}: {exc.strerror}", file=sys.stderr)
        return 2
    except UnicodeDecodeError as exc:
        print(f"check_fidelity: not UTF-8 text: {exc}", file=sys.stderr)
        return 2
    findings, warnings = compare(before, after, args.allow, args.anchors, args.strict_count)
    for warning in warnings:
        print(f"check_fidelity: warning: {warning}", file=sys.stderr)
    for f in findings:
        path = args.before if f.change == "missing" else args.after
        print(f"{path}:{f.line}: {f.change} {f.kind}: {f.value}")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
