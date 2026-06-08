"""
Reports the location of each disconnected GND zone section on F.Cu and B.Cu.

Run from KiCad scripting console:
  exec(open('/home/zach/Documents/pi-dash/hardware/pi-dash-input-hat/find_gnd_sections.py').read())
"""
import pcbnew

BOARD_FILE = '/home/zach/Documents/pi-dash/hardware/pi-dash-input-hat/pi-dash-input-hat.kicad_pcb'
board = pcbnew.LoadBoard(BOARD_FILE)

for zone in board.Zones():
    if zone.GetNet().GetNetname() != 'GND':
        continue
    layer = zone.GetLayerName()
    layer_id = zone.GetLayer()
    filled = zone.GetFilledPolysList(layer_id)
    if not filled:
        print(f"{layer}: no fill data (press B first)")
        continue
    count = filled.OutlineCount()
    print(f"\n{layer} GND zone — {count} section(s):")
    for i in range(count):
        outline = filled.Outline(i)
        pts = [outline.CPoint(j) for j in range(outline.PointCount())]
        xs = [p.x / 1e6 for p in pts]
        ys = [p.y / 1e6 for p in pts]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        cx = (min_x + max_x) / 2
        cy = (min_y + max_y) / 2
        area = (max_x - min_x) * (max_y - min_y)
        print(f"  [{i}] centroid ({cx:.1f}, {cy:.1f})  "
              f"bbox ({min_x:.1f},{min_y:.1f})→({max_x:.1f},{max_y:.1f})  "
              f"approx area {area:.0f} mm²")
