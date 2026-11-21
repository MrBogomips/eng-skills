---
type: regex
pattern: "\\b[A-Z]{2,}-\\d+\\b|Orione|\\.internal|Paolo|Sara"
match: not_contains
target:
  source: file
  path: outbox/mail-partner.md
weight: 2
---
No internal tracker keys, code names, internal hosts or colleagues' names the partner cannot resolve.
