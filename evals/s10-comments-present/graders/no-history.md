---
type: regex
pattern: "#431|bug|replaced|last sprint|in production|incident|used to"
flags: i
match: not_contains
target:
  source: file
  path: ratelimit/bucket.go
weight: 2
---
Comments describe the code as it is now; history (the bug, the sprint, the replacement, the incident) belongs in
the commit message. Naming a rejected alternative with its reason ("a token bucket, not a fixed window, because...")
is design rationale, not history, and is allowed.
