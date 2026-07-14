#!/usr/bin/env bash
# Overdash — Raspberry Pi setup script
# Tested on Raspberry Pi OS (Bullseye/Bookworm), 64-bit
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR/.."

echo "==> Installing system packages"
sudo apt-get update -qq
sudo apt-get install -y \
  python3-pip python3-venv \
  can-utils \                     # ip link / candump / cansend
  chromium-browser \
  unclutter \                     # hide cursor in kiosk mode
  xinit x11-xserver-utils \
  openbox                         # minimal WM for X

echo "==> Enabling UART for K-line (disables serial console)"
# Append to /boot/config.txt if not already present
grep -q "^enable_uart=1" /boot/config.txt \
  || echo "enable_uart=1" | sudo tee -a /boot/config.txt
sudo systemctl disable --now serial-getty@ttyAMA0.service 2>/dev/null || true
sudo raspi-config nonint do_serial 2  # disable console, keep hardware UART

echo "==> Loading CAN modules at boot"
grep -q "^can$" /etc/modules || echo "can" | sudo tee -a /etc/modules
grep -q "^can_raw$" /etc/modules || echo "can_raw" | sudo tee -a /etc/modules
grep -q "^mcp251x$" /etc/modules || echo "mcp251x" | sudo tee -a /etc/modules

echo "==> CAN interface config  (edit /etc/network/interfaces.d/can0 for your hat)"
sudo tee /etc/network/interfaces.d/can0 > /dev/null <<'EOF'
allow-hotplug can0
iface can0 inet manual
    pre-up /sbin/ip link set can0 type can bitrate 250000 restart-ms 100
    up /sbin/ip link set can0 up
    down /sbin/ip link set can0 down
EOF

echo "==> Creating Python virtualenv"
python3 -m venv "$PROJECT_DIR/.venv"
"$PROJECT_DIR/.venv/bin/pip" install --upgrade pip
"$PROJECT_DIR/.venv/bin/pip" install -r "$PROJECT_DIR/requirements.txt"

echo "==> Installing systemd service: overdash-backend"
sudo tee /etc/systemd/system/overdash-backend.service > /dev/null <<EOF
[Unit]
Description=Overdash Backend
After=network.target

[Service]
ExecStart=$PROJECT_DIR/.venv/bin/python -m backend.main configs/vehicles/tdi_discovery.yaml
WorkingDirectory=$PROJECT_DIR
Restart=on-failure
RestartSec=5
User=$(whoami)

[Install]
WantedBy=multi-user.target
EOF

echo "==> Installing systemd service: overdash-kiosk"
sudo tee /etc/systemd/system/overdash-kiosk.service > /dev/null <<EOF
[Unit]
Description=Overdash Kiosk (Chromium)
After=overdash-backend.service graphical.target
Requires=overdash-backend.service

[Service]
Environment=DISPLAY=:0
ExecStart=$PROJECT_DIR/scripts/start_kiosk.sh
Restart=on-failure
RestartSec=5
User=$(whoami)

[Install]
WantedBy=graphical.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable overdash-backend overdash-kiosk

echo ""
echo "Done. Reboot to start automatically, or run:"
echo "  sudo systemctl start overdash-backend"
echo "  sudo systemctl start overdash-kiosk"
