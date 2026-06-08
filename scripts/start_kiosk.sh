#!/usr/bin/env bash
# Launch Pi Dash in Chromium kiosk mode.
# Expects the backend to be running (or started separately via systemd).

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$SCRIPT_DIR/../frontend"
LAYOUT="${1:-tdi_discovery}"

# Hide cursor
unclutter -idle 0.5 -root &

chromium-browser \
  --kiosk \
  --noerrdialogs \
  --disable-infobars \
  --disable-session-crashed-bubble \
  --disable-restore-session-state \
  --disable-translate \
  --no-first-run \
  --fast \
  --fast-start \
  --disable-features=TranslateUI \
  --autoplay-policy=no-user-gesture-required \
  "file://${FRONTEND_DIR}/index.html?layout=configs/layouts/${LAYOUT}.json&ws=ws://127.0.0.1:8765"
