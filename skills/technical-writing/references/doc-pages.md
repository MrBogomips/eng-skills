# Documentation pages by content type

Pick the type by what the reader came to do. A page has one type; when a draft serves two, split it and link the
parts. The type decides how the page opens and in what order it goes, not its length.

## Concept / explanation (also architecture overviews)

The reader wants a mental model before using the thing. Order:

1. **The problem**, in the reader's situation: what goes wrong or is hard without this. One short paragraph.
2. **The idea** that solves it, in plain words.
3. **The term** and **the mechanism**: name it now, then how it works. Sequences go in a numbered list or a diagram.
4. **Trade-offs and limits**: what it costs, when not to use it.
5. **Where next**: the how-to or reference pages that apply it.

Each section after the first opens with one sentence that says why it follows from the previous one. Run the
diagram step of `SKILL.md` for every mechanism with more than three moving parts.

```markdown
# Image variants

You upload one photo, but a phone, a laptop and a print preview each need a different size. Resizing on every
request makes pages slow; storing every size in advance wastes space on sizes nobody asks for.

The service creates each size the first time someone asks for it, then keeps it.

A **variant** is one stored rendition of an original: ...
```

Not `# Image variants` followed by "A variant is a stored rendition..." or "This page explains variants": the
reader meets the term before knowing why it matters.

## Quickstart / tutorial

The reader wants a first success. Order:

1. **What you will have at the end** and the **prerequisites**: together, at most five lines.
2. **Numbered steps**. Each step is one action, its command or UI path, and the output the reader should see.
3. **Result**: how to tell it worked.
4. **Next steps**: links to the concept page and the how-to guides.

One path only: one platform, one backend, the defaults. Alternatives and options go to how-to and reference pages.
Theory gets at most one sentence inside the step that needs it. When the reader must understand a concept to go
on, even when asked to explain it, add one short section after the result (at most five sentences, or a list of
at most three items) and link the concept page for the rest; a quickstart never becomes the concept page.

## Scenario / how-to

The reader has a goal already. Order: the goal in their words ("You want to…"), when this applies, prerequisites,
numbered steps with the expected result of each, the result, then variants and troubleshooting. One scenario per
page or per section; a section heading names the goal ("Rotate the signing key"), not the feature.

## Component reference page

The reader looks up one component (a module, a command, a service, a plugin part). Fixed order:

1. **Purpose**: one sentence.
2. **When to use it** and **when not to**, with the alternative.
3. **How it works**: short; link the concept page for depth.
4. **Configuration**: a table with name, default, allowed values, effect.
5. **Commands** or **API**: each with an example and its output.
6. **Limits** and known constraints.
7. **See also**.

Every component page of a set uses the same headings in the same order, so readers find the same fact in the same
place.

## README / landing page

Order: what it is and why it exists (at most three sentences), use cases, installation, minimal usage, links to the
docs. No history, no internals, no roadmap. A contributor README follows `code-comments.md` instead.

## Migration / upgrade guide

Order: who must act and by when, the breaking change, before and after side by side, ordered steps, how to verify,
how to roll back. Every removed thing names its replacement; if the source does not give one, it is a gap to report.

## FAQ / troubleshooting

Each entry: the symptom as the reader sees it (the error text, the behaviour), the cause, the fix. Questions use the
reader's words. An FAQ is never the only place a fact lives: link the page that owns it.

## Form rules for every page

| Content | Form |
|---|---|
| One idea | A paragraph of at most 4 sentences (about 80 words) |
| Three or more parallel items, no order | Bullet list |
| Steps or anything where order matters | Numbered list |
| Items sharing two or more attributes | Table |
| A flow, lifecycle or structure | Diagram, with the text still complete |

- Bridges between sections are one sentence that says why the next section follows. Never "In this section we
  will see…", "Let's dive in", or a summary of what the page is about to say.
- Headings say what the section answers or does ("Choose a retention period"), not a bare noun when a task fits.
- Register and wording: `register.md`.
