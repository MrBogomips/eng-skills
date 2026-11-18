---
max_turns: 25
timeout_seconds: 600
allowed_tools: [Read, Write, Edit, Glob, Grep, Skill, Bash]
tags: [technical-writing]
---
Add good comments to ratelimit/bucket.go. Background: last sprint we replaced the fixed-window limiter with this token bucket to fix bug #431 (bursts at window boundaries let clients through at twice the limit). The clamp on `now` is there because the clock source can go backwards after an NTP adjustment, and we got negative token counts in production. Do not run builds or tests.
