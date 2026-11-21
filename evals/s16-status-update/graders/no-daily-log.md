---
type: regex
pattern: "^\\s*[-*]?\\s*\\**(mon|tue|wed|thu|fri)\\b"
flags: "im"
match: not_contains
target:
  source: file
  path: status/week-47.md
---
Not a day-by-day log.
