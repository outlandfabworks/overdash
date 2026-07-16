# Installation Guide

## Requirements

- Raspberry Pi 4 (2 GB RAM minimum) or Pi 5
- Raspberry Pi OS Lite (64-bit recommended)
- Python 3.11+
- CAN bus interface (e.g. PiCAN2, Waveshare CAN HAT) for J1939/CompuShift data
- USB-to-serial adapter or UART for K-line OBD-II
- Overdash Input HAT (optional) for GPIO warning light inputs

## ⚠️ Safety — Read First

Before you install, read [LEGAL.md](LEGAL.md) in full. Key points:

1. Retain your vehicle's original cluster as the primary instrument
2. Configure everything before driving — do not operate the touchscreen while moving
3. Check roadworthiness / inspection requirements in your country
4. Inform your insurer of the modification

## Quick Start

```bash
# Clone the repository
git clone https://github.com/outlandfabworks/overdash.git
cd overdash

# Create a virtual environment and install dependencies
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Copy and edit the vehicle config for your setup
cp configs/vehicles/tdi_discovery.yaml configs/vehicles/my_vehicle.yaml
# Edit my_vehicle.yaml to match your CAN interface, baud rate, serial ports, etc.

# Test with the mock vehicle source (no hardware required)
.venv/bin/python -m backend.main configs/vehicles/mock.yaml

# Open http://<pi-ip>:8080 in a browser
```

## Install as a System Service (Auto-start on Boot)

```bash
sudo bash scripts/install-service.sh
```

This installs a systemd service that:
- Starts Overdash automatically at boot
- Restarts it within 5 seconds if it crashes
- Logs to the system journal (`sudo journalctl -u overdash -f`)

## CAN Bus Setup (Raspberry Pi)

```bash
# Add to /etc/network/interfaces or use a .conf in /etc/network/interfaces.d/
auto can0
iface can0 inet manual
    pre-up ip link set can0 type can bitrate 250000
    up ip link set can0 up
    down ip link set can0 down
```

Or using a systemd-networkd `.link` file — see your CAN HAT documentation.

## Touchscreen Auto-Launch (Chromium Kiosk Mode)

Add to `/etc/xdg/lxsession/LXDE-pi/autostart`:

```
@chromium-browser --kiosk --disable-infobars --disable-session-crashed-bubble \
  --noerrdialogs http://localhost:8080
```

## Configuration

Vehicle configs live in `configs/vehicles/`. Layout configs live in
`configs/layouts/`. You can edit layouts visually using the in-browser editor
(click the pencil icon on the dashboard) or by editing the JSON directly.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Dashboard shows OFFLINE | Check that the backend service is running: `sudo systemctl status overdash` |
| Gauges show STALE | A data source (CAN, K-line, GPIO) has stopped responding — check wiring and `journalctl -u overdash` |
| CAN bus not working | Ensure `can0` is up: `ip link show can0` |
| Permission denied on serial port | Add your user to the `dialout` group: `sudo usermod -aG dialout pi` |
