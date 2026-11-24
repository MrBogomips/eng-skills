"""Resolve where the documentation lives: this repo, a local path, or a git URL.

A URL source is cloned once into the git common dir and refreshed on later runs.
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

NETWORK_TIMEOUT = 120
URL_PATTERN = re.compile(r"^(?:(?:https?|ssh|git|file)://\S+|[\w.-]+@[\w.-]+:\S+)$")


class SourceError(Exception):
    """The documentation source cannot be resolved."""


@dataclass(frozen=True)
class SourceResult:
    root: Path
    origin: str
    warning: str | None


def _git(args: list[str], cwd: Path | None = None,
         timeout: int | None = None) -> subprocess.CompletedProcess:
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    try:
        return subprocess.run(
            ["git", *args], cwd=cwd, env=env, capture_output=True,
            text=True, encoding="utf-8", errors="replace", timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(
            args, 124, "", f"timed out after {timeout} s")
    except OSError as exc:
        raise SourceError(f"cannot run git: {exc}") from exc


def _common_dir(repo: Path) -> Path:
    proc = _git(["rev-parse", "--git-common-dir"], cwd=repo)
    if proc.returncode != 0 or not proc.stdout.strip():
        raise SourceError(f"{repo} is not a git repository: {proc.stderr.strip()}")
    common = Path(proc.stdout.strip())
    return common if common.is_absolute() else (repo / common).resolve()


def _cache_dir(spec: str, ref: str | None, repo: Path) -> Path:
    key = hashlib.sha1((spec + (ref or "")).encode("utf-8")).hexdigest()[:12]
    return _common_dir(repo) / "docs-impact" / "sources" / key


def _clone(spec: str, ref: str | None, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    args = ["clone", "--depth", "1"] + (["--branch", ref] if ref else []) + ["--", spec, str(dest)]
    proc = _git(args, timeout=NETWORK_TIMEOUT)
    if proc.returncode != 0:
        shutil.rmtree(dest, ignore_errors=True)
        raise SourceError(f"cannot clone {spec}: {proc.stderr.strip()}")


def _refresh(spec: str, ref: str | None, dest: Path) -> str | None:
    """Update the cache; return a warning when it could not be refreshed."""
    fetch = _git(["fetch", "--depth", "1", "origin", ref or "HEAD"], cwd=dest,
                 timeout=NETWORK_TIMEOUT)
    if fetch.returncode == 0:
        reset = _git(["reset", "--hard", "FETCH_HEAD"], cwd=dest)
        if reset.returncode == 0:
            return None
        detail = reset.stderr.strip()
    else:
        detail = fetch.stderr.strip()
    return f"could not refresh {spec}; using the cached copy: {detail}"


def resolve_source(spec: str | None, repo: Path, ref: str | None = None) -> SourceResult:
    """None: the repo itself; an existing path: that path; otherwise a git URL."""
    if spec is None:
        return SourceResult(repo, "repo", None)
    if ref is not None and (ref.startswith("-") or not ref):
        raise SourceError(f"invalid ref {ref!r}")
    local = Path(spec).expanduser()
    if local.exists():
        if not local.is_dir():
            raise SourceError(f"{spec!r} is not a directory")
        warning = f"ref {ref!r} ignored for a local path" if ref else None
        return SourceResult(local.resolve(), f"path:{local.resolve()}", warning)
    if spec.startswith("-") or not URL_PATTERN.match(spec):
        raise SourceError(f"{spec!r} is neither an existing path nor a git URL")
    dest = _cache_dir(spec, ref, repo)
    origin = f"url:{spec}" + (f"@{ref}" if ref else "")
    if (dest / ".git").exists():
        return SourceResult(dest, origin, _refresh(spec, ref, dest))
    _clone(spec, ref, dest)
    return SourceResult(dest, origin, None)
