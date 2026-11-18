# Implementation comments and contributor docs

Implementation comments (`//`, `#`, `/* */` that no tool publishes) are written for developers and coding agents.
They are internal even in a public repository, and they are where traceability to requirements and decisions lives.

## Write

- **Why**, when the code can't say it: the constraint, the invariant, the reason for an unusual choice, the
  alternative rejected and why.
- **Units, ranges and assumptions** the types don't carry ("seconds", "never negative", "caller holds the lock").
- **References** that let a contributor find the requirement or decision behind the code: `// FR-112: only pending
  and confirmed orders can be cancelled.`, `// See ADR 0007.`
- **Workarounds**: what is being worked around, a link to the external issue, and the condition for removing it.
- **TODO** only with an owner or a tracker reference: `// TODO(PROJ-231): stream the file instead of buffering it.`

## Don't write

- **What** the next line does when the code already says it (`// increment i`, `// check state`).
- **History**: what the code replaced, the bug or incident that prompted it, who changed it and when. That story
  belongs in the commit message and the PR, which stay attached to the change. A comment states what is true now:

  ```python
  # Retries share one deadline: a slow first attempt must not let the total
  # wait exceed what the caller asked for.
  remaining = deadline - clock.now()
  ```

  not "Switched from per-attempt timeouts after the outage of last March (bug #212)".
- Commented-out code: version control keeps it.
- Comments that will go stale silently: duplicated values ("default is 30"), lists of callers.

A comment that no longer matches the code is worse than none: change or delete it in the same change as the code.

## Contributor docs

Contributor READMEs, design notes, specs and ADRs cite requirement, story and decision IDs freely: that is what
they are for. When you edit them, keep the existing references and add new ones.

Write them for a new team member: what this part is for, how it fits with the rest, how to build, run and test it,
where decisions are recorded. The structure and content of ADRs and architecture views belong to the project's
architecture practice. This guidance covers their wording and audience.
