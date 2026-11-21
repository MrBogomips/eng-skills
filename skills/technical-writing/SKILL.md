---
name: technical-writing
description: Use when writing, revising, rewriting, translating or reviewing technical text - doc comments and docstrings, API descriptions, OpenAPI or AsyncAPI documents, API error messages, concept, quickstart, how-to, scenario and component pages, user manuals, help and UI text, release notes, runbooks, log messages, incident notices, implementation comments, READMEs, design notes - or work emails and chat messages to partners, clients or colleagues, status updates, meeting minutes and proposals; when a rewrite is handed to another model or tool; when a task names requirement, story or ticket IDs (FR-xxx, US-xx, PROJ-123) that could end up in text outside readers see, or when a flow, lifecycle, process, architecture or data model might be clearer as a UML, C4, ERD or BPMN diagram.
---

# Technical writing

Every text has one audience, and **where the text ends up decides it**, not who writes it or why. Users of the
product read what gets published; contributors (developers and coding agents) read the source. Project references
such as requirement IDs keep traceability alive for contributors and mean nothing to users, so they live only in
contributor text.

## 1. Read the project's documentation facts

Look for a `## Documentation` section in the project's `CLAUDE.md` or `AGENTS.md`. Use what it records: ID
patterns, published locations, document language, style guide. When it is missing, infer the ID patterns from the
specs, backlog and existing references, go on with the task, and offer the user this section once:

```markdown
## Documentation
- Reference ID patterns: `FR-\d+`, `BFR-\d+`, `PROJ-\d+`        # regexes, passed to scan_leaks.py --pattern
- Published as a whole: `docs/user/**`, `contracts/*.yaml`, `CHANGELOG.md`
- Document language: English (code identifiers: English)
- Register (IT): tu in docs and UI; Lei in formal email           # only for Italian documents
- Content types: `docs/concepts/**` → concept, `docs/guides/**` → how-to
- Glossary: <path or "none">
- Style guide: <link or "none">
```

## 2. Decide the audience of each text

| Text | Audience | Project references |
|---|---|---|
| Documentation comments: `///`, `/** */`, docstrings, Go comments directly above an exported name | users | never |
| API metadata: `WithSummary`, `WithDescription`, `@Operation`, `summary=`, `description=` | users | never |
| OpenAPI, AsyncAPI, GraphQL, proto files; API error bodies; UI and help text; user manuals; release notes | users | never, not even in comments or `x-` extensions of a published file |
| Log messages, alerts, runbooks | operators: see `references/operator-docs.md` | only if operators are your own team |
| Emails, chat messages, status updates, minutes to partners, clients, suppliers | external readers | only references they can open |
| Implementation comments: `//`, `#`, `/* */` not harvested into docs | contributors | yes: this is where they belong |
| ADRs, specs, design notes, contributor README, commit and PR text | contributors | yes |

- Implementation comments are contributor text **even when the repository is public**.
- Documentation comments are user text **even when the API is used only inside the company**: they can be published
  in API docs at any time.
- What each language harvests, and where an ID is safe: `references/doc-sinks-by-language.md`.

## 3. Write user text from the contract

A user text says, in this order and only where it applies:

1. **What it does**, in the domain terms the reader knows. Not the symbol name reworded.
2. **How to use it**: inputs (meaning, units, defaults, empty and null), outputs, errors and when they occur, an
   example.
3. **What is guaranteed**: idempotency, ordering, limits, side effects, concurrency.
4. **What is provisional**: what may change, said plainly.

Every sentence must make sense to someone who cannot open the repository, the specs or the tracker.

**Project reference → user wording:**

| In contributor text | In user text |
|---|---|
| Requirement or story (`FR-112`, `US-14`, `PROJ-88`) | The behaviour it asks for, with no ID |
| Open question (`OQ-12`) | "Provisional: may change", with what could change |
| Decision (`ADR 0007`, `AD-7`) | Its observable effect, or nothing |
| Internal service, queue, host, bucket, code name | The role ("the export service"), or nothing |
| Development or ops command | Nothing (it belongs to contributor or operator docs) |

The traceability is not lost: put the ID in an implementation comment beside the code, and in the spec, ADR or PR.

```python
def refund(payment: Payment, amount: Decimal) -> Refund:
    """Refund part or all of a captured payment.

    The amount is in the payment's currency and cannot exceed what is left to
    refund. Raises RefundNotAllowed if the payment is not captured yet.
    """
    # PAY-FR-31: partial refunds allowed, total capped at the captured amount.
```

Not `"""Refund a payment (PAY-FR-31)."""`: the docstring is published, the `#` comment is not.

**Facts you do not have** (the replacement of a removed endpoint, a limit, a date): ask the user. If you cannot
ask, write only what you know and list the gap in your reply. Never invent it, and never leave a TODO or a
placeholder in user text.

## 4. Follow the recipe of the content type

