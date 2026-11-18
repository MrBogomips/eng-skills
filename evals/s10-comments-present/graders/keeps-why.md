---
type: regex
pattern: "clock|NTP|backwards|backward"
flags: i
target:
  source: file
  path: ratelimit/bucket.go
---
The reason for the clamp on now is still explained.
