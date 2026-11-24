"""Match diff terms against documentation sections and rank the impacts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Iterable

from diff_terms import Term
from doc_sections import Section, matches_glob

ADJUSTMENTS = ("update", "obsolete", "check")
CONFIDENCE_RANK = {"high": 0, "medium": 1, "low": 2}
UNDOCUMENTED_KINDS = frozenset({"symbol", "flag", "env", "route"})
IDENTIFIER_KINDS = frozenset({"symbol", "env", "config_key"})
RENAME_WINDOW = 3


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


def _rename_partners(terms: Iterable[Term]) -> dict[Term, Term]:
    """Map both halves of each rename (removed and added, same kind and file, lines close)."""
    terms = list(terms)
    added = [t for t in terms if t.change == "added"]
    used: set[int] = set()
    partners: dict[Term, Term] = {}
    for old in (t for t in terms if t.change == "removed"):
        best = None
        for idx, new in enumerate(added):
            if idx in used or new.kind != old.kind or new.file != old.file:
                continue
            gap = abs(new.line - old.line)
            if gap <= RENAME_WINDOW and (best is None or gap < best[0]):
                best = (gap, idx)
        if best:
            used.add(best[1])
            partners[old], partners[added[best[1]]] = added[best[1]], old
    return partners


def _moved_keys(terms: Iterable[Term]) -> set[tuple[str, str]]:
    """(kind, text) pairs both removed and added in the diff: code moved, not gone."""
    removed = {(t.kind, t.text) for t in terms if t.change == "removed"}
    return removed & {(t.kind, t.text) for t in terms if t.change == "added"}


def _without_moves(terms: list[Term]) -> list[Term]:
    moved = _moved_keys(terms)
    return [t for t in terms
            if not (t.change in ("removed", "added") and (t.kind, t.text) in moved)]


def _is_updated(
    section: Section, changed: list, hunks: dict[str, list[tuple[int, int]]] | None
) -> bool:
    """A section the branch edits: its lines overlap a hunk; every section of an added file."""
    if hunks is None:
        return section.path in {p for _, p, _ in changed}
    if any(st == "A" and p == section.path for st, p, _ in changed):
        return True
    return any(a <= section.end_line and b >= section.start_line
               for a, b in hunks.get(section.path, []))


def _groups(hits: list[Term], renamed: set[Term]) -> list[tuple[str, str, list[Term]]]:
    """Hits split by what they imply: obsolete (unpaired removal), rename or change (update)."""
    obsolete = [t for t in hits if t.change == "removed" and t not in renamed]
    rename = [t for t in hits if t in renamed]
    changed = [t for t in hits if t.change == "changed"]
    groups: list[tuple[str, str, list[Term]]] = []
    if obsolete:
        groups.append(("obsolete", "high", obsolete))
    if rename or changed:
        groups.append(("update", "high" if rename else "medium", rename + changed))
    return groups


def declared_code_files(
    section_path: str, mappings: list[tuple[str, str]], changed: list
) -> list[str]:
    """Changed files that a declared mapping ties to the documentation file."""
    files: list[str] = []
    for code_glob, doc_glob in mappings:
        if not matches_glob(section_path, doc_glob, False):
            continue
        files.extend(p for _, p, _ in changed if matches_glob(p, code_glob, False) and p not in files)
    return files


def match(
    terms: list[Term],
    sections: list[Section],
    mappings: list[tuple[str, str]],
    changed: list,
    *,
    docs_in_repo: bool = True,
    url_for: Callable[[Section], str | None] | None = None,
    hunks: dict[str, list[tuple[int, int]]] | None = None,
) -> list[Impact]:
    """Impacts ranked by confidence, then number of terms. Matching is case-sensitive.

    ``hunks`` (new-side ranges per doc file) makes "updated in branch" per section; without
    it a section counts as updated when its file changed.
    """
    terms = _without_moves(terms)
    renamed = set(_rename_partners(terms))
    patterns = [(t, _pattern(t)) for t in terms]
    impacts: list[Impact] = []
    for section in sections:
        hits = [t for t, rx in patterns if rx.search(section.text)]
        groups = _groups(hits, renamed)
        declared = bool(declared_code_files(section.path, mappings, changed))
        if not groups and declared:
            groups = [("check", "low", [])]
        url = url_for(section) if url_for else None
        for adjustment, confidence, used in groups:
            impacts.append(Impact(
                section, tuple(used), declared, adjustment,
                "high" if declared and used else confidence, url,
                docs_in_repo and _is_updated(section, changed, hunks),
            ))
    impacts.sort(key=lambda i: (
        CONFIDENCE_RANK[i.confidence], -len(i.terms), i.section.path, i.section.start_line))
    return impacts


def undocumented(terms: list[Term], sections: list[Section]) -> list[Term]:
    """Added public terms that no section mentions, except the new half of a reported rename."""
    terms = _without_moves(terms)
    partners = _rename_partners(terms)
    found: list[Term] = []
    seen: set[tuple[str, str]] = set()
    for term in terms:
        key = (term.kind, term.text)
        if term.change != "added" or term.kind not in UNDOCUMENTED_KINDS or key in seen:
            continue
        seen.add(key)
        if not any(_pattern(term).search(s.text) for s in sections):
            old = partners.get(term)
            if old is None or not any(_pattern(old).search(s.text) for s in sections):
                found.append(term)
    return found
