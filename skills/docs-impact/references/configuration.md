# Configuration

The skill reads the target project's `## Documentation` section in `AGENTS.md` or `CLAUDE.md`, the same section the
technical-writing skill uses. It needs no configuration: with no section, the scanner checks the default doc set in
the repository itself and detects GitHub Pages on its own. Add keys only when the defaults are wrong for the project.

## Keys

The first line is an existing key of the section; the other three belong to this skill. Unknown keys are ignored.

```markdown
## Documentation
- Published as a whole: `README.md`, `docs/**`, `guides/*.md`
- Docs source: https://github.com/example/payments-docs.git@main
- Docs impact map: `src/refunds/**` => `docs/api/refunds.md`
- Docs impact map: `src/webhooks/**` => `docs/guides/webhooks/**`
- Docs pages: off
```

| Key | Meaning | Scanner option |
|---|---|---|
| `Published as a whole:` | The doc set: only files matching these globs are checked | `--docs <glob>`, one per glob |
| `Docs source:` | Where the documentation lives when it is not this repository: a local path or a git URL, optionally `@<ref>` | `--source <path or URL>`, `--source-ref <ref>` |
| `Docs impact map:` | A code area and the pages that document it; repeat the key for each pair | `--map "<code glob> => <doc glob>"` |
| `Docs pages: off` | Skip GitHub Pages detection, URLs and the navigation check | `--pages off` |

Only documentation formats are scanned: Markdown/MDX, reStructuredText, AsciiDoc and HTML. Files of any other
format that match a glob (for example an OpenAPI `*.yaml`) are skipped, and changelogs are excluded by default. With
`Docs source:` the globs (`--docs` and the doc globs of `--map`) are relative to the source root.

Without `Published as a whole:` the doc set is `README*`, `docs/**`, `doc/**` and top-level `*.md`. Changelogs and
build output (`node_modules/`, `_site/`, `site/`, `build/`, `.docusaurus/`) are always excluded; add more exclusions
with `--exclude <glob>` when a run shows noise from generated files.

## Docs source

- **Local path**: an existing directory, such as a sibling checkout of the docs repository. A `@ref` is ignored, with
  a warning in the report.
- **Git URL** (`https://`, `ssh://`, `git@host:...`, `file://`): cloned shallowly once into the repository's git
  directory and refreshed on later runs; if the refresh fails, the cached copy is used and the report warns.

With an external source, two checks are off and the report says so: sections already edited in this branch cannot be
recognised (the branch does not touch the docs repository), and the navigation check is skipped.

## Docs impact map

The scanner matches documentation to code by shared terms: flag names, environment variables, routes, public
symbols, configuration keys. A mapping covers what has no shared term. When a changed file matches the code glob, every
section of the documents matching the doc glob is reported:

- with a term match too: confidence `high`;
- without one: adjustment `check`, confidence `low` - read the section against the change.

Example: `src/refunds/**` => `docs/api/refunds.md`. A branch that changes how partial refunds are rounded touches no
documented name, but the mapping still lists every section of the refunds page for a check.

Keep mappings narrow: a broad pair such as `src/** => docs/**` turns every run into a full documentation review.

## Base and report

- **Base**: not a key. The branch the pull request targets, when known (`--base`); otherwise origin's default branch,
  then `main`, then `master`. An unresolvable base stops the scanner with exit 2 and a `git fetch origin <base>` hint.
- **Report**: the path the user names, else `docs-impact-report.md` in the session scratchpad (`--out`). `--format
  json` gives the same content for tools; `--max-impacts N` caps the impacts table (default 50) and notes how many
  were left out.
