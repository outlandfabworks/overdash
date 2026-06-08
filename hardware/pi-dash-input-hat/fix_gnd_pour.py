"""
1. Removes the stitching vias added by add_stitching_vias.py
2. Adds a GND copper pour on F.Cu

Run from KiCad scripting console:
  exec(open('/home/zach/Documents/pi-dash/hardware/pi-dash-input-hat/fix_gnd_pour.py').read())
"""
import pcbnew

BOARD_FILE = '/home/zach/Documents/pi-dash/hardware/pi-dash-input-hat/pi-dash-input-hat.kicad_pcb'

board = pcbnew.LoadBoard(BOARD_FILE)
gnd_net = board.FindNet('GND')

# ── Remove bad stitching vias ─────────────────────────────────────────────────
BAD_VIA_POSITIONS = {
    (65.0, 20.0), (65.0, 35.0), (65.0, 48.0),
    (75.0, 20.0), (75.0, 35.0), (75.0, 48.0),
    (85.0, 20.0), (85.0, 35.0), (85.0, 48.0),
    (55.0, 35.0), (55.0, 48.0),
}

removed = 0
for track in list(board.GetTracks()):
    if isinstance(track, pcbnew.PCB_VIA):
        x = round(track.GetX() / 1e6, 1)
        y = round(track.GetY() / 1e6, 1)
        if (x, y) in BAD_VIA_POSITIONS:
            board.Remove(track)
            print(f"  Removed via at ({x}, {y})")
            removed += 1

print(f"Removed {removed} bad vias.")

# ── Add F.Cu GND pour ─────────────────────────────────────────────────────────
for zone in board.Zones():
    if zone.GetNet().GetNetname() == 'GND' and zone.GetLayer() == pcbnew.F_Cu:
        print("F.Cu GND zone already exists — skipping.")
        break
else:
    zone = pcbnew.ZONE(board)
    zone.SetNet(gnd_net)
    zone.SetLayer(pcbnew.F_Cu)

    outline = zone.Outline()
    outline.NewOutline()
    for x_mm, y_mm in [(0, 0), (100.5, 0), (100.5, 56.5), (0, 56.5)]:
        outline.Append(pcbnew.FromMM(x_mm), pcbnew.FromMM(y_mm))

    zone.SetMinThickness(pcbnew.FromMM(0.25))
    zone.SetLocalClearance(pcbnew.FromMM(0.5))
    zone.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    zone.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    zone.SetThermalReliefGap(pcbnew.FromMM(0.5))
    zone.SetThermalReliefSpokeWidth(pcbnew.FromMM(0.5))

    board.Add(zone)
    print("F.Cu GND pour added.")

board.Save(BOARD_FILE)
print("\nDone. Close and reopen the board, press B, then run DRC.")
