---
name: docs-impact
description: Use before the final delivery of a branch - opening or updating its final pull request, handing it over, or when the user says the work is done - to check whether its changes affect the public documentation (README, user guide, API reference pages, a GitHub Pages site); also when asked what documentation a change, commit range or branch affects. Not for writing, revising or reviewing the documentation itself (that is technical-writing and the documentation-writer and documentation-reviewer agents).
---

# Documentation impact

A branch changes code; the public documentation describes the code as it was. This skill finds which documentation
sections the branch makes wrong, incomplete or unreachable, and says what each one needs. **It never edits
documentation and never writes replacement text**: the report is the deliverable, and the fix is a separate,
offered step.

The scanner finds what shares a term with the diff. You add what it cannot see, then hand the result over.

## 1. Resolve the inputs

Read the `## Documentation` section of the project's `AGENTS.md` or `CLAUDE.md`, if there is one, and map it to
scanner options (keys and examples: [references/configuration.md](references/configuration.md)):

| Key | Option |
|---|---|
| `Published as a whole:` globs | one `--docs` per glob (the doc set; default: README, `docs/`, `doc/`, top-level `*.md`) |
| `Docs source: <path or git URL>[@ref]` | `--source <path or URL>` and `--source-ref <ref>` |
| `Docs impact map: <code glob> => <doc glob>` (repeatable) | one `--map "<code glob> => <doc glob>"` each |
| `Docs pages: off` | `--pages off` |

Base: the branch the pull request targets when the user or the project names it (`--base`); otherwise leave
`--base` out and the scanner uses origin's default branch, then `main`, then `master`.

Report path: the path the user names; otherwise `<session scratchpad>/docs-impact-report.md`.

## 2. Run the scanner

```sh
python3 "${CLAUDE_SKILL_DIR}/scripts/docs_impact.py" --repo . [--base main] [options from step 1] --out <report path>
```

- **Exit 0**: the report is written, possibly with "No documentation impact found."
- **Exit 2**: one line on stderr (bad argument, git or source failure, unresolvable base). Fix what it names
  (for a missing base, `git fetch origin <base>` as the hint says) and run again. If it still fails, tell the user
  the check could not run and why. **Never report "no impact" after an exit 2.**

What the report contains, and GitHub Pages detection: [references/github-pages.md](references/github-pages.md).

## 3. Add the judgment the scanner cannot

Read the report, then `git diff <base>...HEAD` and the sections the report names. Append a `## Assessment`
section to the same report file with these parts, in order, each omitted when empty:

1. **Pending adjustments**: one line per impacted section, `path#anchor`: the adjustment and the concrete change,
   naming old and new values from the diff (`update`: replace `--currency-code` with `--currency`; `obsolete`:
   remove the `PAYMENTS_RETRY_LIMIT` variable, it no longer exists; `check`: re-read against the changed code).
2. **Missed by the scanner**: sections whose prose describes changed behaviour with no shared term, such as a
   default timeout, a status code, the order of steps, a limit. Give the section, the code change and why it is
   affected. Look at the sections nearest the changed code before declaring there are none.
3. **Struck as false positives**: report rows that need nothing, each with the reason (the term is a common word
   in that section, the change is internal, the section already says the new thing).
4. **Undocumented additions**: each new public element named the way a reader meets it - the full command line,
   the flag with its command, the HTTP method and route (`payctl refund`, not `refund`; `POST /v1/refunds`, not
   `refunds`) - the code file that defines it, the page where readers would look for it, and the statement that
   no existing page or section documents it. Its options and behaviour are the writer's to read from the code: do
   not list them.
5. **Navigation**: new pages missing from the site navigation, with their published URL, so readers cannot reach
   them from the menu.
6. **Verdict**: one sentence. When nothing is pending, missed, undocumented or missing from navigation, state that
   the branch has no impact on the public documentation.

Sections listed under "Already updated in this branch" are done unless the diff shows the edit is incomplete.

Naming old and new values is fine; a drafted sentence, paragraph or code block meant to be pasted into the
documentation is not. The writer drafts, from the report.

## 4. Present and offer

Reply with a short summary (counts by adjustment, the undocumented additions, the navigation gaps, the verdict) and
the report path. Then offer, without doing it:

- the `documentation-writer` agent, to make the changes, or
- the `documentation-reviewer` agent, for a quick review of the affected pages,

passing the report's `## Review context` list and your `## Assessment` as their starting context. Do nothing more
unless the user accepts; when the user cannot be asked, stop at the offer.

## Common mistakes

| Mistake | Instead |
|---|---|
| Editing a page or the site navigation "while you are there" | Report it; the documentation agents make the change on request |
| Writing the corrected paragraph into the report | Name the section, the adjustment and the old and new values |
| Treating a removed element as a rename (`update`) | A removal with no successor is `obsolete`: the text goes |
| Naming an undocumented addition by its internal symbol | Name it as the reader types or sees it |
| "No impact" because the scanner found nothing | Read the diff for prose-only impacts first; never after an exit 2 |
