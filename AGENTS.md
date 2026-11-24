# AGENTS.md

This file provides guidance to coding agents working in this repository. `CLAUDE.md` is a symbolic link to it.

## Project

`eng-skills` is a Claude Code **plugin** that bundles skills for engineering work, such as
`technical-writing`, `ddd-architect` and `togaf-architect`. The product is skill content (Markdown
instructions plus any bundled references and scripts), not an application: there is no build step.

## Plugin layout

Follows the standard Claude Code plugin structure:

- `.claude-plugin/plugin.json`: plugin manifest (name, version, description). The version here is the
  plugin's release version.
- `skills/<skill-name>/SKILL.md`: one directory per skill. The YAML frontmatter `name` must match the
  directory name; `description` is what triggers the skill, so it states *when* to use it, not just
  what it does.
- `skills/<skill-name>/references/`, `scripts/`, `assets/`: optional supporting files, loaded on demand
  and referenced by relative path from `SKILL.md`. Keep `SKILL.md` lean and push detail here. Invoke
  bundled scripts through their interpreter (`python3 scripts/x.py`), never by bare path.
- `agents/<agent-name>.md`: subagents shipped with the plugin (frontmatter `name`, `description`, `tools`).
- `tests/`: unit tests for bundled scripts (standard-library `unittest`).
- `evals/`: eval cases for `claude plugin eval` (default location).

Skills and agents are generic: no project names, client names or project-specific identifiers. A skill
that needs project facts reads them from the target project's own `CLAUDE.md` / `AGENTS.md`.

## Commands

```sh
claude plugin validate .                 # validate the manifest and every skill/agent/command
claude --plugin-dir .                    # start a session with this plugin loaded from the working tree
claude plugin details <plugin-name>      # component inventory and projected token cost
claude plugin eval .                     # run the eval suite (with a no-plugin baseline arm)
claude plugin eval . --case '<glob>'     # run a single eval case or a subset
claude plugin tag .                      # create the {name}--v{version} release tag
python3 -m unittest discover tests       # unit tests for bundled scripts
python3 -m unittest tests.test_scan_leaks.GoTest.test_package_doc_comment   # a single test
python3 -m coverage run -m unittest discover tests && python3 -m coverage report
```

Run evals with `--no-publish` (reports stay local). The cases write files and use the scanner, so they need
`--scaffold --allow-tools Bash Write Edit`:

```sh
claude plugin eval . --scaffold --allow-tools Bash Write Edit --no-publish --trust-plugin --runs 1
```

Regex graders must target what the guidance forbids, not words a correct answer may also use (a rejected
alternative named with its reason is not history).

Eval grader syntax (not in `--help`):

- `--case` takes `*` and `?` only: `[..]` and `{..}` match nothing. Run one case per call to select several.
- Regex graders: flags go in `flags: "im"`; inline `(?i)` is rejected.
- LLM graders read a file with `focus: {source: file, path: ...}`; `target:` is refused and `focus: files` shows
  the judge only the paths.
- One criterion per LLM grader, and `--judge-model sonnet` for judgments on content: compound criteria get
  unstable votes. Prefer a regex when the rule is checkable.
- `--keep-temp` keeps the traces: read the agent's real output before blaming the skill or the grader.

## Authoring skills

Create and revise skills with the `superpowers:writing-skills` skill: write the eval or pressure test
first, confirm the baseline fails without the skill, then write the skill.

- Each deliverable is a skill, plus agents where a separate context helps, such as a writer/reviewer pair for
  independent review.
- Examples in a skill come from a different domain than its test scenarios, so tests measure the rules, not
  recall of the example.

## Working documents

- `drafts/` (committed): plans, decision logs and design notes for skills under development. Working material,
  never authoritative for users.
- `skills/`, `agents/`, `README.md` (authoritative): the shipped content and its public description.
- Anything else AI-generated stays in the session scratchpad.

## Git / PR Working Policy
- Worktree usage: disabled
- Worktree location: n/a
- Base branch: main
- Recorded on: 2026-11-18
