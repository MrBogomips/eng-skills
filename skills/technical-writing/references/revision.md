# Rewriting, translating and delegating a rewrite

A rewrite changes how a text reads, never what it states. Readability work, translation, restructuring and a
rewrite handed to another model or tool all follow this file.

## What must survive, verbatim

- inline code and code blocks: commands, flags and their values, file and script names, skill, hook and agent names;
- environment variables and configuration keys, with their default values;
- numbers in prose with their units: limits, timeouts, sizes, percentages, dates;
- tables: every row and every cell;
- warnings and other admonitions;
- link targets, relative ones included, and image references with their captions;
- heading anchors that other pages link to (change a heading's text only if nothing links to it, or add the old
  anchor back).

## What may change

Prose, sentence order, the order of sections, paragraph splits, prose turned into lists or tables and back, heading
wording (anchors above), repetitions of a fact that stays elsewhere on the page (a default stated in the prose and
in the table may stay in the table only), the register (`register.md`), the structure required by the content type (`doc-pages.md`).

"Shorter" and "cut what is not essential" shorten prose: repetition, filler, preamble. A fact from the list above
leaves the page only when the requester names it, or when you move it to another page and link it; report each one.

## Procedure

1. Copy the original before editing (`<name>.orig.md`, or use the version in git).
2. Rewrite following the content type and the register.
3. Run the check:

   ```bash
   python3 "${CLAUDE_SKILL_DIR}/scripts/check_fidelity.py" <original> <rewritten>
   ```

   It reports every item missing from the rewrite or added to it, with its line. Fix each one, or keep it and
   justify it in your reply (`--allow '<regex>'` for a change you justify, such as a number written as a word).
   Changed anchors are warnings: check whether anything links to them.
4. Delete the copy if you made one in the working tree, unless the requester asked for it.

## Delegating a rewrite to another model or tool

Assemble the prompt from the content type's recipe, the register and the preserve list; don't send the whole skill.
Write it in the language of the target document:

```markdown
Rewrite <file> for <audience>. Content type: <type>.

Structure:
<the order and opening rule for this type, from doc-pages.md>

Form: paragraphs of at most 4 sentences; bullet lists for parallel items; numbered lists for sequences; tables for
items that share attributes; one-sentence bridges between sections, no "in this section we will see".

Register: <language>, <form of address>, <formality>; one term per concept: <glossary terms>.

Keep exactly, each at least once: inline code, code blocks, commands and flags, file, script, skill
and hook names, environment variables (<prefix>_*), configuration keys and defaults, numbers with units, every
table row and cell, warnings, link targets and image references with captions, headings that other pages link to.

Do not add facts, commands or links that are not in the original. Return the full file.
```

Run `check_fidelity.py` on what comes back before accepting it, exactly as for your own rewrite.
