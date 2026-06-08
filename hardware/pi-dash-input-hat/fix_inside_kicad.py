"""
Run INSIDE the KiCad PCB scripting console:
    exec(open('/home/zach/Documents/pi-dash/hardware/pi-dash-input-hat/fix_inside_kicad.py').read())
"""
import pcbnew, os

board = pcbnew.GetBoard()

# Find the Resistor_SMD library inside the KiCad snap
SNAP_BASE = '/snap/kicad/current/usr/share/kicad/footprints'
SMD_LIB   = os.path.join(SNAP_BASE, 'Resistor_SMD.pretty')

if not os.path.isdir(SMD_LIB):
    print("ERROR: SMD library not found at", SMD_LIB)
else:
    print("Library found:", SMD_LIB)

# --- Replace R1-R24 with R_0805_2012Metric ---
to_remove, to_add = [], []

for fp in list(board.GetFootprints()):
    ref = fp.GetReference()
    if not (ref.startswith('R') and ref[1:].isdigit() and 1 <= int(ref[1:]) <= 24):
        continue

    new_fp = pcbnew.FootprintLoad(SMD_LIB, 'R_0805_2012Metric')
    if not new_fp:
        print(f"  SKIP {ref}: FootprintLoad returned None")
        continue

    new_fp.SetReference(ref)
    new_fp.SetValue(fp.GetValue())
    new_fp.SetPosition(fp.GetPosition())
    new_fp.SetOrientation(fp.GetOrientation())
    new_fp.SetPath(fp.GetPath())

    old_pads = {p.GetNumber(): p for p in fp.Pads()}
    for new_pad in new_fp.Pads():
        old = old_pads.get(new_pad.GetNumber())
        if old:
            new_pad.SetNet(old.GetNet())

    to_remove.append(fp)
    to_add.append(new_fp)
    print(f"  Prepared {ref}")

for old in to_remove:
    board.Remove(old)
for new in to_add:
    board.Add(new)

print(f"Replaced {len(to_add)} resistors with R_0805_2012Metric")

# --- Fix J1 pad sizes: 3.6 mm -> 1.8 mm ---
j1 = board.FindFootprintByReference('J1')
if j1:
    n = 0
    for pad in j1.Pads():
        pad.SetSize(pcbnew.VECTOR2I(pcbnew.FromMM(1.8), pcbnew.FromMM(1.8)))
        pad.SetDrillSize(pcbnew.VECTOR2I(pcbnew.FromMM(1.0), pcbnew.FromMM(1.0)))
        n += 1
    print(f"Fixed {n} J1 pads: 3.6 mm -> 1.8 mm")
else:
    print("WARNING: J1 not found")

pcbnew.Refresh()
board.Save(board.GetFileName())
print("Done — saved. Now run place_components.py, then DRC.")
