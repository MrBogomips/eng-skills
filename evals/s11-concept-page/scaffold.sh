#!/usr/bin/env bash
set -euo pipefail
mkdir -p notes docs/concepts
cat > notes/flags-design.md <<'MD'
# Flags design notes

- A flag is a named boolean or multivariate value evaluated per request against an evaluation context (user id, tenant, attributes).
- Rules are ordered; first match wins; fallthrough to the default variation. Percentage rollouts hash `flagKey + userId` (murmur3) into 0..9999, so a user stays in the same bucket.
- The SDK keeps a local copy of all rules, refreshed over a streaming connection; evaluation is local, no network call per check. If the stream drops, the last known rules are used; at first start with no rules the code default passed to `client.variation(key, ctx, default)` is returned.
- Typical uses: ship code dark and turn it on later, gradual rollout, kill switch, per-tenant entitlements.
- Flags should be removed once fully rolled out; stale flags are reported in the dashboard after 30 days at 100 %.
- Events: every evaluation emits an impression event, batched every 5 s.
MD
