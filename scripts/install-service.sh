#!/bin/bash
# Install and enable the Overdash systemd service.
# Run as: sudo bash scripts/install-service.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SERVICE_SRC="$SCRIPT_DIR/overdash.service"
SERVICE_DEST="/etc/systemd/system/overdash.service"

# Patch the WorkingDirectory and ExecStart with the actual install path
sed "s|/home/pi/overdash|$PROJECT_DIR|g" "$SERVICE_SRC" > "$SERVICE_DEST"

systemctl daemon-reload
systemctl enable overdash
systemctl start overdash

echo ""
echo "Overdash service installed and started."
echo "  Status:  sudo systemctl status overdash"
echo "  Logs:    sudo journalctl -u overdash -f"
echo "  Stop:    sudo systemctl stop overdash"
