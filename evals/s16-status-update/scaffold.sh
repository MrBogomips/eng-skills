#!/usr/bin/env bash
set -euo pipefail
mkdir -p notes status
cat > notes/week-47.md <<'MD'
mon: finished the data migration dry run, 2 tables failed (encoding), fixed tue
tue: vendor said SSO certificate renewal needs their ops, maybe 2 weeks
wed: load test ok at 1.5x target. demo to finance went well, they asked for CSV export (not in scope)
thu: if SSO cert slips past 6 Dec go-live 9 Dec is not possible. options: a) postpone go-live to 16 Dec b) go live with local login for 1 week (security must accept). need steering decision by 2 Dec
fri: started cutover runbook, 60% done. Last week's status: on track.
MD
