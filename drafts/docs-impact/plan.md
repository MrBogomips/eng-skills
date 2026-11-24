# docs-impact Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A generic `docs-impact` skill that, before final delivery of a branch, reports which sections of the
public documentation the branch's changes affect and what kind of adjustment each needs, and hands that report
over as the starting context for a quick documentation review, without reviewing or editing anything itself.

**Architecture:** A Python 3 standard-library scanner, run fresh on every call with no index: it extracts public
terms from `git diff base...HEAD`, splits the documentation into sections, matches them, ranks the hits and writes
a compact Markdown (or JSON) report. Documentation may come from the same repository or from an external path or
git URL cached in the git common dir. One specialization, GitHub Pages, adds published URLs, navigation checks and
generator output exclusion. `SKILL.md` tells the agent when to run it, how to read the project configuration and
how to hand the report over.

**Tech Stack:** Python 3.9+ standard library only (`re`, `pathlib`, `subprocess`, `dataclasses`, `argparse`,
`hashlib`, `json`, `fnmatch`), git CLI, `unittest`, `claude plugin eval`.

**Spec:** `drafts/docs-impact/decisions.md`

## Global Constraints

- Skill name `docs-impact`; files under `skills/docs-impact/`; frontmatter `name: docs-impact`.
- Scripts use only the Python standard library and run unchanged on Windows, Linux and macOS. Report paths are
  POSIX (`Path.as_posix()`); no shell-only syntax in subprocess calls (argument lists, never `shell=True`).
- Invoked as `python3 scripts/docs_impact.py ...` from `SKILL.md`, never by bare path.
- No persistent index. The only on-disk state is the external-source clone cache in
  `$(git rev-parse --git-common-dir)/docs-impact/sources/`.
- Read-only on documentation: no script or instruction writes to doc files. The report goes to the session
  scratchpad unless the user names another path.
- No build of the documentation site.
- Configuration extends the `## Documentation` section already read by `technical-writing`; existing keys keep
  their meaning.
- Diff base: the PR base branch, otherwise the repository default branch.
- Doc formats: Markdown/MDX (`.md`, `.mdx`, `.markdown`), reStructuredText (`.rst`), AsciiDoc (`.adoc`,
  `.asciidoc`), HTML (`.html`, `.htm`) only as source pages, never generator output.
- Skill content is generic: no project or client names. Examples in `SKILL.md` and references come from a payments
  HTTP API domain; eval scenarios use an image-conversion CLI and a static-site project, so evals measure rules, not
  recall.
- Each source file under 400 lines; functions under 50 lines.

## Review Focus

- **Docs already changed in the branch**: a section the branch already edits is reported as "updated in this
  branch", not as pending work. Test in Task 5.
- **Generic terms flooding the report** (`main`, `name`, `id`, two-letter flags): terms shorter than 4 characters
  and a stoplist are dropped; impacts above `--max-impacts` are cut with the count of omitted ones stated. Tests
  in Tasks 2 and 5.
- **Base ref missing in a shallow or CI clone**: exit 2 with a message naming the ref and suggesting
  `git fetch origin <base>`, never an empty "no impact" report. Test in Task 5.
- **URL source while offline**: use the cached clone with a warning in the report; no cache means exit 2. Test in
  Task 3.
- **Non-UTF-8 or binary files** in docs or diff: read with `errors="replace"`, skip binaries, never crash. Tests in
  Tasks 2 and 3.

---

### Task 1: Eval cases and baseline

**Files:**
- Create: `evals/d1-renamed-flag/{case.yaml,prompt.md,scaffold.sh,graders/*.md}`
- Create: `evals/d2-undocumented-command/...`, `evals/d3-pages-nav/...`, `evals/d4-no-impact/...`

**Interfaces:**
- Produces: four cases tagged `docs-impact`. Each `scaffold.sh` creates a git repo with a `main` commit and a
  `feature/x` branch checked out, so `main...HEAD` is the diff under test.

Scenarios (image-conversion CLI `imgconv` unless stated). Every prompt ends with "Save the report as
`DOCS-IMPACT.md`. You cannot ask me questions during this task." and opens with a pre-PR phrasing such as "I've
finished the work on this branch and I'm about to open the PR."

