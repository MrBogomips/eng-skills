"""Render the documentation impact report as Markdown or JSON."""

from __future__ import annotations

import json
from dataclasses import asdict

from impact import Impact, declared_code_files

NO_IMPACT = "No documentation impact found."


def _term_dict(term) -> dict:
    return asdict(term)


def _impact_dict(imp: Impact, code_files: list[str]) -> dict:
    sec = imp.section
    return {
        "path": sec.path, "anchor": sec.anchor, "title": sec.title,
        "start_line": sec.start_line, "end_line": sec.end_line, "url": imp.url,
        "adjustment": imp.adjustment, "confidence": imp.confidence, "declared": imp.declared,
        "updated_in_branch": imp.updated_in_branch,
        "terms": [_term_dict(t) for t in imp.terms], "code_files": code_files,
    }


def _code_files(imp: Impact, report: dict) -> list[str]:
    files = [t.file for t in imp.terms]
    files += declared_code_files(imp.section.path, report.get("mappings", []),
                                 report.get("changed", []))
    return list(dict.fromkeys(files))


def _json_view(report: dict) -> dict:
    skip = ("impacts", "updated", "undocumented", "mappings", "changed")
    view = {k: v for k, v in report.items() if k not in skip}
    view["updated"] = [_impact_dict(i, _code_files(i, report)) for i in report.get("updated", [])]
    view["impacts"] = [_impact_dict(i, _code_files(i, report)) for i in report["impacts"]]
    view["undocumented"] = [_term_dict(t) for t in report["undocumented"]]
    return view


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def _header(report: dict) -> list[str]:
    src = report["source"]
    lines = ["# Documentation impact", "",
             f"- base: {report['base']}  head: {report['head']}",
             f"- diff: {report.get('diffstat') or 'no changes'}",
             f"- doc source: {src['origin']} ({src['root']})"]
    pages = report.get("pages")
    if pages:
        lines.append(f"- pages: {pages['generator']} {pages['base_url'] or '(no base URL)'}"
                     f" deploy={pages['deploy']}")
    warnings = list(report.get("warnings", [])) + ([src["warning"]] if src.get("warning") else [])
    lines += [f"- warning: {w}" for w in warnings]
    return lines


def _impacts_md(report: dict) -> list[str]:
    lines = ["", "## Impacts", ""]
    if not report["impacts"]:
        return lines + ["None.", ""]
    lines += ["| Section | URL | Adjustment | Confidence | Terms | Cause |", "|---|---|---|---|---|---|"]
    for imp in report["impacts"]:
        sec = imp.section
        terms = ", ".join(f"`{t.text}` ({t.change})" for t in imp.terms) or "declared mapping"
        cause = ", ".join(dict.fromkeys(f"{t.file}:{t.line}" for t in imp.terms)) or (
            ", ".join(_code_files(imp, report)))
        lines.append("| " + " | ".join(_cell(c) for c in (
            f"{sec.path}#{sec.anchor}", imp.url or "-", imp.adjustment, imp.confidence,
            terms, cause)) + " |")
    return lines + [""]


def _undocumented_md(report: dict) -> list[str]:
    if not report["undocumented"]:
        return []
    lines = ["## Undocumented additions", "", "| Term | Kind | Cause |", "|---|---|---|"]
    lines += [f"| {_cell('`' + t.text + '`')} | {t.kind} | {t.file}:{t.line} |"
              for t in report["undocumented"]]
    return lines + [""]


def _navigation_md(report: dict) -> list[str]:
    note = report.get("nav_note")
    if not report["navigation"] and not note:
        return []
    lines = ["## Navigation", ""]
    lines += [f"- not in navigation: {p['path']} {p['url'] or '—'}" for p in report["navigation"]]
    if note:
        lines.append(f"- {note}")
    return lines + [""]


def _updated_md(report: dict) -> list[str]:
    done = report.get("updated", [])
    lines = ["## Already updated in this branch", ""]
    if not done:
        return lines + ["None.", ""]
    return lines + [f"- {i.section.path}#{i.section.anchor} ({i.adjustment})" for i in done] + [""]


def _context_md(report: dict) -> list[str]:
    order: dict[str, list[str]] = {}
    for imp in report["impacts"]:
        files = order.setdefault(imp.section.path, [])
        files.extend(f for f in _code_files(imp, report) if f not in files)
    lines = ["## Review context", ""]
    if not order:
        return lines + ["None.", ""]
    for n, (doc, files) in enumerate(order.items(), 1):
        lines.append(f"{n}. open {doc}; code: {', '.join(files) or '-'}")
    return lines + [""]


def _md(report: dict) -> str:
    lines = _header(report) + _impacts_md(report) + _undocumented_md(report)
    lines += _navigation_md(report) + _updated_md(report) + _context_md(report)
    if not (report["impacts"] or report["undocumented"] or report["navigation"]):
        lines += [NO_IMPACT, ""]
    if report.get("omitted"):
        lines.append(f"{report['omitted']} impacts omitted (--max-impacts)")
    return "\n".join(lines).rstrip() + "\n"


def render(report: dict, fmt: str) -> str:
    """Render the report dict as ``md`` or ``json``; ValueError for another format."""
    if fmt == "md":
        return _md(report)
    if fmt == "json":
        return json.dumps(_json_view(report), indent=2, ensure_ascii=False) + "\n"
    raise ValueError(f"unknown format {fmt!r}")
