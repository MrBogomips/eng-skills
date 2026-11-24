"""Match diff terms against documentation sections and rank the impacts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Iterable

from diff_terms import Term
from doc_sections import Section, _matches

ADJUSTMENTS = ("update", "obsolete", "check")
CONFIDENCE_RANK = {"high": 0, "medium": 1, "low": 2}
UNDOCUMENTED_KINDS = frozenset({"symbol", "flag", "env", "route"})
IDENTIFIER_KINDS = frozenset({"symbol", "env", "config_key"})
RENAME_WINDOW = 3

Changed = "list[tuple[str, str, str | None]]"


@dataclass(frozen=True)
class Impact:
    section: Section
    terms: tuple[Term, ...]
    declared: bool
    adjustment: str
    confidence: str
    url: str | None
    updated_in_branch: bool


def parse_mappings(specs: list[str]) -> list[tuple[str, str]]:
    """Split ``"CODE_GLOB => DOC_GLOB"`` specs; ValueError when one is malformed."""
    pairs: list[tuple[str, str]] = []
    for spec in specs:
        code, sep, doc = spec.partition("=>")
        if not sep or not code.strip() or not doc.strip():
            raise ValueError(f"invalid --map {spec!r}: expected 'CODE_GLOB => DOC_GLOB'")
        pairs.append((code.strip(), doc.strip()))
    return pairs


def _pattern(term: Term) -> re.Pattern:
    text = re.escape(term.text)
    if term.kind in IDENTIFIER_KINDS:
        return re.compile(rf"(?<![A-Za-z0-9_]){text}(?![A-Za-z0-9_])")
    lead = r"(?<![\w-])" if term.kind == "flag" else ""
    return re.compile(rf"{lead}{text}(?![A-Za-z0-9_-])")


def _rename_pairs(terms: Iterable[Term]) -> set[Term]:
    """Terms taking part in a rename: removed and added, same kind and file, lines close."""
    terms = list(terms)
    removed = [t for t in terms if t.change == "removed"]
    added = [t for t in terms if t.change == "added"]
    used: set[int] = set()
    paired: set[Term] = set()
    for old in removed:
        best = None
        for idx, new in enumerate(added):
            if idx in used or new.kind != old.kind or new.file != old.file:
                continue
            gap = abs(new.line - old.line)
            if gap <= RENAME_WINDOW and (best is None or gap < best[0]):
                best = (gap, idx)
        if best:
            used.add(best[1])
            paired.update((old, added[best[1]]))
    return paired


def _classify(hits: list[Term], renamed: set[Term]) -> tuple[str, str] | None:
    """Obsolete outranks a rename, which outranks a plain change."""
    if any(t.change == "removed" and t not in renamed for t in hits):
        return "obsolete", "high"
    if any(t in renamed for t in hits):
        return "update", "high"
    if any(t.change == "changed" for t in hits):
        return "update", "medium"
    return None


def declared_code_files(
    section_path: str, mappings: list[tuple[str, str]], changed: list
) -> list[str]:
    """Changed files that a declared mapping ties to the documentation file."""
    files: list[str] = []
    for code_glob, doc_glob in mappings:
        if not _matches(section_path, doc_glob, False):
            continue
        files.extend(p for _, p, _ in changed if _matches(p, code_glob, False) and p not in files)
    return files


def match(
    terms: list[Term],
    sections: list[Section],
    mappings: list[tuple[str, str]],
    changed: list,
    *,
    docs_in_repo: bool = True,
    url_for: Callable[[Section], str | None] | None = None,
) -> list[Impact]:
    """Impacts ranked by confidence, then number of terms. Matching is case-sensitive."""
    renamed = _rename_pairs(terms)
    patterns = [(t, _pattern(t)) for t in terms]
    changed_docs = {p for _, p, _ in changed} if docs_in_repo else set()
    impacts: list[Impact] = []
    for section in sections:
        hits = [t for t, rx in patterns if rx.search(section.text)]
        kind = _classify(hits, renamed)
        declared = bool(declared_code_files(section.path, mappings, changed))
        if kind is None and not declared:
            continue
        if kind is None:
            kind = ("check", "low")
        elif declared:
            kind = (kind[0], "high")
        used = tuple(t for t in hits if t.change != "added" or t in renamed)
        impacts.append(Impact(
            section, used, declared, kind[0], kind[1],
            url_for(section) if url_for else None, section.path in changed_docs,
        ))
    impacts.sort(key=lambda i: (
        CONFIDENCE_RANK[i.confidence], -len(i.terms), i.section.path, i.section.start_line))
    return impacts


def undocumented(terms: list[Term], sections: list[Section]) -> list[Term]:
    """Added public terms that no documentation section mentions."""
    found: list[Term] = []
    seen: set[tuple[str, str]] = set()
    for term in terms:
        key = (term.kind, term.text)
        if term.change != "added" or term.kind not in UNDOCUMENTED_KINDS or key in seen:
            continue
        seen.add(key)
        rx = _pattern(term)
        if not any(rx.search(s.text) for s in sections):
            found.append(term)
    return found
