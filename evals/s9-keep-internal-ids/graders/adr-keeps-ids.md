---
type: regex
pattern: "FR-020[\\s\\S]*FR-031|FR-031[\\s\\S]*FR-020"
target:
  source: file
  path: docs/adr/0007-order-cancellation.md
---
The ADR keeps the existing requirement IDs and adds the new one.
