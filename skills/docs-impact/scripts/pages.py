"""Detect GitHub Pages publishing, map sources to published URLs, check navigation.

No site is built and no YAML or JavaScript parser is used: configuration is read
with line regexes, and anything unreadable falls back to defaults.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

GIT_TIMEOUT = 30
DEPLOY_MARKERS = ("actions/deploy-pages", "peaceiris/actions-gh-pages", "mkdocs gh-deploy")
MD_EXTS = (".md", ".markdown", ".mdx")
GITHUB_REMOTES = (
    re.compile(r"^https?://(?:[^@/]+@)?github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$"),
    re.compile(r"^(?:ssh://)?git@github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?/?$"),
)


@dataclass(frozen=True)
class PagesSite:
    generator: str
    source_dir: str
    base_url: str
    deploy: str
    nav_files: tuple[str, ...] | None
    excludes: tuple[str, ...]
    # Needed to read front matter and to choose the MkDocs URL style.
    root: str = ""
    directory_urls: bool = True


def _read(path: Path, limit: int | None = None) -> str:
    try:
        with open(path, encoding="utf-8-sig", errors="replace") as handle:
            return handle.read(limit) if limit else handle.read()
    except OSError:
        return ""


def _first(root: Path, names: list[str]) -> Path | None:
    for name in names:
        try:
            if (root / name).is_file():
                return root / name
        except OSError:
            continue
    return None


def _key(text: str, name: str) -> str | None:
    match = re.search(
        rf"""^\s*['"]?{name}['"]?\s*[:=]\s*['"]?([^'"\s,#]+)""", text, re.M)
    return match.group(1) if match else None


def _github_repo(remote_url: str | None) -> tuple[str, str] | None:
    for pattern in GITHUB_REMOTES:
        match = pattern.match((remote_url or "").strip())
        if match:
            return match.group(1), match.group(2)
    return None


def _cname_host(root: Path, source_dir: str) -> str | None:
    for base in {root, root / source_dir}:
        host = _read(base / "CNAME").strip().split()
        if host:
            return host[0]
    return None


def _resolve_base(root: Path, source_dir: str, remote_url: str | None,
                  cfg_origin: str | None, cfg_path: str | None) -> str:
    """Generator config, then CNAME, then the owner.github.io fallback."""
    cname = _cname_host(root, source_dir)
    repo = _github_repo(remote_url)
    path = cfg_path
    if cfg_origin:
        origin = cfg_origin.rstrip("/")
    elif cname:
        origin = f"https://{cname}"
    elif repo:
        origin = f"https://{repo[0]}.github.io"
        if path is None and repo[1].lower() != f"{repo[0]}.github.io".lower():
            path = f"/{repo[1]}"
    else:
        return ""
    return origin + "/" + (path or "").strip("/") + ("/" if (path or "").strip("/") else "")


def _deploy(root: Path) -> str:
    workflows = root / ".github" / "workflows"
    try:
        files = sorted(p for p in workflows.glob("*") if p.suffix in (".yml", ".yaml"))
    except OSError:
        files = []
    for path in files:
        text = _read(path)
        if any(marker in text for marker in DEPLOY_MARKERS):
            return "actions"
    for ref in ("refs/heads/gh-pages", "refs/remotes/origin/gh-pages"):
        try:
            proc = subprocess.run(
                ["git", "show-ref", "--verify", "--quiet", ref], cwd=root,
                capture_output=True, timeout=GIT_TIMEOUT)
        except (OSError, subprocess.TimeoutExpired):
            return "unknown"
        if proc.returncode == 0:
            return "branch"
    return "unknown"


def _mkdocs_nav(text: str, docs_dir: str) -> tuple[str, ...] | None:
    lines = text.splitlines()
    start = next((i for i, ln in enumerate(lines) if re.match(r"^nav\s*:", ln)), None)
    if start is None:
        return None
    found: list[str] = []
    for line in lines[start + 1:]:
        if line.strip() and re.match(r"^\S", line) and not line.startswith("-"):
            break
        code = line.split("#", 1)[0]
        for ref in re.findall(r"""([^\s'":\[\],]+\.md)\b""", code):
            entry = f"{docs_dir}/{ref}" if docs_dir else ref
            if entry not in found:
                found.append(entry)
    return tuple(found)


def _detect_mkdocs(root: Path, cfg: Path, remote_url: str | None, deploy: str) -> PagesSite:
    text = _read(cfg)
    docs_dir = (_key(text, "docs_dir") or "docs").strip("/") or "docs"
    parts = urlsplit(_key(text, "site_url") or "")
    origin = f"{parts.scheme}://{parts.netloc}" if parts.netloc else None
    base = _resolve_base(root, docs_dir, remote_url, origin, parts.path if origin else None)
    flag = (_key(text, "use_directory_urls") or "true").lower()
    return PagesSite("mkdocs", docs_dir, base, deploy, _mkdocs_nav(text, docs_dir),
                     ("site/**",), str(root), flag != "false")


def _detect_jekyll(root: Path, cfg: Path, remote_url: str | None, deploy: str) -> PagesSite:
    text = _read(cfg)
    source_dir = cfg.parent.relative_to(root).as_posix()
    source_dir = "" if source_dir == "." else source_dir
    baseurl = _key(text, "baseurl")
    base = _resolve_base(root, source_dir, remote_url, _key(text, "url"), baseurl)
    return PagesSite("jekyll", source_dir, base, deploy, None, ("_site/**",), str(root))


def _docusaurus_nav(root: Path) -> tuple[str, ...] | None:
    sidebar = _first(root, ["sidebars.js", "sidebars.ts", "sidebars.mjs", "sidebars.cjs",
                            "sidebars.json"])
    if sidebar is None:
        return None
    text = _read(sidebar)
    if "autogenerated" in text:
        return None
    ids = re.findall(r"""['"](\w[\w./-]*)['"]""", text)
    return tuple(dict.fromkeys(f"docs/{i}.md" for i in ids))


def _detect_docusaurus(root: Path, cfg: Path, remote_url: str | None, deploy: str) -> PagesSite:
    text = _read(cfg)
    base = _resolve_base(root, "", remote_url, _key(text, "url"), _key(text, "baseUrl"))
    return PagesSite("docusaurus", "", base, deploy, _docusaurus_nav(root),
                     ("build/**", ".docusaurus/**"), str(root))


def _detect_static(root: Path, remote_url: str | None, deploy: str) -> PagesSite | None:
    source_dir = "docs" if (root / "docs").is_dir() else ""
    if deploy == "unknown" and not _cname_host(root, source_dir):
        return None
    base = _resolve_base(root, source_dir, remote_url, None, None)
    return PagesSite("static", source_dir, base, deploy, None, (), str(root))


def detect_pages(root: Path, remote_url: str | None) -> PagesSite | None:
    """Describe how the docs under root are published, or None when they are not."""
    root = Path(root)
    deploy = _deploy(root)
    cfg = _first(root, ["docusaurus.config.js", "docusaurus.config.ts",
                        "docusaurus.config.mjs", "docusaurus.config.cjs"])
    if cfg:
        return _detect_docusaurus(root, cfg, remote_url, deploy)
    cfg = _first(root, ["mkdocs.yml", "mkdocs.yaml"])
    if cfg:
        return _detect_mkdocs(root, cfg, remote_url, deploy)
    cfg = _first(root, ["_config.yml", "_config.yaml", "docs/_config.yml", "docs/_config.yaml"])
    if cfg:
        return _detect_jekyll(root, cfg, remote_url, deploy)
    return _detect_static(root, remote_url, deploy)


def _relative(site: PagesSite, rel_path: str) -> str | None:
    rel = rel_path.replace("\\", "/").lstrip("/")
    prefix = site.source_dir.strip("/")
    if not prefix:
        return rel
    return rel[len(prefix) + 1:] if rel.startswith(prefix + "/") else None


def _front_matter_permalink(site: PagesSite, rel_path: str) -> str | None:
    head = _read(Path(site.root) / rel_path, 4096)
    match = re.match(r"---[ \t]*\r?\n(.*?)\r?\n---", head, re.S)
    if not match:
        return None
    found = re.search(r"""^permalink:\s*['"]?([^'"\r\n#]+?)['"]?\s*$""", match.group(1), re.M)
    return found.group(1) if found else None


def _stem_and_dir(rel: str) -> tuple[str, bool]:
    """Strip the Markdown extension; flag index pages, which map to their directory."""
    stem = rel
    for ext in MD_EXTS:
        if rel.lower().endswith(ext):
            stem = rel[: -len(ext)]
            break
    else:
        return rel, False
    if stem.rsplit("/", 1)[-1].lower() in ("index", "readme"):
        return stem.rsplit("/", 1)[0] if "/" in stem else "", True
    return stem, False


def page_url(site: PagesSite, rel_path: str) -> str | None:
    """Absolute URL a docs file is published at, or None when it is not published."""
    rel = _relative(site, rel_path)
    if rel is None or not site.base_url:
        return None
    stem, is_index = _stem_and_dir(rel)
    is_markdown = stem != rel or is_index
    if not is_markdown or site.generator == "static":
        return site.base_url + rel
    if site.generator == "jekyll":
        link = _front_matter_permalink(site, rel_path.lstrip("/"))
        if link:
            return site.base_url + link.strip().lstrip("/")
    if is_index:
        suffix = "" if site.generator == "docusaurus" and stem else "/"
        if site.generator == "mkdocs" and not site.directory_urls:
            return site.base_url + (f"{stem}/" if stem else "") + "index.html"
        return site.base_url + (stem + suffix if stem else "")
    if site.generator == "jekyll" or (site.generator == "mkdocs" and not site.directory_urls):
        return f"{site.base_url}{stem}.html"
    return f"{site.base_url}{stem}" + ("/" if site.generator == "mkdocs" else "")


def _nav_key(path: str) -> str:
    return _stem_and_dir(path.replace("\\", "/"))[0].lower() if path.lower().endswith(
        MD_EXTS) else path.lower()


def missing_from_nav(site: PagesSite, rel_paths: list[str]) -> list[str]:
    """Markdown pages under the docs dir that the site navigation does not list."""
    if site.nav_files is None:
        return []
    listed = {_nav_key(p) for p in site.nav_files}
    missing: list[str] = []
    for path in rel_paths:
        if not path.lower().endswith(MD_EXTS) or _relative(site, path) is None:
            continue
        if site.generator == "docusaurus" and not path.startswith("docs/"):
            continue
        if _nav_key(path) not in listed:
            missing.append(path)
    return missing
