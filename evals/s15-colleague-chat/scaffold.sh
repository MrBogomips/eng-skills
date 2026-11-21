#!/usr/bin/env bash
set -euo pipefail
mkdir -p notes outbox
cat > notes/review.md <<'MD'
- PR #318 sul retry dei webhook, tocca il modulo di Marco (dispatcher)
- mi serve la sua review entro domani 12:00, merge in finestra di rilascio delle 15
- punti dove voglio il suo parere: backoff cap a 5 min ok? e il cambio della chiave di idempotenza
- se non riesce, chiedo a Luca
MD
