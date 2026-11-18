#!/usr/bin/env bash
set -euo pipefail
mkdir -p app
cat > app/main.py <<'EOF'
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import Response

from .deps import current_tenant, invoice_repo, pdf_renderer

app = FastAPI(title="ACME Billing API", version="1.4.0")


@app.get("/invoices/{invoice_id}")
def get_invoice(invoice_id: str, tenant=Depends(current_tenant), repo=Depends(invoice_repo)):
    """Return an invoice."""
    inv = repo.get(invoice_id)
    if inv is None or inv.tenant_id != tenant.id:
        raise HTTPException(status_code=404)
    return inv
EOF
cat > app/deps.py <<'EOF'
def current_tenant(): ...
def invoice_repo(): ...
def pdf_renderer(): ...
EOF
