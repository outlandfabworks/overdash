"""
Removes the 4 bad stitching vias that landed on signal traces / component pads.
Keeps the 4 clean ones at (67,42), (78,42), (90,14), (90,42).

Run from KiCad scripting console:
  exec(open('/home/zach/Documents/pi-dash/hardware/pi-dash-input-hat/remove_bad_vias2.py').read())
"""
import pcbnew

BOARD_FILE = '/home/zach/Documents/pi-dash/hardware/pi-dash-input-hat/pi-dash-input-hat.kicad_pcb'

board = pcbnew.LoadBoard(BOARD_FILE)

REMOVE = {(63.0, 14.0), (78.0, 14.0), (93.0, 28.0), (67.0, 28.0)}

removed = 0
for track in list(board.GetTracks()):
    x = round(track.GetX() / 1e6, 1)
    y = round(track.GetY() / 1e6, 1)
    if (x, y) in REMOVE:
        board.Remove(track)
        print(f"  Removed via at ({x}, {y})")
        removed += 1

board.Save(BOARD_FILE)
print(f"\nRemoved {removed} bad vias. Close/reopen, press B, run DRC.")
