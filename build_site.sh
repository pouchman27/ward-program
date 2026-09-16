#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
curl -fsSL -o /tmp/agendas.xlsx 'https://docs.google.com/spreadsheets/d/1fvw_Kyhy44Er_al2Ammw07KbXA39iBporF3bOF_B1aw/export?format=xlsx'
curl -fsSL -o /tmp/activities.xlsx 'https://docs.google.com/spreadsheets/d/1_6NKa_YWGWKSLCINSjZeAUrhwWAj4hBrWWF88O7Qj-I/export?format=xlsx'
python3 fetch_announcements.py
printf '%s' '9541feda7b84bf953efa2cf47305248ec3ca90d9673d8fa1baea79aa47012831' > .cal-token
WARD_SITE_PASSPHRASE="${WARD_SITE_PASSPHRASE:?required}" python3 generate.py /tmp/agendas.xlsx ./data.json
rm -f data.json cal_events.json
