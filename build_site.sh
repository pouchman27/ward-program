#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
python3 fetch_announcements.py
printf '%s' '9541feda7b84bf953efa2cf47305248ec3ca90d9673d8fa1baea79aa47012831' > .cal-token
python3 generate.py ./data.json
rm -f data.json cal_events.json
