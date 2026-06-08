"""
KiPython fix script.
1. Rotates J2 from +90° to -90° (pins now extend LEFT, all within board)
2. Spreads J3/F1/Q1 to fix clearance and short violations
3. Clears all existing routes (must re-run FreeRouting after)

exec(open('/home/zach/Documents/pi-dash/hardware/pi-dash-input-hat/fix_layout.py').read())
"""
import pcbnew

board = pcbnew.GetBoard()

def move(ref, x_mm, y_mm, angle=None):
    fp = board.FindFootprintByReference(ref)
    if not fp:
        print(f"Not found: {ref}"); return
    fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x_mm), pcbnew.FromMM(y_mm)))
    if angle is not None:
        fp.SetOrientationDegrees(angle)
    print(f"  {ref} → ({x_mm}, {y_mm})" + (f" @ {angle}°" if angle is not None else ""))

print("Fixing J2 rotation...")
move('J2', 58.42, 11.43, -90)   # was +90, pins were going RIGHT off the board

print("Fixing power section spacing (J3/F1/Q1)...")
# J3 stays at x=69 — it's the input connector
# F1: was at x=76 (too close to J3 and Q1), move to x=79
# Q1: was at x=82 (too close to F1), move to x=85
# C1 and D17 follow
move('F1',  79, 25)
move('Q1',  85, 25)
move('D17', 79, 39, 270)    # TVS stays below F1
move('C1',  85, 39)         # bulk cap below Q1

print("Deleting all routed tracks and vias...")
tracks = list(board.GetTracks())
for t in tracks:
    board.Remove(t)
print(f"  Removed {len(tracks)} tracks/vias.")

board.Save(board.GetFileName())
pcbnew.Refresh()
print("Done. Now re-run assign_nets.py, then File > Revert, then export DSN for FreeRouting.")
