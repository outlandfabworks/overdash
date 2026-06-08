"""
Removes duplicate F.Cu GND zones (keeps only the first one).
Run from KiCad scripting console:
  exec(open('/home/zach/Documents/pi-dash/hardware/pi-dash-input-hat/cleanup_zones.py').read())
"""
import pcbnew

BOARD_FILE = '/home/zach/Documents/pi-dash/hardware/pi-dash-input-hat/pi-dash-input-hat.kicad_pcb'
board = pcbnew.LoadBoard(BOARD_FILE)

fcu_gnd_zones = []
bcu_gnd_zones = []

for zone in board.Zones():
    net_name = zone.GetNet().GetNetname()
    layer = zone.GetLayer()
    if net_name == 'GND':
        if layer == pcbnew.F_Cu:
            fcu_gnd_zones.append(zone)
        elif layer == pcbnew.B_Cu:
            bcu_gnd_zones.append(zone)

print(f"Found {len(fcu_gnd_zones)} F.Cu GND zone(s)")
print(f"Found {len(bcu_gnd_zones)} B.Cu GND zone(s)")

# Remove duplicate F.Cu zones — keep first, delete rest
for zone in fcu_gnd_zones[1:]:
    board.Remove(zone)
    print("  Removed duplicate F.Cu GND zone")

board.Save(BOARD_FILE)
print("\nDone. Close/reopen, press B, run DRC.")
