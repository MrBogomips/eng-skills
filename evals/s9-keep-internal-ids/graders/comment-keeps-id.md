---
type: regex
pattern: "//[^\\n]*FR-021"
target:
  source: file
  path: internal/cancel/cancel.go
weight: 2
---
The implementation comment keeps its requirement ID even though the repository is public.
