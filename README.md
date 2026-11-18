# eng-skills

A Claude Code plugin with skills and agents for engineering work: technical writing now, architecture and design
next.

## Contents

| Component | Kind | Use it to |
|---|---|---|
| `technical-writing` | skill | Write doc comments, API references, OpenAPI descriptions, error messages, user manuals, release notes, runbooks and implementation comments for the audience each text reaches. It keeps requirement and ticket IDs out of published text without losing traceability, and it recognises when a UML, C4, ERD or BPMN diagram should go with the text. |
| `documentation-writer` | agent | Hand off a scoped documentation pass (a module's public API, a guide section, release notes) to its own context. |
| `documentation-reviewer` | agent | Review written or changed documentation independently, read-only, with ranked findings. |

The skill bundles `scripts/scan_leaks.py` (Python 3, standard library only). The script reports project references
in the parts of files that get published: documentation comments, API metadata, OpenAPI and AsyncAPI documents,
and any file marked as published.

## Project configuration

The skill reads an optional `## Documentation` section in the target project's `CLAUDE.md` or `AGENTS.md`:

```markdown
## Documentation
- Reference ID patterns: `FR-\d+`, `PROJ-\d+`
- Published as a whole: `docs/user/**`, `contracts/*.yaml`, `CHANGELOG.md`
- Document language: English
- Style guide: none
```

## Development

```sh
claude --plugin-dir .                  # try the plugin from this checkout
claude plugin validate .
python3 -m unittest discover tests
```