| Case | Branch change | Docs on `main` | Graders |
|---|---|---|---|
| d1 | flag `--output-dir` renamed `--out-dir`; env `IMGCONV_QUALITY` removed | `README.md` and `docs/usage.md` mention both | regex `contains` on `DOCS-IMPACT.md`: `docs/usage\.md`; regex `contains` `--output-dir`; regex `contains` on `docs/usage.md`: `--output-dir` (docs left untouched); llm on `DOCS-IMPACT.md`: flag rename classified as update and env var as obsolete |
| d2 | new public subcommand `imgconv batch` | no mention | regex `contains` on report: `batch`; llm: report states `batch` is undocumented and does not write the missing docs |
| d3 | static site (MkDocs, `site_url: https://example.github.io/pixkit/`), new page `docs/guides/batch.md`, not in `nav` | `mkdocs.yml` nav lists other pages | regex `contains` on report: `https://example\.github\.io/pixkit/guides/batch/`; llm: report flags the page missing from navigation |
| d4 | private helper `_resize_kernel` refactored, tests only | `docs/usage.md` | llm on last message: states no documentation impact and lists no invented impacts |

- [ ] **Step 1: Write the four cases** following `evals/s6-release-notes/` (schema `1.1`, `max_turns: 25`,
  `allowed_tools: [Read, Write, Edit, Glob, Grep, Skill, Bash]`). One criterion per llm grader. Graders target
  what the skill forbids or requires, not wording a correct answer may vary.
- [ ] **Step 2: Run the baseline**

Run (per case): `claude plugin eval . --case 'd1-*' --scaffold --allow-tools Bash Write Edit --no-publish --trust-plugin --runs 1 --judge-model sonnet --keep-temp`
Expected: the no-plugin arm fails at least one grader in d1, d2 and d3 (typically: docs edited, no adjustment
classification, no URL or nav finding). Read the kept traces. If a case passes at baseline it measures nothing:
tighten it before going on. d4 may pass at baseline; it guards against over-reporting.

- [ ] **Step 3: Commit**

```bash
git add evals/d1-renamed-flag evals/d2-undocumented-command evals/d3-pages-nav evals/d4-no-impact
git commit -m "test(docs-impact): eval cases and baseline"
```

### Task 2: Term extraction from the diff

