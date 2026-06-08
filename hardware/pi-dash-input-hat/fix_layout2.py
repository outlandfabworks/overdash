"""
KiPython fix script 2.
1. J2: rotation 90° (stored 90 = pins go LEFT, all within board)
2. Q1: move to x=90 (F1 pad1 is at x=79, pad2 at x=86.62 — need Q1 clear of that)
3. Redistribute L1/D18/C1/C2/D19/R25 to avoid overlap with Q1's new position
4. Clears all routes

exec(open('/home/zach/Documents/pi-dash/hardware/pi-dash-input-hat/fix_layout2.py').read())
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
    print(f"  {ref} -> ({x_mm}, {y_mm})" + (f" @ {angle}" if angle is not None else ""))

# J2: the footprint's long axis is along local -Y.
# Stored -90 -> formula Gx = cx - Ly -> pins go RIGHT (off board).
# Stored +90 -> formula Gx = cx + Ly -> pins go LEFT (x=10..58, within board).
print("Fixing J2 rotation...")
move('J2', 58.42, 11.43, 90)

# Q1 (SOT-23): move right so it clears F1's pad2 at x=86.62mm
# pad3 (drain) will be at ~90.94mm — 4.3mm clear of F1 pad2
print("Spreading power rail components...")
move('Q1',  90, 25)

# L1 was at (90,25) — now occupied by Q1. Move to bottom row.
move('L1',  82, 47)

# C1 moves to be directly under Q1 (same VIN_BUCK node, short trace)
move('C1',  90, 39)

# D18 freewheeling Schottky: move near L1 output end
move('D18', 73, 49, 270)

# C2 output cap: near L1 pin2 (+5V)
move('C2',  94, 49)

# D19 LED + R25 resistor
move('D19', 94, 43)
move('R25', 94, 37)

print("Deleting all routed tracks and vias...")
tracks = list(board.GetTracks())
for t in tracks:
    board.Remove(t)
print(f"  Removed {len(tracks)} tracks/vias.")

board.Save(board.GetFileName())
pcbnew.Refresh()
print("Done. Now run assign_nets.py, then File > Revert, then export DSN for FreeRouting.")
