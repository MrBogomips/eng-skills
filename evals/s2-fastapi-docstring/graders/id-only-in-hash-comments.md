---
type: regex
pattern: "^(?![ \\t]*#).*BFR-7"
flags: m
match: not_contains
target:
  source: file
  path: app/main.py
weight: 2
---
BFR-7 may appear only in `#` implementation comments, never in docstrings or API metadata strings.
