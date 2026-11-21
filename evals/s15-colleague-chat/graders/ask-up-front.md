---
type: llm
focus:
  source: file
  path: outbox/msg-marco.md
---
PASS only if it is a single chat message (no subject line, no email-style closing) whose first two sentences, together with the greeting, state the ask (review of PR #318) and the deadline (tomorrow 12:00), followed by the two points to look at as a short list. FAIL if it opens with a bare greeting or background before the ask.