**Files:**
- Create: `skills/docs-impact/scripts/diff_terms.py`
- Test: `tests/test_diff_terms.py`

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) Term(text: str, kind: str, change: str, file: str, line: int)`; `kind` in
    `{"symbol", "flag", "env", "config_key", "route", "path"}`; `change` in `{"added", "removed", "changed"}`.
  - `parse_diff(diff_text: str) -> list[Term]` (pure).
  - `extract_terms(repo: Path, base: str, head: str = "HEAD") -> list[Term]` (runs
    `git diff --unified=0 -M base...head`, then `parse_diff`).
  - `changed_files(repo: Path, base: str, head: str = "HEAD") -> list[tuple[str, str, str | None]]`
    as `(status, path, old_path)` from `git diff --name-status -M`.
  - `class GitError(Exception)`.

Rules: a term only on `-` lines is `removed`, only on `+` lines `added`, on both `changed`. A renamed file yields a
`path` term for the old name (`removed`) and the new one (`added`). Public symbols: Python `def`/`class` without a
leading `_`; JS/TS `export`; Go capitalized `func`/`type`; Java/C#/Kotlin `public`; Rust `pub fn|struct|enum`.
Flags `--[a-z][a-z0-9-]+`; env `[A-Z][A-Z0-9_]{3,}` inside `getenv`/`environ`/`process.env` or quoted; config keys
from changed lines of `.yaml`, `.yml`, `.toml`, `.json`, `.ini`; routes as quoted `/segment/...` strings. Drop
terms shorter than 4 characters and those in `STOPLIST` (`main`, `init`, `test`, `data`, `name`, `value`, `self`,
`args`, `none`, `true`, `false`). Skip diff hunks of test files (`test_*`, `*_test.*`, `tests/`, `__tests__/`) and
binary files.

- [ ] **Step 1: Write failing tests** `test_renamed_flag_is_changed_pair` (removed `--output-dir`, added
  `--out-dir`), `test_private_python_def_ignored`, `test_go_exported_func_only`, `test_env_var_removed`,
  `test_yaml_key_changed`, `test_short_and_stoplisted_terms_dropped`, `test_test_files_skipped`,
  `test_binary_diff_skipped`, `test_rename_yields_path_terms`, `test_bad_base_raises_git_error` (temp repo, base
  `nope`).
- [ ] **Step 2: Run** `python3 -m unittest tests.test_diff_terms -v` → FAIL (module missing).
- [ ] **Step 3: Implement** `diff_terms.py` with the signatures above; one compiled regex table keyed by `kind`.
- [ ] **Step 4: Run** `python3 -m unittest tests.test_diff_terms -v` → PASS.
- [ ] **Step 5: Commit** `feat(docs-impact): extract public terms from the branch diff`.

### Task 3: Documentation sources and sections

**Files:**
- Create: `skills/docs-impact/scripts/doc_sections.py`, `skills/docs-impact/scripts/doc_source.py`
- Test: `tests/test_doc_sections.py`, `tests/test_doc_source.py`

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) Section(path: str, anchor: str, title: str, start_line: int, end_line: int, text: str)`
  - `DEFAULT_DOC_GLOBS = ["README*", "docs/**", "doc/**", "*.md"]`;
    `DEFAULT_EXCLUDES = ["CHANGELOG*", "node_modules/**", "_site/**", "site/**", "build/**", ".docusaurus/**"]`
  - `find_doc_files(root: Path, globs: list[str], excludes: list[str]) -> list[Path]` (doc extensions only).
  - `split_sections(rel_path: str, text: str) -> list[Section]`: Markdown ATX headings (ignoring fenced code), RST
    underlined titles, AsciiDoc `=` titles, HTML `<h1>`–`<h6>`; text before the first heading is a section with
    `anchor=""`. Anchor is the GitHub slug: lowercase, drop characters other than letters, digits, spaces and `-`,
    spaces to `-`.
  - `@dataclass(frozen=True) SourceResult(root: Path, origin: str, warning: str | None)`
  - `resolve_source(spec: str | None, repo: Path, ref: str | None = None) -> SourceResult`: `None` → the repo
    itself; an existing path → that path; otherwise a git URL cloned with `git clone --depth 1 [--branch ref]` into
    `<git-common-dir>/docs-impact/sources/<sha1(spec+ref)[:12]>`, refreshed with `git fetch --depth 1 origin <ref or
    HEAD>` and `git reset --hard FETCH_HEAD` inside the cache. Fetch failure with a cache → warning; without →
    `SourceError`.

- [ ] **Step 1: Write failing tests**: `test_markdown_headings_and_anchors` (`## Output options` →
  `output-options`), `test_heading_inside_code_fence_ignored`, `test_rst_and_adoc_titles`, `test_html_headings`,
  `test_preamble_section`, `test_excludes_generator_output`, `test_non_utf8_file_read_with_replacement`;
  `test_none_spec_uses_repo`, `test_local_path_spec`, `test_url_spec_clones_into_common_dir` (a bare repo via
  `file://`), `test_second_run_fetches_update`, `test_offline_with_cache_warns`, `test_offline_without_cache_raises`.
- [ ] **Step 2: Run** `python3 -m unittest tests.test_doc_sections tests.test_doc_source -v` → FAIL.
- [ ] **Step 3: Implement** both modules.
- [ ] **Step 4: Run** the same command → PASS.
- [ ] **Step 5: Commit** `feat(docs-impact): documentation sources and section splitting`.

### Task 4: GitHub Pages specialization

