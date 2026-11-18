#!/usr/bin/env bash
set -euo pipefail
mkdir -p docs/adr internal/cancel
cat > docs/adr/0007-order-cancellation.md <<'EOF'
# 0007. Order cancellation is a state transition, not a delete

- Status: accepted
- Requirements: FR-020, FR-021

## Context

FR-020 requires customers to cancel orders before shipment; FR-021 requires the cancellation to be auditable.

## Decision

Cancellation sets the order state to CANCELLED and records who cancelled it and when. Rows are never deleted.

## Consequences

- Reports must filter out cancelled orders.
EOF
cat > internal/cancel/cancel.go <<'EOF'
package cancel

import "time"

func cancel(o *order, by string, now time.Time) error {
	// check state
	if o.state != "PENDING" && o.state != "CONFIRMED" {
		return errNotCancellable
	}
	// FR-021: cancellation must be auditable, so we record who and when instead of deleting (ADR 0007).
	o.state = "CANCELLED"
	o.cancelledBy = by
	o.cancelledAt = now
	return nil
}
EOF
cat > README.md <<'EOF'
# orders-service

Open source on GitHub under the Apache-2.0 licence.
EOF
