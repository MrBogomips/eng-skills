---
type: regex
pattern: "in this section,? (we|you) will|in the next section,? (we|you) will|let's (now )?(dive|take a look)"
flags: "i"
match: not_contains
target:
  source: file
  path: docs/concepts/feature-flags.md
---
No filler bridges.
