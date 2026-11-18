#!/usr/bin/env bash
set -euo pipefail
mkdir -p orders
cat > go.mod <<'EOF'
module github.com/acme/orders-sdk

go 1.22
EOF
cat > README.md <<'EOF'
# orders-sdk

Public Go module published to pkg.go.dev for customers integrating with ACME Orders.
EOF
cat > orders/orders.go <<'EOF'
package orders

import "errors"

type State string

const (
	Pending   State = "PENDING"
	Confirmed State = "CONFIRMED"
	Shipped   State = "SHIPPED"
	Cancelled State = "CANCELLED"
)

type Order struct {
	ID    string
	State State
}

var ErrNotFound = errors.New("order not found")
EOF
