"""
Run OUTSIDE KiCad.  Expands board from 65×56.5mm to 100×56.5mm and
adds mounting holes H5 (96.5, 3.5) and H6 (96.5, 53.0).
Reload PCB in KiCad after running (File > Revert).
"""

PCB = '/home/zach/Documents/pi-dash/hardware/pi-dash-input-hat/pi-dash-input-hat.kicad_pcb'

with open(PCB) as f:
    content = f.read()

# 1. Expand board outline
if '(end 65 56.5)' not in content:
    print("ERROR: expected board outline (end 65 56.5) not found. Already resized?")
else:
    content = content.replace('(end 65 56.5)', '(end 100 56.5)', 1)
    print("Board outline expanded to 100 × 56.5 mm")

# 2. New mounting holes
def mounting_hole(ref, x, y, n):
    return f"""
\t(footprint "MountingHole:MountingHole_2.7mm_M2.5"
\t\t(layer "F.Cu")
\t\t(uuid "b000000{n}-0000-0000-0000-000000000001")
\t\t(at {x} {y})
\t\t(property "Reference" "{ref}"
\t\t\t(at 0 -3.5 0)
\t\t\t(layer "F.SilkS")
\t\t\t(uuid "b000000{n}-0001-0000-0000-000000000001")
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1 1)
\t\t\t\t\t(thickness 0.15)
\t\t\t\t)
\t\t\t)
\t\t)
\t\t(property "Value" "MountingHole_2.7mm_M2.5"
\t\t\t(at 0 3.5 0)
\t\t\t(layer "F.Fab")
\t\t\t(hide yes)
\t\t\t(uuid "b000000{n}-0002-0000-0000-000000000001")
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1 1)
\t\t\t\t\t(thickness 0.15)
\t\t\t\t)
\t\t\t)
\t\t)
\t\t(attr through_hole)
\t\t(pad "" np_thru_hole circle
\t\t\t(at 0 0)
\t\t\t(size 2.7 2.7)
\t\t\t(drill 2.7)
\t\t\t(layers "*.Cu" "*.Mask")
\t\t\t(uuid "b000000{n}-0003-0000-0000-000000000001")
\t\t)
\t\t(embedded_fonts no)
\t)"""

insert_at = content.find('\n\t(gr_rect')
holes = mounting_hole('H5', 96.5, 3.5, 5) + mounting_hole('H6', 96.5, 53.0, 6)
content = content[:insert_at] + holes + content[insert_at:]
print("Added H5 (96.5, 3.5) and H6 (96.5, 53.0)")

with open(PCB, 'w') as f:
    f.write(content)
print("Done. File > Revert in KiCad to reload.")
