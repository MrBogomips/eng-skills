---
type: regex
pattern: "^\\s*ciao\\b|\\b(fammi|fatemi) sapere\\b|\\bun abbraccio\\b"
flags: "im"
match: not_contains
target:
  source: file
  path: outbox/mail-partner.md
---
Formal register to an external partner.
