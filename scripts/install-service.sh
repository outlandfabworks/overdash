#!/bin/bash
# Install and enable the Pi Dash systemd service.
# Run as: sudo bash scripts/install-service.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SERVICE_SRC="$SCRIPT_DIR/pi-dash.service"
SERVICE_DEST="/etc/systemd/system/pi-dash.service"

# Patch the WorkingDirectory and ExecStart with the actual install path
sed "s|/home/pi/pi-dash|$PROJECT_DIR|g" "$SERVICE_SRC" > "$SERVICE_DEST"

systemctl daemon-reload
systemctl enable pi-dash
systemctl start pi-dash

echo ""
echo "Pi Dash service installed and started."
echo "  Status:  sudo systemctl status pi-dash"
echo "  Logs:    sudo journalctl -u pi-dash -f"
echo "  Stop:    sudo systemctl stop pi-dash"
