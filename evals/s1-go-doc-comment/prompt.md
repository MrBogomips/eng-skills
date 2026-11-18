---
max_turns: 25
timeout_seconds: 600
allowed_tools: [Read, Write, Edit, Glob, Grep, Skill, Bash]
tags: [technical-writing]
---
Implement requirement FR-112 in package `orders` and document it properly.

FR-112 — Cancel order: an order can be cancelled only while its state is PENDING or CONFIRMED; cancelling sets the state to CANCELLED. Cancelling an order in any other state returns a dedicated error. Cancelling an already cancelled order is a no-op and returns nil.

Add an exported function `Cancel(o *Order) error` and the error value it needs, both in orders/orders.go. Do not run builds or tests.
