"""
Run OUTSIDE KiCad (close or save first, then reload after).
Adds the 39 missing pads to J2 in the PCB file.
J2 is at (58.42, 11.43, -90°). Local layout:
  odd pins (col A): local x=0, y=0,-2.54,-5.08,...  → board x decreasing, board y=11.43
  even pins (col B): local x=2.54, same y values    → board y=8.89
"""
import re, uuid

PCB = '/home/zach/Documents/pi-dash/hardware/pi-dash-input-hat/pi-dash-input-hat.kicad_pcb'

with open(PCB) as f:
    content = f.read()

# Locate J2 footprint block
j2_ref = content.find('"J2"')
fp_start = content.rfind('\n\t(footprint', 0, j2_ref)

# Find insertion point: just before (embedded_fonts ...) line inside J2 footprint
insert_at = content.find('\n\t\t(embedded_fonts', fp_start)
if insert_at == -1:
    # fallback: before the closing paren of the footprint
    depth, pos = 0, fp_start
    for i, c in enumerate(content[fp_start:], fp_start):
        if c == '(': depth += 1
        elif c == ')':
            depth -= 1
            if depth == 0:
                insert_at = i
                break

def pad_text(num, lx, ly):
    uid = str(uuid.uuid4())
    shape = 'rect' if num == 1 else 'circle'
    size = '2.54 2.54' if num == 1 else '1.7 1.7'
    return (
        f'\t\t(pad "{num}" thru_hole {shape}\n'
        f'\t\t\t(at {lx:.4f} {ly:.4f})\n'
        f'\t\t\t(size {size})\n'
        f'\t\t\t(drill 1.1)\n'
        f'\t\t\t(layers "*.Cu" "*.Mask")\n'
        f'\t\t\t(remove_unused_layers no)\n'
        f'\t\t\t(uuid "{uid}")\n'
        f'\t\t)'
    )

# Collect existing pad numbers from J2 block only
depth, pos = 0, fp_start
fp_end = fp_start
for i, c in enumerate(content[fp_start:], fp_start):
    if c == '(': depth += 1
    elif c == ')':
        depth -= 1
        if depth == 0:
            fp_end = i
            break

j2_block = content[fp_start:fp_end + 1]
existing_pads = set(re.findall(r'\(pad "(\d+)"', j2_block))
print(f"Existing J2 pads: {sorted(existing_pads, key=int)}")

new_pad_lines = []
for row in range(1, 21):          # 20 rows
    ly = -(row - 1) * 2.54
    for lx, col_offset in [(0.0, 0), (2.54, 1)]:
        pin = (row - 1) * 2 + col_offset + 1   # 1..40
        if str(pin) in existing_pads:
            continue
        new_pad_lines.append(pad_text(pin, lx, ly))

if not new_pad_lines:
    print("No pads to add.")
else:
    insert_str = '\n' + '\n'.join(new_pad_lines) + '\n'
    new_content = content[:insert_at] + insert_str + content[insert_at:]
    with open(PCB, 'w') as f:
        f.write(new_content)
    print(f"Added {len(new_pad_lines)} pads to J2. Reload the PCB in KiCad, then run assign_nets.py.")
