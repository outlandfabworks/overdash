"""
KiPython script — bypasses KiCad's built-in SES importer.
Parses the FreeRouting SES file and adds track segments directly
using the pcbnew API.

exec(open('/home/zach/Documents/pi-dash/hardware/pi-dash-input-hat/import_ses.py').read())
"""
import pcbnew, re

SES = '/home/zach/Documents/pi-dash/hardware/pi-dash-input-hat/pi-dash-input-hat.ses'
BOARD_FILE = '/home/zach/Documents/pi-dash/hardware/pi-dash-input-hat/pi-dash-input-hat.kicad_pcb'
board = pcbnew.LoadBoard(BOARD_FILE)

# SES uses (resolution um 10) → 1 unit = 0.1 um = 0.0001 mm
SCALE = 0.0001  # mm per SES unit

layer_map = {'F.Cu': pcbnew.F_Cu, 'B.Cu': pcbnew.B_Cu}

with open(SES) as f:
    content = f.read()

# Find the network_out section
routes_start = content.find('(network_out')
if routes_start == -1:
    print("ERROR: no network_out section found")
    raise SystemExit

routes_text = content[routes_start:]

# Extract all wire paths: (path LAYER WIDTH x1 y1 x2 y2 ...)
wire_pat = re.compile(
    r'\(path\s+(\S+)\s+(\d+)\s+((?:[-\d]+\s+[-\d]+\s*)+)\)'
)

segments_added = 0
skipped = 0

for m in wire_pat.finditer(routes_text):
    layer_name = m.group(1)
    width_units = int(m.group(2))
    coords_str = m.group(3).strip()

    if layer_name not in layer_map:
        skipped += 1
        continue

    layer = layer_map[layer_name]
    width_nm = int(width_units * SCALE * 1e6)  # mm → nm (pcbnew internal)

    nums = list(map(int, coords_str.split()))
    points = [(nums[i] * SCALE, -nums[i+1] * SCALE) for i in range(0, len(nums)-1, 2)]
    # SES y is negated relative to KiCad (KiCad y increases downward)

    for i in range(len(points) - 1):
        x1, y1 = points[i]
        x2, y2 = points[i+1]
        if x1 == x2 and y1 == y2:
            continue
        seg = pcbnew.PCB_TRACK(board)
        seg.SetLayer(layer)
        seg.SetWidth(width_nm)
        seg.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(x1), pcbnew.FromMM(y1)))
        seg.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(x2), pcbnew.FromMM(y2)))
        board.Add(seg)
        segments_added += 1

# Also import vias
via_pat = re.compile(
    r'\(via\s+\S+\s+([-\d]+)\s+([-\d]+)\)'
)
vias_added = 0
for m in via_pat.finditer(routes_text):
    x = int(m.group(1)) * SCALE
    y = -int(m.group(2)) * SCALE
    via = pcbnew.PCB_VIA(board)
    via.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
    via.SetWidth(pcbnew.FromMM(0.8))
    via.SetDrill(pcbnew.FromMM(0.4))
    board.Add(via)
    vias_added += 1

board.Save(BOARD_FILE)
print(f"Done: {segments_added} track segments, {vias_added} vias added.")
print(f"Skipped {skipped} paths on unknown layers.")
