"""
Replace R1-R24 THT axial footprints with Resistor_SMD:R_0805_2012Metric in the PCB file.
Run from the terminal: python3 fix_resistor_footprints.py
"""
import re
import shutil
from pathlib import Path

PCB = Path(__file__).parent / "pi-dash-input-hat.kicad_pcb"
BACKUP = PCB.with_suffix(".kicad_pcb.bak")

THT_NAME = "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal"

def find_block(text, start):
    """Return (start_of_open_paren, end_inclusive) for the S-expr block at start."""
    depth = 0
    i = start
    while i < len(text):
        if text[i] == '(':
            depth += 1
        elif text[i] == ')':
            depth -= 1
            if depth == 0:
                return (start, i)
        i += 1
    raise ValueError(f"Unclosed block starting at {start}")

def extract(pattern, text, group=1, default=None):
    m = re.search(pattern, text, re.DOTALL)
    return m.group(group) if m else default

def make_0805_block(at_x, at_y, at_rot, ref, value,
                    fp_uuid, ref_uuid, val_uuid, ds_uuid, desc_uuid,
                    path, sheetname, sheetfile,
                    net1_id, net1_name, net2_id, net2_name,
                    pad1_uuid, pad2_uuid):
    rot_str = f" {at_rot}" if at_rot != "0" else ""
    # Property offsets rotate with the footprint
    r = at_rot

    def prop_uuid_block(uuid_val):
        if uuid_val:
            return f"\n\t\t\t(uuid \"{uuid_val}\")"
        return ""

    block = f"""\t(footprint "Resistor_SMD:R_0805_2012Metric"
\t\t(layer "F.Cu")
\t\t(uuid "{fp_uuid}")
\t\t(at {at_x} {at_y}{rot_str})
\t\t(descr "Resistor SMD 0805 (2012 Metric), square (rectangular) end terminal, IPC-7351 nominal")
\t\t(tags "resistor")
\t\t(property "Reference" "{ref}"
\t\t\t(at 0 -1.65 {r}){prop_uuid_block(ref_uuid)}
\t\t\t(layer "F.SilkS")
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1 1)
\t\t\t\t\t(thickness 0.15)
\t\t\t\t)
\t\t\t)
\t\t)
\t\t(property "Value" "{value}"
\t\t\t(at 0 1.65 {r}){prop_uuid_block(val_uuid)}
\t\t\t(layer "F.Fab")
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1 1)
\t\t\t\t\t(thickness 0.15)
\t\t\t\t)
\t\t\t)
\t\t)
\t\t(property "Datasheet" "~"
\t\t\t(at 0 0 {r}){prop_uuid_block(ds_uuid)}
\t\t\t(layer "F.Fab")
\t\t\t(hide yes)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t\t(thickness 0.15)
\t\t\t\t)
\t\t\t)
\t\t)
\t\t(property "Description" ""
\t\t\t(at 0 0 {r}){prop_uuid_block(desc_uuid)}
\t\t\t(layer "F.Fab")
\t\t\t(hide yes)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t\t(thickness 0.15)
\t\t\t\t)
\t\t\t)
\t\t)
\t\t(path "{path}")
\t\t(sheetname "{sheetname}")
\t\t(sheetfile "{sheetfile}")
\t\t(attr smd)
\t\t(fp_line
\t\t\t(start -0.227064 -0.735)
\t\t\t(end 0.227064 -0.735)
\t\t\t(stroke
\t\t\t\t(width 0.12)
\t\t\t\t(type solid)
\t\t\t)
\t\t\t(layer "F.SilkS")
\t\t)
\t\t(fp_line
\t\t\t(start -0.227064 0.735)
\t\t\t(end 0.227064 0.735)
\t\t\t(stroke
\t\t\t\t(width 0.12)
\t\t\t\t(type solid)
\t\t\t)
\t\t\t(layer "F.SilkS")
\t\t)
\t\t(fp_rect
\t\t\t(start -1.68 -0.95)
\t\t\t(end 1.68 0.95)
\t\t\t(stroke
\t\t\t\t(width 0.05)
\t\t\t\t(type solid)
\t\t\t)
\t\t\t(fill no)
\t\t\t(layer "F.CrtYd")
\t\t)
\t\t(fp_rect
\t\t\t(start -1 -0.625)
\t\t\t(end 1 0.625)
\t\t\t(stroke
\t\t\t\t(width 0.1)
\t\t\t\t(type solid)
\t\t\t)
\t\t\t(fill no)
\t\t\t(layer "F.Fab")
\t\t)
\t\t(fp_text user "${{REFERENCE}}"
\t\t\t(at 0 0 {r})
\t\t\t(layer "F.Fab")
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 0.5 0.5)
\t\t\t\t\t(thickness 0.08)
\t\t\t\t)
\t\t\t)
\t\t)
\t\t(pad "1" smd roundrect
\t\t\t(at -0.9125 0)
\t\t\t(size 1.025 1.4)
\t\t\t(layers "F.Cu" "F.Mask" "F.Paste")
\t\t\t(roundrect_rratio 0.243902)
\t\t\t(net {net1_id} "{net1_name}")
\t\t\t(pintype "passive")
\t\t\t(uuid "{pad1_uuid}")
\t\t)
\t\t(pad "2" smd roundrect
\t\t\t(at 0.9125 0)
\t\t\t(size 1.025 1.4)
\t\t\t(layers "F.Cu" "F.Mask" "F.Paste")
\t\t\t(roundrect_rratio 0.243902)
\t\t\t(net {net2_id} "{net2_name}")
\t\t\t(pintype "passive")
\t\t\t(uuid "{pad2_uuid}")
\t\t)
\t\t(embedded_fonts no)
\t\t(model "${{KICAD9_3DMODEL_DIR}}/Resistor_SMD.3dshapes/R_0805_2012Metric.step"
\t\t\t(offset
\t\t\t\t(xyz 0 0 0)
\t\t\t)
\t\t\t(scale
\t\t\t\t(xyz 1 1 1)
\t\t\t)
\t\t\t(rotate
\t\t\t\t(xyz 0 0 0)
\t\t\t)
\t\t)
\t)"""
    return block

