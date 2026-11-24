---
type: regex
pattern: "batch\\.md"
match: not_contains
target:
  source: file
  path: mkdocs.yml
---
mkdocs.yml was not edited to add the page.
