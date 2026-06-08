"""
Adds GND stitching vias to reconnect isolated B.Cu GND zone sections.
Targets the disconnected void in the center-right area of the board.

Run from KiCad scripting console:
  exec(open('/home/zach/Documents/pi-dash/hardware/pi-dash-input-hat/add_stitching_vias.py').read())
"""
import pcbnew

BOARD_FILE = '/home/zach/Documents/pi-dash/hardware/pi-dash-input-hat/pi-dash-input-hat.kicad_pcb'

board = pcbnew.LoadBoard(BOARD_FILE)
gnd_net = board.FindNet('GND')

if not gnd_net:
    print("ERROR: GND net not found")
else:
    # Via locations (mm) targeting the disconnected center-right void
    # and the right-side open areas around U9/J4
    via_positions = [
        (65.0, 20.0),   # center strip, upper band
        (65.0, 35.0),   # center strip, mid
        (65.0, 48.0),   # center strip, lower
        (75.0, 20.0),   # right area, upper
        (75.0, 35.0),   # right area, mid
        (75.0, 48.0),   # right area, lower
        (85.0, 20.0),   # far right, upper
        (85.0, 35.0),   # far right, mid
        (85.0, 48.0),   # far right, lower
        (55.0, 35.0),   # left edge of void
        (55.0, 48.0),   # left edge of void, lower
    ]

    added = 0
    for x_mm, y_mm in via_positions:
        via = pcbnew.PCB_VIA(board)
        via.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x_mm), pcbnew.FromMM(y_mm)))
        via.SetWidth(pcbnew.FromMM(0.8))    # 0.8mm via diameter
        via.SetDrill(pcbnew.FromMM(0.4))    # 0.4mm drill — PCBWay standard
        via.SetNet(gnd_net)
        via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        board.Add(via)
        print(f"  Via added at ({x_mm}, {y_mm}) on GND")
        added += 1

    board.Save(BOARD_FILE)
    print(f"\nDone — {added} stitching vias added.")
    print("Press B to refill zones, then rerun DRC.")
