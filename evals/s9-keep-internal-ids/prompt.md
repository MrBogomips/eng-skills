---
max_turns: 25
timeout_seconds: 600
allowed_tools: [Read, Write, Edit, Glob, Grep, Skill, Bash]
tags: [technical-writing]
---
Two small tasks:
1. Update ADR docs/adr/0007-order-cancellation.md: the decision now also covers bulk cancellation, required by FR-031 (a customer can cancel several orders at once; each cancellation is recorded individually).
2. This repository is public on GitHub. Tidy up the comments in internal/cancel/cancel.go before we publish the next release.
