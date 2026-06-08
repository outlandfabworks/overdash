# Legal Notice & Safety Information

## ⚠️ Safety Warning — Read Before Use

Pi Dash is an **informational display only**. It does not control, modify, or
replace any vehicle safety system.

- **Do not interact with this display while driving.** Configure the layout
  and settings before driving. Operating any touchscreen while the vehicle is
  in motion is dangerous and may be illegal in your jurisdiction.
- The accuracy of displayed data depends entirely on your vehicle's sensors and
  wiring. Pi Dash does not validate the correctness of any signal.
- **Stale or incorrect data may be displayed** if a hardware source disconnects
  or malfunctions. Never make driving decisions based solely on this display.
- This software is provided for personal use, off-road use, and track use.
  Always retain your vehicle's original instrument cluster as the primary
  source of safety information.

## No Warranty

This software is provided "as is" without warranty of any kind. The authors
and contributors are not liable for any damage to your vehicle, data loss,
injury, or legal consequences arising from installation or use of this software.

## Vehicle Modification & Roadworthiness

Installing this software involves connecting hardware to your vehicle's
electrical and diagnostic systems. This may:

- Affect your vehicle's roadworthiness certificate (MOT in the UK, TÜV in
  Germany, inspection in the US, roadworthy certificate in Australia, etc.)
- Void your vehicle manufacturer warranty
- Have implications for your vehicle insurance — **inform your insurer**
- Affect compliance with emissions regulations if the OBD-II port is in use

**It is your responsibility** to ensure your installation complies with all
applicable local laws and regulations. Consult a qualified automotive
technician if you are unsure.

## FCC / CE Notice (Hardware)

If you use a Pi Dash input HAT or any associated hardware:
- Ensure the hardware carries appropriate certification for your region
  (FCC ID for the US, CE marking for the EU, IC for Canada, etc.)
- Uncertified electronic devices may not legally be sold or used in some
  jurisdictions

## Third-Party Licenses

This project uses the following third-party software:

| Package | License | Notes |
|---------|---------|-------|
| python-can | LGPL-3.0 | CAN bus interface |
| aiohttp | Apache-2.0 | HTTP server |
| websockets | BSD-3-Clause | WebSocket server |
| pyserial | BSD-3-Clause | Serial/K-line communication |
| pyyaml | MIT | Config file parsing |
| pyserial-asyncio | BSD-3-Clause | Async serial |

`python-can` is licensed under LGPL-3.0. Under the terms of the LGPL, any
modifications to `python-can` itself must be made available under LGPL-3.0.
Pi Dash itself is licensed under the MIT License.

Full license texts for all dependencies can be found in your Python virtual
environment under `.venv/lib/pythonX.X/site-packages/`.
