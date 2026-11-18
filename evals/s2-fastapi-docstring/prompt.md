---
max_turns: 25
timeout_seconds: 600
allowed_tools: [Read, Write, Edit, Glob, Grep, Skill, Bash]
tags: [technical-writing]
---
Add the endpoint `GET /invoices/{invoice_id}/pdf` to app/main.py, implementing BFR-7: "Download invoice as PDF. Returns the PDF (application/pdf). 404 if the invoice does not exist or belongs to another tenant." Use `pdf_renderer` from deps (it has a `render(invoice) -> bytes` method). Document the endpoint properly for our API docs. Do not run builds or tests.
