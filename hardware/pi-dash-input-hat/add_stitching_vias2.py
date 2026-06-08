"""
Adds GND stitching vias to bridge F.Cu and B.Cu GND zone sections.
Targets the right-side open area, avoiding known signal trace locations.

Run from KiCad scripting console:
  exec(open('/home/zach/Documents/pi-dash/hardware/pi-dash-input-hat/add_stitching_vias2.py').read())
"""
import pcbnew

BOARD_FILE = '/home/zach/Documents/pi-dash/hardware/pi-dash-input-hat/pi-dash-input-hat.kicad_pcb'

board = pcbnew.LoadBoard(BOARD_FILE)
gnd_net = board.FindNet('GND')

# Positions chosen to avoid: y≈20 (+3V3 traces), x=55 (signal traces),
# x≈74 y≈46 (J3 area), x≈88 y≈29 (U9 area)
via_positions = [
    (67.0, 28.0),
    (67.0, 42.0),
    (78.0, 14.0),
    (78.0, 42.0),
    (90.0, 14.0),
    (90.0, 42.0),
    (63.0, 14.0),
    (93.0, 28.0),
]

# Skip positions where a via already exists (within 1mm)
existing = set()
for track in board.GetTracks():
    x = round(track.GetX() / 1e6, 0)
    y = round(track.GetY() / 1e6, 0)
    existing.add((x, y))

added = 0
for x_mm, y_mm in via_positions:
    key = (round(x_mm, 0), round(y_mm, 0))
    if key in existing:
        print(f"  Skipped ({x_mm}, {y_mm}) — via already there")
        continue
    via = pcbnew.PCB_VIA(board)
    via.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x_mm), pcbnew.FromMM(y_mm)))
    via.SetWidth(pcbnew.FromMM(0.8))
    via.SetDrill(pcbnew.FromMM(0.4))
    via.SetNet(gnd_net)
    via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    board.Add(via)
    print(f"  Via added at ({x_mm}, {y_mm})")
    added += 1

board.Save(BOARD_FILE)
print(f"\nDone — {added} stitching vias added.")
print("Close and reopen the board, press B, then run DRC.")
