"""
Fix J1 Molex Micro-Fit 3.0 pads: 3.6mm (oversized, overlapping) → 1.8mm oval, 1.0mm drill.
Run from terminal: python3 fix_j1_pads.py
"""
import re
from pathlib import Path

PCB = Path(__file__).parent / "pi-dash-input-hat.kicad_pcb"

text = PCB.read_text()

# Find J1 footprint block
j1_start = text.find('(uuid "c0000002-0000-0000-0000-000000000001")')
if j1_start == -1:
    print("J1 UUID not found — searching by reference")
    j1_start = text.find('"J1"')
    if j1_start == -1:
        print("ERROR: J1 not found in PCB file")
        exit(1)

# Find the enclosing footprint block start (scan back for the '(footprint' keyword)
block_start = text.rfind('\t(footprint', 0, j1_start)
if block_start == -1:
    print("ERROR: could not locate J1 footprint block start")
    exit(1)

# Find block end by tracking parenthesis depth
depth = 0
i = block_start
while i < len(text):
    if text[i] == '(':
        depth += 1
    elif text[i] == ')':
        depth -= 1
        if depth == 0:
            block_end = i
            break
    i += 1

j1_block = text[block_start:block_end + 1]

# Replace oversized pads: (size 3.6 3.6) / (drill 1.8) → (size 1.8 1.8) / (drill 1.0)
fixed = j1_block.replace('(size 3.6 3.6)', '(size 1.8 1.8)')
fixed = fixed.replace('(drill 1.8)', '(drill 1.0)')

if fixed == j1_block:
    print("No 3.6mm pads found in J1 block — already fixed?")
else:
    count = j1_block.count('(size 3.6 3.6)')
    text = text[:block_start] + fixed + text[block_end + 1:]
    PCB.write_text(text)
    print(f"Fixed {count} J1 pads: 3.6mm → 1.8mm, drill 1.8 → 1.0mm")
    print("Gap between adjacent pads now: 3.0 - 1.8 = 1.2mm (was -0.6mm overlap)")
