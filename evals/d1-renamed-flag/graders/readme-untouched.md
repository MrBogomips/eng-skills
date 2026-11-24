---
type: regex
pattern: "--output-dir"
match: contains
target:
  source: file
  path: README.md
---
README.md still carries the old flag, so it was not edited.
