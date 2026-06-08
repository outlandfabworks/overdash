"""
Fix the 3 malformed global_label blocks added by update_schematic_power.py.
Changes:
  - (shape passive) → (shape bidirectional)
  - removes (pin "~" ...) sub-element
  - adds (fields_autoplaced yes) after (at ...)
  - adds (property "Intersheetrefs" ...) after (uuid ...)
Run OUTSIDE KiCad, then File > Revert.
"""
import re

SCH = '/home/zach/Documents/pi-dash/hardware/pi-dash-input-hat/pi-dash-input-hat.kicad_sch'

with open(SCH) as f:
    content = f.read()

# Pattern matches each bad global_label block (those with "shape passive" + pin "~")
# We only fix blocks that have the bad (pin "~") element.
pattern = re.compile(
    r'\(global_label "([^"]+)"\n'
    r'\t\(shape passive\)\n'
    r'\t\(at ([^\)]+)\)\n'
    r'\t\(effects\n\t\t\(font\n\t\t\t\(size 1\.27 1\.27\)\n\t\t\)\n\t\)\n'
    r'\t\(uuid "([^"]+)"\)\n'
    r'\t\(pin "~"\n\t\t\(uuid "[^"]+"\)\n\t\)\n'
    r'\)'
)

def replacement(m):
    name = m.group(1)
    at_args = m.group(2)   # e.g. "110 222 270"
    uuid_val = m.group(3)
    # Extract x y from at_args for the Intersheetrefs property
    parts = at_args.split()
    px, py = parts[0], parts[1]
    angle = parts[2] if len(parts) > 2 else '0'
    return (
        f'(global_label "{name}"\n'
        f'\t(shape bidirectional)\n'
        f'\t(at {at_args})\n'
        f'\t(fields_autoplaced yes)\n'
        f'\t(effects\n\t\t(font\n\t\t\t(size 1.27 1.27)\n\t\t)\n\t)\n'
        f'\t(uuid "{uuid_val}")\n'
        f'\t(property "Intersheetrefs" "${{INTERSHEET_REFS}}"\n'
        f'\t\t(at {px} {py} {angle})\n'
        f'\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n'
        f'\t\t\t(hide yes)\n\t\t)\n\t)\n'
        f')'
    )

new_content, count = pattern.subn(replacement, content)
print(f"Fixed {count} global_label block(s).")

with open(SCH, 'w') as f:
    f.write(new_content)
print("Done. File > Revert in KiCad to reload.")