def main():
    shutil.copy(PCB, BACKUP)
    print(f"Backed up to {BACKUP}")

    text = PCB.read_text()
    replacements = []  # list of (start, end, new_text)

    search_start = 0
    tht_marker = f'(footprint "{THT_NAME}"'
    while True:
        idx = text.find(tht_marker, search_start)
        if idx == -1:
            break
        block_start, block_end = find_block(text, idx)
        block_text = text[block_start:block_end + 1]

        ref = extract(r'\(property "Reference" "([^"]+)"', block_text)
        # Only process R1-R24
        if ref and ref.startswith('R') and ref[1:].isdigit() and 1 <= int(ref[1:]) <= 24:
            # Position
            at_m = re.search(r'\(at ([\d.+-]+) ([\d.+-]+)(?:\s+([\d.+-]+))?\)', block_text)
            at_x = at_m.group(1)
            at_y = at_m.group(2)
            at_rot = at_m.group(3) or "0"

            value = extract(r'\(property "Value" "([^"]+)"', block_text, default="R")

            # Footprint UUID (first uuid in the block)
            fp_uuid = extract(r'\(uuid "([^"]+)"\)', block_text)

            # Property UUIDs — after each property header
            prop_uuids = re.findall(
                r'\(property "[^"]+"\s*(?:\([^)]+\)\s*)*?\(uuid "([^"]+)"\)', block_text
            )
            ref_uuid  = prop_uuids[0] if len(prop_uuids) > 0 else ""
            val_uuid  = prop_uuids[1] if len(prop_uuids) > 1 else ""
            ds_uuid   = prop_uuids[2] if len(prop_uuids) > 2 else ""
            desc_uuid = prop_uuids[3] if len(prop_uuids) > 3 else ""

            path      = extract(r'\(path "([^"]+)"\)', block_text, default="")
            sheetname = extract(r'\(sheetname "([^"]+)"\)', block_text, default="/")
            sheetfile = extract(r'\(sheetfile "([^"]+)"\)', block_text, default="pi-dash-input-hat.kicad_sch")

            # Pad nets — match (net <id> "<name>") inside each pad block
            pad_nets = re.findall(r'\(pad "(?:1|2)".*?\(net (\d+) "([^"]+)"\)', block_text, re.DOTALL)
            net1_id, net1_name = (pad_nets[0][0], pad_nets[0][1]) if len(pad_nets) > 0 else ("0", "")
            net2_id, net2_name = (pad_nets[1][0], pad_nets[1][1]) if len(pad_nets) > 1 else ("0", "")

            # Pad UUIDs
            pad_uuids = re.findall(r'\(pad "[12]".*?\(uuid "([^"]+)"\)', block_text, re.DOTALL)
            pad1_uuid = pad_uuids[0] if len(pad_uuids) > 0 else ""
            pad2_uuid = pad_uuids[1] if len(pad_uuids) > 1 else ""

            new_block = make_0805_block(
                at_x, at_y, at_rot, ref, value,
                fp_uuid, ref_uuid, val_uuid, ds_uuid, desc_uuid,
                path, sheetname, sheetfile,
                net1_id, net1_name, net2_id, net2_name,
                pad1_uuid, pad2_uuid,
            )
            replacements.append((block_start, block_end, new_block))
            print(f"  Queued replacement: {ref} at ({at_x}, {at_y}) rot={at_rot}")
        else:
            print(f"  Skipping footprint with ref={ref}")

        search_start = block_end + 1

    if not replacements:
        print("No THT resistor blocks found for R1-R24.")
        return

    # Apply replacements in reverse order so indices stay valid
    replacements.sort(key=lambda x: x[0], reverse=True)
    for start, end, new_text in replacements:
        text = text[:start] + new_text + text[end + 1:]

    PCB.write_text(text)
    print(f"\nDone — replaced {len(replacements)} footprints. File saved.")
    print("Re-open in KiCad, then re-run place_components.py in the scripting console.")

if __name__ == "__main__":
    main()
