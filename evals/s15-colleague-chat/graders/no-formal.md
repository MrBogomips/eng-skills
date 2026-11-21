---
type: regex
pattern: "Gentile|Cordiali saluti|Distinti saluti|Egregio|In attesa di (un )?(Suo|vostro) (cortese )?riscontro"
match: not_contains
target:
  source: file
  path: outbox/msg-marco.md
---
Informal register with a colleague in chat.
