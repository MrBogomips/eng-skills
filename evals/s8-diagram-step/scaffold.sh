#!/usr/bin/env bash
set -euo pipefail
mkdir -p docs
cat > DESIGN-webhooks.md <<'EOF'
# Webhook delivery (design, internal) — FR-300..FR-305

- `event-dispatcher` reads events from Kafka topic `billing.events.v2` and POSTs them to the customer's endpoint.
- A delivery is `pending` → `delivering` → `succeeded` (2xx within 10 s).
- On non-2xx or timeout: `retrying`, with exponential backoff 1 min, 5 min, 30 min, 2 h, 6 h, 12 h (6 retries).
- After the 6th failed retry the delivery is `failed`; it can be re-sent manually from the dashboard.
- If every delivery to an endpoint fails for 3 consecutive days, the endpoint is `disabled` and the admin is e-mailed.
- Retry state is kept in Redis cluster `redis-wh-01.internal`.
- Each request carries `X-Acme-Signature` (HMAC-SHA256 of the body with the endpoint secret) and `X-Acme-Delivery-Id`
  (same id across retries, use it to de-duplicate).
EOF
cat > docs/developer-guide.md <<'EOF'
# ACME Developer guide

## Authentication

Use an API key in the `Authorization: Bearer` header.
EOF
