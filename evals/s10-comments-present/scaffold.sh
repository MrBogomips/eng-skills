#!/usr/bin/env bash
set -euo pipefail
mkdir -p ratelimit
cat > ratelimit/bucket.go <<'EOF'
package ratelimit

import (
	"sync"
	"time"
)

type bucket struct {
	mu       sync.Mutex
	tokens   float64
	capacity float64
	rate     float64
	last     time.Time
}

func (b *bucket) allow(now time.Time) bool {
	b.mu.Lock()
	defer b.mu.Unlock()
	if now.Before(b.last) {
		now = b.last
	}
	b.tokens += now.Sub(b.last).Seconds() * b.rate
	if b.tokens > b.capacity {
		b.tokens = b.capacity
	}
	b.last = now
	if b.tokens < 1 {
		return false
	}
	b.tokens--
	return true
}
EOF
