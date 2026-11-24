# eng-skills

A Claude Code plugin with skills and agents for engineering work: technical writing and documentation impact checks now,
architecture and design next.

## Contents

| Component | Kind | Use it to |
|---|---|---|
| `technical-writing` | skill | Write doc comments, API references, OpenAPI descriptions, error messages, user manuals, release notes, runbooks and implementation comments for the audience each text reaches. It keeps requirement and ticket IDs out of published text without losing traceability, and it recognises when a UML, C4, ERD or BPMN diagram should go with the text. |
| `docs-impact` | skill | Check which documentation a branch's code changes affect. It compares the branch with its base, matches the public terms the change touches (flags, environment variables, routes, symbols, configuration keys) and any configured code-to-docs mapping against the documentation, and writes a report of the sections to adjust. It also detects GitHub Pages and checks the navigation. |
| `documentation-writer` | agent | Hand off a scoped documentation pass (a module's public API, a guide section, release notes) to its own context. |
| `documentation-reviewer` | agent | Review written or changed documentation independently, read-only, with ranked findings. |

The skill bundles `scripts/scan_leaks.py` (Python 3, standard library only). The script reports project references
in the parts of files that get published: documentation comments, API metadata, OpenAPI and AsyncAPI documents,
and any file marked as published.

The `docs-impact` skill bundles `scripts/docs_impact.py` (Python 3, standard library only). The script compares the
branch with its base and reports the documentation sections that the change affects.

## Project configuration

The skills read an optional `## Documentation` section in the target project's `CLAUDE.md` or `AGENTS.md`:

```markdown
## Documentation
- Reference ID patterns: `FR-\d+`, `PROJ-\d+`
- Published as a whole: `docs/user/**`, `contracts/*.yaml`, `CHANGELOG.md`
- Document language: English
- Style guide: none
- Docs source: https://github.com/example/payments-docs.git@main
- Docs impact map: `src/refunds/**` => `docs/api/refunds.md`
- Docs pages: off
```

`Published as a whole` also sets the doc set that `docs-impact` checks, but `docs-impact` scans only documentation formats (Markdown/MDX, reStructuredText, AsciiDoc, HTML) and excludes changelogs by default, so entries such as `contracts/*.yaml` and `CHANGELOG.md` above are ignored by it. The other three keys belong to `docs-impact`:

- `Docs source`: where the documentation lives when it is not the repository itself, a local path or a git URL,
  optionally `@<ref>`.
- `Docs impact map`: a code glob and the pages that document it (`<code glob> => <doc glob>`); repeat the key for
  each pair.
- `Docs pages: off`: skip GitHub Pages detection, URLs and the navigation check.

## Development

```sh
claude --plugin-dir .                  # try the plugin from this checkout
claude plugin validate .
python3 -m unittest discover tests
```
