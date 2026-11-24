"""Report which public documentation sections a branch's changes affect.

Read-only: nothing here writes documentation. Exit 0 with a report (also when empty),
exit 2 with a one-line stderr message on bad arguments, git or source failures.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

from diff_terms import GitError, changed_files, extract_terms
from doc_sections import DEFAULT_DOC_GLOBS, DEFAULT_EXCLUDES, Section, find_doc_files, read_doc, split_sections
from doc_source import SourceError, resolve_source
from impact import match, parse_mappings, undocumented
from pages import PagesSite, detect_pages, missing_from_nav, page_url
from report import render

GIT_TIMEOUT = 60
DEFAULT_MAX_IMPACTS = 50


class UsageError(Exception):
    """Bad arguments or an unresolvable ref; reported as one line with exit status 2."""


def _git(repo: Path, *args: str) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            ["git", *args], cwd=str(repo), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=GIT_TIMEOUT,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise GitError(f"cannot run git: {exc}") from exc
    return proc.returncode, proc.stdout.strip()


def _resolves(repo: Path, ref: str) -> bool:
    return _git(repo, "rev-parse", "--verify", "--quiet", "--end-of-options", ref + "^{commit}")[0] == 0


def resolve_base(repo: Path, requested: str | None) -> str:
    """The requested base, else origin's default branch, ``main`` or ``master``."""
    if requested is not None:
        candidates = [requested]
    else:
        code, target = _git(repo, "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD")
        candidates = ([target.replace("refs/remotes/", "", 1)] if code == 0 and target else [])
        candidates += ["main", "master"]
    for ref in candidates:
        if _resolves(repo, ref):
            return ref
    name = candidates[-1] if requested else "main"
    raise UsageError(f"cannot resolve base ref '{requested or 'main/master'}'; try: git fetch origin {name}")


def _diffstat(repo: Path, base: str, head: str) -> str:
    code, out = _git(repo, "diff", "--shortstat", "--end-of-options", f"{base}...{head}")
    return out if code == 0 else ""


def _remote_url(root: Path) -> str | None:
    try:
        code, out = _git(root, "remote", "get-url", "origin")
    except GitError:
        return None
    return (out or None) if code == 0 else None


def _load_sections(root: Path, globs: list[str], excludes: list[str]) -> list[Section]:
    sections: list[Section] = []
    for path in find_doc_files(root, globs, excludes):
        text = read_doc(path)
        if text is not None:
            sections.extend(split_sections(path.relative_to(root).as_posix(), text))
    return sections


def _pages_view(site: PagesSite | None) -> dict | None:
    if site is None:
        return None
    return {k: v for k, v in asdict(site).items() if k not in ("root", "nav_files")}


def _nav_check(site: PagesSite | None, in_repo: bool, changed: list) -> tuple[list[str], str | None]:
    if site is None:
        return [], None
    if not in_repo:
        return [], "navigation check skipped: documentation source is not this repository"
    new_docs = [p for s, p, _ in changed if s in ("A", "R")]
    return missing_from_nav(site, new_docs), None


def _url_for(site: PagesSite | None):
    if site is None:
        return None

    def url(section: Section) -> str | None:
        page = page_url(site, section.path)
        return f"{page}#{section.anchor}" if page else None

    return url


def build_report(args: argparse.Namespace) -> dict:
    repo = Path(args.repo).resolve()
    mappings = parse_mappings(args.map)
    base = resolve_base(repo, args.base)
    if not _resolves(repo, args.head):
        raise UsageError(f"cannot resolve head ref '{args.head}'; try: git fetch origin {args.head}")
    source = resolve_source(args.source, repo, args.source_ref)
    in_repo = source.origin == "repo"
    site = detect_pages(source.root, _remote_url(source.root)) if args.pages == "auto" else None
    excludes = DEFAULT_EXCLUDES + args.exclude + (list(site.excludes) if site else [])
    sections = _load_sections(source.root, args.docs or DEFAULT_DOC_GLOBS, excludes)
    terms = extract_terms(repo, base, args.head)
    changed = changed_files(repo, base, args.head)
    impacts = match(terms, sections, mappings, changed, docs_in_repo=in_repo,
                    url_for=_url_for(site))
    navigation, nav_note = _nav_check(site, in_repo, changed)
    warnings = [] if in_repo else ["external documentation source: updated-in-branch detection is off"]
    return {
        "base": base, "head": args.head, "diffstat": _diffstat(repo, base, args.head),
        "source": {"origin": source.origin, "root": source.root.as_posix(), "warning": source.warning},
        "pages": _pages_view(site), "warnings": warnings,
        "impacts": impacts[: args.max_impacts], "omitted": max(0, len(impacts) - args.max_impacts),
        "undocumented": undocumented(terms, sections), "navigation": navigation,
        "nav_note": nav_note, "mappings": mappings, "changed": changed,
    }


def _non_negative(value: str) -> int:
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError("must be 0 or more")
    return number


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--repo", default=".")
    p.add_argument("--base")
    p.add_argument("--head", default="HEAD")
    p.add_argument("--docs", action="append", default=[], metavar="GLOB")
    p.add_argument("--exclude", action="append", default=[], metavar="GLOB")
    p.add_argument("--map", action="append", default=[], metavar="SPEC")
    p.add_argument("--source")
    p.add_argument("--source-ref")
    p.add_argument("--pages", choices=("auto", "off"), default="auto")
    p.add_argument("--format", choices=("md", "json"), default="md")
    p.add_argument("--max-impacts", type=_non_negative, default=DEFAULT_MAX_IMPACTS)
    p.add_argument("--out")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        text = render(build_report(args), args.format)
        if args.out:
            Path(args.out).write_text(text, encoding="utf-8")
            print(Path(args.out).as_posix())
        else:
            sys.stdout.buffer.write(text.encode("utf-8"))
    except (GitError, SourceError, UsageError, ValueError, OSError) as exc:
        print(" ".join(str(exc).split()) or type(exc).__name__, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
