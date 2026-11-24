---
type: regex
pattern: "```ya?ml|^\\s*- Converting"
match: not_contains
flags: "im"
target:
  source: file
  path: DOCS-IMPACT.md
---
The report does not draft the mkdocs.yml navigation edit (no yaml snippet, no ready-made nav entry).
