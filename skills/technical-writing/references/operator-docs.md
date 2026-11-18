# Log messages, alerts and runbooks

Operators run the software. If they are your own team, operator text is contributor text: internal names,
commands and references are fine. If customers run it (self-hosted products, on-premises installs), operator text is
user text and follows the user rules in `SKILL.md`.

## Log messages

- One event per message: what happened and its outcome ("Export failed: storage quota exceeded").
- Include the identifiers someone needs to find the affected thing: order id, request id, tenant id. Prefer
  structured fields to values inside the sentence.
- Never log secrets, tokens, passwords or personal data beyond what policy allows.
- The level means something: `error` needs action, `warn` may need action, `info` records normal operation, `debug`
  is for developers.
- Keep the message text stable: alerts and dashboards often match on it.

## Alerts

- The alert names the symptom and its impact ("Webhook deliveries failing for 15 min: customers are not receiving
  events"), not only the metric.
- Link the runbook.

## Runbooks

| Section | Content |
|---|---|
| Symptom | What the alert or report looks like |
| Impact | Who is affected and how badly |
| Diagnosis | Ordered checks, each with the command or dashboard and what a good or bad result looks like |
| Remediation | Steps, safest first, with how to confirm each worked |
| Escalation | When to stop and whom to call |

Commands are copy-pasteable, with placeholders marked (`<export-id>`). State which steps are destructive.
