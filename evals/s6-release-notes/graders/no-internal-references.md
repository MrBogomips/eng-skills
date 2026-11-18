---
type: regex
pattern: "PAY-\\d+|BFR-\\d+|#\\d{3}|Falcon|Bianchi|Neri|Verdi|k8s|ix_invoices|export-worker"
match: not_contains
target:
  source: file
  path: RELEASE-NOTES-2.4.0.md
weight: 2
---
No tracker keys, issue numbers, code names, author names or internal names in customer release notes.