**Files:**
- Create: `skills/docs-impact/scripts/pages.py`
- Test: `tests/test_pages.py`

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) PagesSite(generator: str, source_dir: str, base_url: str, deploy: str, nav_files: tuple[str, ...] | None, excludes: tuple[str, ...])`;
    `generator` in `{"jekyll", "mkdocs", "docusaurus", "static"}`; `deploy` in `{"actions", "branch", "unknown"}`.
  - `detect_pages(root: Path, remote_url: str | None) -> PagesSite | None`
  - `page_url(site: PagesSite, rel_path: str) -> str | None`
  - `missing_from_nav(site: PagesSite, rel_paths: list[str]) -> list[str]`

Detection without third-party parsers: `mkdocs.yml` (line regexes for `site_url`, `docs_dir`,
`use_directory_urls`, and `*.md` references under `nav:`), `_config.yml` (`url`, `baseurl`; Jekyll; source `/` or
`docs/`), `docusaurus.config.{js,ts}` (`url`, `baseUrl`; `sidebars.*` with `autogenerated` → nav check skipped).
`deploy = "actions"` when a workflow contains `actions/deploy-pages`, `peaceiris/actions-gh-pages` or
`mkdocs gh-deploy`; `"branch"` when a `gh-pages` branch exists. Base URL precedence: generator config, then `CNAME`
host, then `https://<owner>.github.io/<repo>/` from the remote. URL rules: Jekyll `a/b.md` → `a/b.html`,
`index.md` → directory, front-matter `permalink` wins; MkDocs with directory URLs `a/b.md` → `a/b/`, otherwise
`a/b.html`; Docusaurus `docs/a/b.md` → `docs/a/b`. Returns `None` when no generator or Pages signal is found.

- [ ] **Step 1: Write failing tests**: `test_mkdocs_detected_with_site_url`, `test_mkdocs_directory_urls`,
  `test_jekyll_permalink_wins`, `test_docusaurus_base_url`, `test_cname_overrides_remote`,
  `test_remote_fallback_url`, `test_page_missing_from_mkdocs_nav`, `test_docusaurus_autogenerated_skips_nav`,
  `test_actions_deploy_detected`, `test_plain_repo_returns_none`.
- [ ] **Step 2: Run** `python3 -m unittest tests.test_pages -v` → FAIL.
- [ ] **Step 3: Implement** `pages.py`.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat(docs-impact): GitHub Pages detection, URLs and navigation check`.

### Task 5: Matching, report and CLI

**Files:**
- Create: `skills/docs-impact/scripts/impact.py` (matching and ranking), `skills/docs-impact/scripts/report.py`
  (rendering), `skills/docs-impact/scripts/docs_impact.py` (CLI)
- Test: `tests/test_impact.py`, `tests/test_docs_impact_cli.py`

**Interfaces:**
- Consumes: Tasks 2–4 as declared.
- Produces:
  - `@dataclass(frozen=True) Impact(section: Section, terms: tuple[Term, ...], declared: bool, adjustment: str, confidence: str, url: str | None, updated_in_branch: bool)`;
    `adjustment` in `{"update", "obsolete", "check"}`; `confidence` in `{"high", "medium", "low"}`.
  - `parse_mappings(specs: list[str]) -> list[tuple[str, str]]` from `"CODE_GLOB => DOC_GLOB"`.
  - `match(terms, sections, mappings, changed: list[tuple[str, str, str | None]]) -> list[Impact]`, ranked by
    confidence, then number of terms.
  - `undocumented(terms, sections) -> list[Term]`: `added` terms of kind `symbol`, `flag`, `env`, `route` found in
    no section.
  - `render(report: dict, fmt: str) -> str` for `"md"` and `"json"`.
  - CLI `docs_impact.py`: `--repo PATH` (default `.`), `--base REF` (default: `origin/HEAD` target, else `main`,
    else `master`), `--head REF`, `--docs GLOB`*, `--exclude GLOB`*, `--map SPEC`*, `--source SPEC`,
    `--source-ref REF`, `--pages auto|off`, `--format md|json`, `--max-impacts N` (default 50), `--out PATH`.
    Exit 0 with a report (also when empty), 2 on `GitError`, `SourceError` or bad arguments, with one-line stderr.

Classification: a section hit by a `removed` term → `obsolete`, `high`; by a `changed` term or both halves of a
renamed pair → `update`, `high` for renames, `medium` otherwise; matched only by a declared mapping → `check`,
`low`; declared plus a term raises to `high`. Matching is case-sensitive on word boundaries (flags and routes
literal). A section whose file the branch already changed gets `updated_in_branch=True`.

Report sections, in order: header (base, head, diff stat, doc source, Pages site if any, warnings); **Impacts**
table (doc `path#anchor`, URL, adjustment, confidence, terms, `file:line` of the cause); **Undocumented
additions**; **Navigation** (pages missing from nav); **Already updated in this branch**; **Review context**: the
doc files to open in order and the changed code files behind each, ready to hand to a reviewer; a final line
`N impacts omitted (--max-impacts)` when cut.

