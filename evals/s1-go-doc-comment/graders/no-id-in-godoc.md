---
type: regex
pattern: "FR-112[^\\n]*\\n(?:[ \\t]*//[^\\n]*\\n)*func Cancel"
match: not_contains
target:
  source: file
  path: orders/orders.go
weight: 2
---
The requirement ID must not be part of the doc comment directly above the exported function.
