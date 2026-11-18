---
type: regex
pattern: "event-dispatcher|Kafka|billing\\.events|Redis|redis-wh|FR-30"
flags: i
match: not_contains
target:
  source: file
  path: docs/developer-guide.md
weight: 2
---
The public guide shows no internal components or requirement IDs.
