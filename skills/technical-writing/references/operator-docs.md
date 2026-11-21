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

## Incident communication

Status page posts and notices to customers or stakeholders during an incident are user text, whoever runs the
software.

Each update says, in this order: what is affected (the feature, as users know it), since when, what users should
do meanwhile, and when the next update will come. State what is known; no guesses about the cause and no internal
component names. Each later update says what changed since the previous one. The closing update gives the time
the impact ended and whether users need to do anything.

## Postmortem

Blameless: it describes what the system and the process allowed, not who made a mistake.

| Section | Content |
|---|---|
| Summary | What happened, impact, duration, in three sentences |
| Impact | Who was affected, how much, for how long, with numbers |
| Timeline | Timestamps with time zone: detection, key decisions, mitigation, resolution |
| Causes | The trigger and the conditions that let it cause harm |
| What went well / what didn't | Detection, response, tooling |
| Actions | Each with owner, due date and tracker reference |

A postmortem shared with customers follows the user rules: no internal names, hosts or tracker keys.
