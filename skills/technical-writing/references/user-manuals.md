# User manuals, help and UI text

## Choose the kind of page

Keep these four kinds apart: a page that mixes them serves no reader well. The structure of each kind, and of
concept, quickstart, component and README pages: `doc-pages.md`.

| Kind | Reader wants to | Shape |
|---|---|---|
| Tutorial | Learn by doing, first time | A guided path with a working result at the end |
| How-to guide | Reach a goal they already have | Goal, prerequisites, numbered steps, result |
| Reference | Look up a fact | Tables and lists, complete and consistent |
| Explanation | Understand why or how it works | Prose, concepts, trade-offs |

## Procedures

1. Start with the goal and who can do it ("As a tenant administrator, you can...").
2. List prerequisites: role or permission, data needed, limits.
3. One action per step, imperative mood. UI labels exactly as on screen, in bold: **Billing > Invoices > Export**.
4. Say what the user sees when a step works, and what to do when it does not.
5. End with the result and the next step, if there is one.

Describe what the user sees and does. The services, queues, storage and commands behind a feature are not part of a
manual. Translate them into what the user notices: "Large exports run in the background; you receive an e-mail
when the file is ready."

Provisional behaviour (an open question in the project) is described as it works today. Add "may change" only when
the user needs to plan around it.

## Voice

Second person, present tense, active voice, the words of the product's UI, one term per concept, no internal
jargon: `register.md`, which also covers Italian.

## Help and UI text

- Buttons and menu items: a verb that says what happens ("Export invoices", not "OK" or "Submit").
- Error messages: what happened, why if the user can act on it, and what to do next. No codes the user can't use,
  no stack traces, no internal names.
- Strings meant for translation: whole sentences with named placeholders (`"{count} invoices exported"`), never
  sentences assembled from fragments. Leave room for longer translations.
- Empty states say what the screen is for and how to fill it.

## Accessibility

- Link text says where it goes ("See Export limits"), never "click here".
- Every image and diagram has alt text, or a text equivalent next to it.
- Headings in order, without skipping levels. Meaning is never carried by colour alone.
- Screenshots go stale quickly: use them only where words can't do the job.
