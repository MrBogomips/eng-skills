#!/usr/bin/env bash
set -euo pipefail
mkdir -p notes outbox
cat > notes/appunti-integrazione.md <<'MD'
# Appunti integrazione spedizioni (interni)

- Contratto API v2 spedizioni pronto: INT-482 chiuso, review fatta da Paolo e Sara. Spec in contracts/shipments-v2.yaml (allegarla).
- Cambia rispetto alla v1: campo `weight` ora in grammi (prima kg), nuovo stato `in_customs`, webhook firmati HMAC-SHA256.
- Ci serve OK formale del partner sul contratto entro venerdì 5 dicembre, altrimenti slitta il rilascio in staging (previsto 12/12) - vedi INT-501.
- Domande aperte per loro: 1) gestiscono già i pesi in grammi lato loro? 2) chi ruota il segreto webhook? 3) ambiente di test loro disponibile dal 9/12?
- Ambiente staging nostro: stg-gw.orione.internal (progetto Orione), NON comunicarlo, gli diamo l'URL pubblico sandbox https://sandbox.example.com.
MD
