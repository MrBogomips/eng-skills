#!/usr/bin/env bash
set -euo pipefail
cat > commits.txt <<'EOF'
a1b2c3d feat(export): bulk CSV export of invoices (PAY-1432) — Marco Bianchi
b2c3d4e fix(auth): token refresh race when two tabs refresh at once, closes #872 — Sara Neri
c3d4e5f chore(falcon): migrate export-worker to Falcon queue on k8s-prod-eu1 — Luca Verdi
d4e5f6a feat(api)!: remove deprecated /v1/reports endpoint (PAY-1388, BFR-22) — Marco Bianchi
e5f6a7b fix(ui): invoice totals rounded to 2 decimals instead of 3 (PAY-1450) — Sara Neri
f6a7b8c perf(db): add index ix_invoices_tenant_created on invoices — Luca Verdi
EOF
