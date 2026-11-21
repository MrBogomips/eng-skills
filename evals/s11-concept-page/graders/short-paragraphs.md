---
type: regex
pattern: "^(?![#|>*`-]|\\d+\\.|\\s)(?:[^\\n.!?]|[.!?](?=\\S)|\\n(?![#|>*`-]|\\d+\\.|\\s*\\n))*?(?:[.!?](?:[ \\t]+|\\n(?![#|>*`-]|\\d+\\.|\\s*\\n)|$)(?:[^\\n.!?]|[.!?](?=\\S)|\\n(?![#|>*`-]|\\d+\\.|\\s*\\n))*?){5}"
flags: "m"
match: not_contains
target:
  source: file
  path: docs/concepts/feature-flags.md
---
No prose paragraph has five or more sentences.