- [ ] **Step 1: Write failing tests**: `test_removed_term_is_obsolete_high`, `test_renamed_flag_is_update_high`,
  `test_declared_mapping_only_is_check_low`, `test_declared_plus_term_is_high`,
  `test_section_changed_in_branch_marked`, `test_undocumented_added_flag`, `test_max_impacts_cut_reported`,
  `test_render_md_sections_in_order`, `test_render_json_roundtrip`; CLI on a temp git repo:
  `test_cli_end_to_end_md`, `test_cli_no_impact_exit_0`, `test_cli_missing_base_exit_2_with_fetch_hint`,
  `test_cli_pages_urls_in_report`.
- [ ] **Step 2: Run** `python3 -m unittest tests.test_impact tests.test_docs_impact_cli -v` → FAIL.
- [ ] **Step 3: Implement** the three modules.
- [ ] **Step 4: Run** `python3 -m unittest discover tests -v` → PASS, then
  `python3 -m coverage run -m unittest discover tests && python3 -m coverage report --include='skills/docs-impact/*'`
  → at least 80%.
- [ ] **Step 5: Commit** `feat(docs-impact): impact matching, report and CLI`.

### Task 6: SKILL.md and references

**Files:**
- Create: `skills/docs-impact/SKILL.md`, `skills/docs-impact/references/configuration.md`,
  `skills/docs-impact/references/github-pages.md`

**Interfaces:**
- Consumes: the CLI of Task 5.

Content decisions:
- `description`: when, not what. Use before final delivery of a branch (opening or updating the final PR, handing
  over, "I'm done") to check whether its changes affect the public documentation, its README, user guide, API pages
  or GitHub Pages site; also when asked what documentation a change affects. Not for writing or reviewing docs
  (that is `technical-writing` and the documentation agents).
- Body (lean, under ~120 lines): 1) read `## Documentation` and resolve base, globs, mappings, source; 2) run the
  script into the scratchpad; 3) read the report and add the judgment the script cannot: impacts described in
  prose with no shared term, false positives to strike (state why); 4) present a short summary and the report path;
  5) offer, without doing it, to hand the report to `documentation-writer` (to make the changes) or
  `documentation-reviewer` (quick review), passing the report's Review context. Never edit docs; never claim
  "no impact" when the script exited 2.
- `references/configuration.md`: the new keys, alongside the existing ones:
  `- Docs source: <path or git URL>[@ref]`, `- Docs impact map: <code glob> => <doc glob>` (repeatable),
  `- Docs pages: off`. "Published as a whole" globs are the doc set when present.
- `references/github-pages.md`: what is detected, URL rules, nav check, limits (no build, no link check).
- Examples from the payments HTTP API domain only.

- [ ] **Step 1: Write** the three files.
- [ ] **Step 2: Run** `claude plugin validate .` → no errors.
- [ ] **Step 3: Run the evals with the plugin**:
  `claude plugin eval . --case 'd*' --scaffold --allow-tools Bash Write Edit --no-publish --trust-plugin --runs 1 --judge-model sonnet --keep-temp`
  Expected: d1–d4 pass on the plugin arm. On a failure read the trace first, then fix the skill or the grader.
- [ ] **Step 4: Commit** `feat(docs-impact): skill instructions and references`.

### Task 7: Plugin metadata and README

**Files:**
- Modify: `README.md` (Contents table row, `## Project configuration` keys), `.claude-plugin/plugin.json`
  (`"version": "0.3.0"`, description mentions documentation impact)
- Modify: `AGENTS.md` only if a new eval or command convention emerged.

- [ ] **Step 1: Update** README and manifest.
- [ ] **Step 2: Run** `claude plugin validate . && python3 -m unittest discover tests` → PASS.
- [ ] **Step 3: Commit** `docs(docs-impact): README and plugin version 0.3.0`.