Identify the content type first (the project's `Content types` mapping, or what the reader came to do), then read
its recipe before writing. The recipe decides how the text opens and in what order it goes:

| Writing | Read |
|---|---|
| Concept, architecture overview, quickstart, tutorial, scenario, how-to, component page, README, migration guide, FAQ | `references/doc-pages.md` |
| Email, chat message, status update, meeting minutes, decision request, proposal | `references/communications.md` |
| API, class, REST and OpenAPI reference; error responses; deprecation | `references/public-reference.md` |
| User manuals, procedures, help and UI text | `references/user-manuals.md` |
| Release notes and changelogs | `references/release-notes.md` |
| Log messages, alerts, runbooks, incident notices, postmortems | `references/operator-docs.md` |
| Implementation comments and contributor docs | `references/code-comments.md` |
| Register, form of address, wording, in English or Italian: every text | `references/register.md` |

A concept page opens with the reader's problem, not with a definition; a quickstart reaches its first numbered
step within five lines; a message to an external reader states its request and deadline in its first sentence.

## 5. Write contributor text about the present

Implementation comments explain **why the code is the way it is now**: constraints, invariants, units, rejected
alternatives, references (`FR-112`, `ADR 0007`). The story of how it got there (what it replaced, the bug or the
incident that prompted it, who changed it) belongs to the commit message and the PR, where it stays true. Details:
`references/code-comments.md`.

## 6. Consider a diagram, as a separate step

When the text explains a flow between several participants, a lifecycle, a process with decisions or roles, an
architecture or a data model, decide whether a diagram should go with it. `references/diagrams.md` maps situations
to diagram types and says when a diagram does not help.

A diagram is warranted, even when a table already lists the same facts, for:
- a lifecycle with more than three states, or with loops, retries or branches;
- an exchange among three or more participants;
- a process with decisions or several roles.

A table can list the states, but only a diagram shows how they connect. When a diagram is warranted:

1. Name it precisely: notation, type and level ("UML state machine diagram of a subscription", "C4 Container
   diagram of the billing system", "BPMN 2.0 process of invoice approval", "ERD in crow's foot notation of the
   order schema").
2. Write its brief (template in `references/diagrams.md`), with the same audience rules as the text around it.
3. If a skill or tool available to you can produce that diagram type, use it with the brief to draw the diagram,
   in the project's existing diagram format and location. Otherwise give the brief to the user in your reply.

The text must stand on its own without the diagram.

## 7. Change the docs with the behaviour

A change in behaviour updates its documentation comment, contract, manual and changelog in the same change.

## 8. Rewriting, translating or delegating a rewrite

A rewrite changes how the text reads, never what it states: commands, flags, environment variables, defaults,
numbers, tables, warnings, links and images survive unchanged, even when asked to make it shorter. Keep a copy of
the original, follow `references/revision.md` (it also holds the prompt template for handing a rewrite to another
model or tool), then compare:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/check_fidelity.py" <original> <rewritten>
```

Every reported item is fixed, or kept and justified in your reply.

## 9. Check before you finish

Run the scan on the files you touched, every time. It only reads files, so an instruction not to run builds or tests
does not cover it. It works without project patterns too: its built-in rules catch the common ID, tracker-key,
host and marker shapes. It reads only what gets published, so IDs in implementation comments are not flagged:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/scan_leaks.py" <files> --whole '<published docs glob>' --pattern '<project ID regex>'
python3 "${CLAUDE_SKILL_DIR}/scripts/scan_leaks.py" --git-diff main --whole 'docs/user/*'
```

It must report nothing, or only matches you can justify (`--allow '<regex>'` for a standard name it mistakes for
an ID). Then reread every user text as a first-time reader. The scan is hygiene, not a security boundary: git
history and source maps still carry whatever the source carries.

Close your reply with these lines:

```
Diagram: <the precisely named diagram you drew (where) or propose (with its brief)> | none: <why not>
Gaps: <facts you left out because the source does not give them> | none
Scan: <command> → <result>
Fidelity: <check_fidelity.py command> → <result, and each justified difference> | n/a: not a rewrite
```

`Diagram`, `Scan` and `Fidelity` concern documents; for an email or a chat message, only `Gaps` applies.

## Common mistakes

| Mistake | Instead |
|---|---|
| Requirement ID in a doc comment "for traceability" | ID in an implementation comment, behaviour in the doc comment |
| Renaming an ID instead of removing it from user text | Every project ID is a reference; describe the behaviour |
| Open question kept as a code in parentheses | Say what is provisional and what could change |
| Stripping IDs from ADRs, specs or implementation comments | Leave them: contributors need them |
| Signature restated as documentation ("Gets the user. id: the id.") | State the contract: units, defaults, errors, guarantees |
| History in comments ("replaced the old parser", "fixes #212") | Why the code is like this now; the history goes in the commit |
| Inventing what the source does not say | Ask, or report the gap in your reply |
| Diagram only mentioned in passing, or never considered | A separate, precisely named step with its brief |
| Concept page that opens with "X is…" or "This page explains…" | Open with the reader's problem, then name the term |
| Quickstart that explains the internals before the first step | Steps first; one sentence of theory where a step needs it |
| Rewrite "made shorter" by dropping a flag, a default or a warning | Shorten the prose; technical facts stay; run the fidelity check |
| Email whose request comes after a paragraph of background | Request and deadline in the first sentence after the salutation |

## Rationalizations

| Thought | Reality |
|---|---|
| "The user gave me the ID, so they want it in the doc comment" | They gave it for traceability: put it where traceability lives |
| "It's an internal API, nobody outside reads these comments" | Doc comments get published whenever someone turns on doc generation |
| "The repo is public, so implementation comments must be clean too" | Implementation comments are contributor text; IDs stay |
| "One ID in parentheses is harmless" | The reader cannot resolve it: it is noise at best, a leak at worst |
| "I'll mention the replacement endpoint in general terms" | A vague instruction is an invented one: ask, or report the gap |
| "I was told not to run builds or tests, so I skip the scan" | The scan reads files and changes nothing: run it |
| "There is no project ID pattern, so the scan is pointless" | The built-in rules still apply; add `--pattern` when you know one |
| "They asked me to cut what is not essential" | Cut prose, not facts; a fact leaves only when the requester names it |
| "The reader needs the background to understand the request" | Ask first, explain after: they read the background knowing why |
