"""
Adds a GND copper pour on F.Cu matching the existing B.Cu pour.
The existing GND vias from FreeRouting will stitch both pours together,
resolving the disconnected B.Cu zone sections.

Run from KiCad scripting console:
  exec(open('/home/zach/Documents/pi-dash/hardware/pi-dash-input-hat/add_fcu_gnd_pour.py').read())
"""
import pcbnew

BOARD_FILE = '/home/zach/Documents/pi-dash/hardware/pi-dash-input-hat/pi-dash-input-hat.kicad_pcb'

board = pcbnew.LoadBoard(BOARD_FILE)
gnd_net = board.FindNet('GND')

if not gnd_net:
    print("ERROR: GND net not found")
else:
    # Check if F.Cu GND zone already exists
    for zone in board.Zones():
        if zone.GetNet().GetNetname() == 'GND' and zone.GetLayer() == pcbnew.F_Cu:
            print("F.Cu GND zone already exists — nothing to do.")
            raise SystemExit

    zone = pcbnew.ZONE(board)
    zone.SetNet(gnd_net)
    zone.SetLayer(pcbnew.F_Cu)

    # Same outline as the B.Cu zone (full board)
    outline = zone.Outline()
    outline.NewOutline()
    for x_mm, y_mm in [(0, 0), (100.5, 0), (100.5, 56.5), (0, 56.5)]:
        outline.Append(pcbnew.FromMM(x_mm), pcbnew.FromMM(y_mm))

    # Match B.Cu zone parameters
    zone.SetMinThickness(pcbnew.FromMM(0.25))
    zone.SetLocalClearance(pcbnew.FromMM(0.5))
    zone.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)   # Solid — no thermal reliefs
    zone.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    zone.SetThermalReliefGap(pcbnew.FromMM(0.5))
    zone.SetThermalReliefCopperBridge(pcbnew.FromMM(0.5))
    zone.SetFillMode(pcbnew.ZONE_FILL_MODE_SOLID)

    board.Add(zone)
    board.Save(BOARD_FILE)
    print("Done — F.Cu GND pour added.")
    print("1. Close and reopen the board file")
    print("2. Press B to fill all zones")
    print("3. Run DRC")
