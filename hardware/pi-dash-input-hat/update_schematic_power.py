#!/usr/bin/env python3
"""
Adds the automotive power regulation section to pi-dash-input-hat.kicad_sch.
Run OUTSIDE KiCad.  Then File > Revert in KiCad to load changes.

New components added:
  J3  — 2-pin screw terminal (12V_BATT + GND_CAR input)
  F1  — 2.5A polyfuse (resettable overcurrent)
  D17 — SMAJ36A TVS (load-dump clamp)
  Q1  — P-ch MOSFET (reverse polarity protection)
  C1  — 220µF / 35V bulk cap
  U9  — LM2596-5.0 buck converter
  D18 — SB360 Schottky freewheeling diode
  L1  — 100µH / 3A output inductor
  C2  — 220µF / 10V output filter cap
  D19 — Green LED (power-on indicator)
  R25 — 1kΩ LED current limiter

Net topology:
  J3.pin1 → F1 → (TVS D17 shunts to GND_CAR) → Q1.S → Q1.D →
  C1(+) → U9.VIN
  U9.OUT → D18(K) (D18.A → GND) → L1 → +5V → C2 → GND
                                               → D19 → R25 → GND
  U9.GND, U9./SHDN → GND
  Q1.G → GND_CAR (low = MOSFET on; blocks reversed polarity)
  J3.pin2 → GND_CAR
"""

import uuid as _uuid
import re

SCH = '/home/zach/Documents/pi-dash/hardware/pi-dash-input-hat/pi-dash-input-hat.kicad_sch'
SCH_UUID = '26eef84c-befb-42bd-b327-458dd5de8766'

def uid():
    return str(_uuid.uuid4())

with open(SCH) as f:
    content = f.read()

# ── insertion points ────────────────────────────────────────────────────────
# lib_symbols closing paren
ls = content.find('\t(lib_symbols')
depth, lib_end = 0, ls
for i, c in enumerate(content[ls:], ls):
    if c == '(': depth += 1
    elif c == ')':
        depth -= 1
        if depth == 0: lib_end = i; break

# schematic body: insert before (embedded_fonts …) at file end
sch_ins = content.rfind('\n\t(embedded_fonts')

already = set(re.findall(r'\t\t\(symbol "([^"]+)"', content[ls:lib_end]))

# ── S-expression builders ───────────────────────────────────────────────────
T = '\t'

def eff(size=1.27, hide=False):
    h = f'\n{T*5}(hide yes)' if hide else ''
    return (f'(effects\n{T*5}(font\n{T*6}(size {size} {size})\n{T*5}){h}\n{T*4})')

def sprop(name, val, ax, ay, size=1.27, hide=False):
    return (f'{T*3}(property "{name}" "{val}"\n'
            f'{T*4}(at {ax} {ay} 0)\n'
            f'{T*4}{eff(size, hide)}\n'
            f'{T*3})')

def spin(num, name, x, y, angle, ptype='passive', ln=2.54):
    n = '~' if name == '~' else name
    return (f'{T*4}(pin {ptype} line\n'
            f'{T*5}(at {x} {y} {angle})\n'
            f'{T*5}(length {ln})\n'
            f'{T*5}(name "{n}"\n{T*6}(effects\n{T*7}(font\n{T*8}(size 1.27 1.27)\n{T*7})\n{T*6})\n{T*5})\n'
            f'{T*5}(number "{num}"\n{T*6}(effects\n{T*7}(font\n{T*8}(size 1.27 1.27)\n{T*7})\n{T*6})\n{T*5})\n'
            f'{T*4})')

def spoly(pts, width=0):
    p = ' '.join(f'(xy {x} {y})' for x, y in pts)
    return (f'{T*4}(polyline\n{T*5}(pts\n{T*6}{p}\n{T*5})\n'
            f'{T*5}(stroke\n{T*6}(width {width})\n{T*6}(type default)\n{T*5})\n'
            f'{T*5}(fill\n{T*6}(type none)\n{T*5})\n{T*4})')

def srect(x1, y1, x2, y2, fill='background', width=0.254):
    return (f'{T*4}(rectangle\n{T*5}(start {x1} {y1})\n{T*5}(end {x2} {y2})\n'
            f'{T*5}(stroke\n{T*6}(width {width})\n{T*6}(type default)\n{T*5})\n'
            f'{T*5}(fill\n{T*6}(type {fill})\n{T*5})\n{T*4})')

def sarc(cx, cy, r, start_angle, end_angle):
    import math
    sa, ea = math.radians(start_angle), math.radians(end_angle)
    sx, sy = cx + r*math.cos(sa), cy + r*math.sin(sa)
    ex, ey = cx + r*math.cos(ea), cy + r*math.sin(ea)
    return (f'{T*4}(arc\n{T*5}(start {sx:.4f} {sy:.4f})\n'
            f'{T*5}(mid {cx + r*math.cos((sa+ea)/2):.4f} {cy + r*math.sin((sa+ea)/2):.4f})\n'
            f'{T*5}(end {ex:.4f} {ey:.4f})\n'
            f'{T*5}(stroke\n{T*6}(width 0)\n{T*6}(type default)\n{T*5})\n'
            f'{T*5}(fill\n{T*6}(type none)\n{T*5})\n{T*4})')

# ── lib symbol definitions ──────────────────────────────────────────────────

def lib_sym(libname, body0, body1, ref_char, ref_ax, ref_ay, val_ax, val_ay,
            fp='', ds='~', pin_names_offset=1.016, pin_names_hide=True):
    pno = f'(offset {pin_names_offset})' + ('\n\t\t\t(hide yes)' if pin_names_hide else '')
    sname = libname.split(':')[1]
    return (f'{T*2}(symbol "{libname}"\n'
            f'{T*3}(pin_names\n{T*4}{pno}\n{T*3})\n'
            f'{T*3}(exclude_from_sim no)\n{T*3}(in_bom yes)\n{T*3}(on_board yes)\n'
            f'{sprop("Reference", ref_char, ref_ax, ref_ay)}\n'
            f'{sprop("Value", sname, val_ax, val_ay)}\n'
            f'{sprop("Footprint", fp, 0, 0, hide=True)}\n'
            f'{sprop("Datasheet", ds, 0, 0, hide=True)}\n'
            f'{sprop("Description", "", 0, 0, hide=True)}\n'
            f'{T*3}(symbol "{sname}_0_1"\n{body0}\n{T*3})\n'
            f'{T*3}(symbol "{sname}_1_1"\n{body1}\n{T*3})\n'
            f'{T*3}(embedded_fonts no)\n{T*2})')

# Device:C — vertical capacitor
NEW_C = lib_sym(
    'Device:C',
    body0='\n'.join([
        spoly([(0.6096, -0.254), (-0.6096, -0.254)], 0.254),
        spoly([(0.6096,  0.254), (-0.6096,  0.254)], 0.254),
    ]),
    body1='\n'.join([
        spin('1', '~', 0,  1.524, 270),
        spin('2', '~', 0, -1.524, 90),
    ]),
    ref_char='C', ref_ax=1.651, ref_ay=0.508,
    val_ax=1.651, val_ay=-1.016,
)

# Device:L — inductor (3-arc coil)
NEW_L = lib_sym(
    'Device:L',
    body0='\n'.join([
        sarc(-1.27, 0, 0.635, 0, 180),
        sarc(0,     0, 0.635, 0, 180),
        sarc( 1.27, 0, 0.635, 0, 180),
    ]),
    body1='\n'.join([
        spin('1', '~', -3.81, 0, 0),
        spin('2', '~',  3.81, 0, 180),
    ]),
    ref_char='L', ref_ax=1.778, ref_ay=0.508,
    val_ax=1.778, val_ay=-0.508,
    pin_names_offset=0,
)

# Device:Polyfuse — resettable fuse (rectangle + 'R' marker)
NEW_FUSE = lib_sym(
    'Device:Polyfuse',
    body0='\n'.join([
        srect(-1.016, -0.508, 1.016, 0.508),
        spoly([(-1.524, 0), (-1.016, 0)]),
        spoly([(1.016, 0), (1.524, 0)]),
        # 'R' squiggle inside — two small bumps
        spoly([(-0.635, -0.254), (-0.381, 0.254), (0, -0.254), (0.381, 0.254), (0.635, -0.254)]),
    ]),
    body1='\n'.join([
        spin('1', 'A', -3.81, 0, 0),
        spin('2', 'K',  3.81, 0, 180),
    ]),
    ref_char='F', ref_ax=0, ref_ay=1.27,
    val_ax=0, val_ay=-1.27,
    pin_names_offset=0,
)

# Connector_Generic:Conn_01x02_Male — 2-pin vertical connector (J3 screw terminal)
NEW_CONN2 = lib_sym(
    'Connector_Generic:Conn_01x02_Male',
    body0='\n'.join([
        srect(-1.27, -2.54, 0, 2.54),
        spoly([(0, 2.54), (0, -2.54)]),
    ]),
    body1='\n'.join([
        spin('1', 'Pin_1', 2.54,  1.27, 180),
        spin('2', 'Pin_2', 2.54, -1.27, 180),
    ]),
    ref_char='J', ref_ax=0, ref_ay=3.81,
    val_ax=0, val_ay=-3.81,
    pin_names_offset=1.016, pin_names_hide=True,
)

# Regulator_Switching:LM2596-5.0 — simplified 4-pin buck converter
# Pins: VIN(1,left), GND(2,bottom), OUT(3,right), /SHDN(4,left)
NEW_LM2596 = lib_sym(
    'Regulator_Switching:LM2596-5.0',
    body0=srect(-3.81, -3.81, 3.81, 3.81),
    body1='\n'.join([
        spin('1', 'VIN',    -6.35,  2.54, 0,   'input'),
        spin('2', 'GND',     0,    -6.35, 90,  'power_in'),
        spin('3', 'OUT',     6.35,  2.54, 180, 'output'),
        spin('4', '~{/SHDN}', -6.35, -2.54, 0, 'input'),
    ]),
    ref_char='U', ref_ax=0, ref_ay=5.08,
    val_ax=0, val_ay=-5.08,
    fp='Package_TO_SOT_THT:TO-263-5',
    pin_names_offset=1.016, pin_names_hide=False,
)

# Transistor_FET:Q_PMOS_GSD — P-ch MOSFET (gate=pin1, source=pin2, drain=pin3)
NEW_PMOS = lib_sym(
    'Transistor_FET:Q_PMOS_GSD',
    body0='\n'.join([
        # Gate stub
        spoly([(-2.54, 0), (-1.27, 0)]),
        # Gate bar (vertical)
        spoly([(-1.27, -2.54), (-1.27, 2.54)], 0.254),
        # Source
        spoly([(-1.27, 1.27), (0, 1.27), (0, 2.54)]),
        # Drain
        spoly([(-1.27, -1.27), (0, -1.27), (0, -2.54)]),
        # Channel bar
        spoly([(0, 1.27), (0, 0.508)]),
        spoly([(0, -0.508), (0, -1.27)]),
        # Arrow on source (P-type: arrow INTO gate)
        spoly([(-1.27, 1.27), (-0.762, 0.508)]),
        spoly([(-0.762, 0.508), (-0.762, 1.524), (-1.27, 1.27)]),
    ]),
    body1='\n'.join([
        spin('1', 'G', -5.08,   0,    0,   'input'),
        spin('2', 'S',  2.54,   2.54, 270, 'passive'),
        spin('3', 'D',  2.54,  -2.54, 90,  'passive'),
    ]),
    ref_char='Q', ref_ax=1.905, ref_ay=0,
    val_ax=1.905, val_ay=-1.524,
    pin_names_offset=0, pin_names_hide=False,
)

# power:+5V — identical structure to power:+3V3 already in schematic
NEW_5V = (
    f'{T*2}(symbol "power:+5V"\n'
    f'{T*3}(exclude_from_sim no)\n{T*3}(in_bom yes)\n{T*3}(on_board yes)\n'
    f'{sprop("Reference", "#PWR", 0, -3.81, hide=True)}\n'
    f'{sprop("Value", "+5V", 0, 3.81)}\n'
    f'{sprop("Footprint", "", 0, 0, hide=True)}\n'
    f'{sprop("Datasheet", "", 0, 0, hide=True)}\n'
    f'{sprop("Description", "", 0, 0, hide=True)}\n'
    f'{T*3}(symbol "+5V_0_1"\n'
    f'{spoly([(-0.762, 1.27), (0, 2.54), (0.762, 1.27)])}\n'
    f'{spoly([(0, 0), (0, 1.27)])}\n'
    f'{T*3})\n'
    f'{T*3}(symbol "+5V_1_1"\n'
    f'{spin("1", "~", 0, 0, 90, "power_in", 0)}\n'
    f'{T*3})\n'
    f'{T*3}(embedded_fonts no)\n{T*2})'
)

new_lib_syms = []
pairs = [
    ('Device:C',                          NEW_C),
    ('Device:L',                          NEW_L),
    ('Device:Polyfuse',                   NEW_FUSE),
    ('Connector_Generic:Conn_01x02_Male', NEW_CONN2),
    ('Regulator_Switching:LM2596-5.0',   NEW_LM2596),
    ('Transistor_FET:Q_PMOS_GSD',        NEW_PMOS),
    ('power:+5V',                         NEW_5V),
]
for name, sym_text in pairs:
    if name not in already:
        new_lib_syms.append(sym_text)

# ── Component instance builder ─────────────────────────────────────────────

def inst(lib_id, ref, value, x, y, angle, pins, fp='', props_extra=None):
    """Generate a schematic symbol instance."""
    props = (f'{T}(property "Reference" "{ref}"\n'
             f'{T*2}(at {x} {y-3} 0)\n'
             f'{T*2}(effects\n{T*3}(font\n{T*4}(size 1.016 1.016)\n{T*3})\n{T*2})\n'
             f'{T})\n'
             f'{T}(property "Value" "{value}"\n'
             f'{T*2}(at {x} {y+3} 0)\n'
             f'{T*2}(effects\n{T*3}(font\n{T*4}(size 1.016 1.016)\n{T*3})\n{T*2})\n'
             f'{T})\n'
             f'{T}(property "Footprint" "{fp}"\n'
             f'{T*2}(at {x} {y} 0)\n'
             f'{T*2}(effects\n{T*3}(font\n{T*4}(size 1.27 1.27)\n{T*3})\n'
             f'{T*3}(hide yes)\n{T*2})\n{T})\n'
             f'{T}(property "Datasheet" "~"\n'
             f'{T*2}(at {x} {y} 0)\n'
             f'{T*2}(effects\n{T*3}(font\n{T*4}(size 1.27 1.27)\n{T*3})\n'
             f'{T*3}(hide yes)\n{T*2})\n{T})\n'
             f'{T}(property "Description" ""\n'
             f'{T*2}(at {x} {y} 0)\n'
             f'{T*2}(effects\n{T*3}(font\n{T*4}(size 1.27 1.27)\n{T*3})\n'
             f'{T*3}(hide yes)\n{T*2})\n{T})')
    if props_extra:
        for pname, pval in props_extra:
            props += (f'\n{T}(property "{pname}" "{pval}"\n'
                      f'{T*2}(at {x} {y} 0)\n'
                      f'{T*2}(effects\n{T*3}(font\n{T*4}(size 1.27 1.27)\n{T*3})\n'
                      f'{T*3}(hide yes)\n{T*2})\n{T})')
    pin_str = '\n'.join(f'{T}(pin "{p}"\n{T*2}(uuid "{uid()}")\n{T})' for p in pins)
    return (f'(symbol\n'
            f'{T}(lib_id "{lib_id}")\n'
            f'{T}(at {x} {y} {angle})\n'
            f'{T}(unit 1)\n'
            f'{T}(exclude_from_sim no)\n{T}(in_bom yes)\n{T}(on_board yes)\n{T}(dnp no)\n'
            f'{T}(uuid "{uid()}")\n'
            f'{props}\n'
            f'{pin_str}\n'
            f'{T}(instances\n'
            f'{T*2}(project "pi-dash-input-hat"\n'
            f'{T*3}(path "/{SCH_UUID}"\n'
            f'{T*4}(reference "{ref}")\n{T*4}(unit 1)\n{T*3})\n{T*2})\n{T})\n'
            f')')

def wire(x1, y1, x2, y2):
    return (f'(wire\n'
            f'{T}(pts\n{T*2}(xy {x1} {y1}) (xy {x2} {y2})\n{T})\n'
            f'{T}(stroke\n{T*2}(width 0)\n{T*2}(type default)\n{T})\n'
            f'{T}(uuid "{uid()}")\n'
            f')')

def net_label(name, x, y, angle=0):
    just = 'right' if angle == 0 else 'left'
    return (f'(label "{name}"\n'
            f'{T}(at {x} {y} {angle})\n'
            f'{T}(effects\n{T*2}(font\n{T*3}(size 1.27 1.27)\n{T*2})\n'
            f'{T*2}(justify {just})\n{T})\n'
            f'{T}(uuid "{uid()}")\n'
            f')')

def global_label(name, x, y, angle=0, shape='bidirectional'):
    u = uid()
    return (f'(global_label "{name}"\n'
            f'{T}(shape {shape})\n'
            f'{T}(at {x} {y} {angle})\n'
            f'{T}(fields_autoplaced yes)\n'
            f'{T}(effects\n{T*2}(font\n{T*3}(size 1.27 1.27)\n{T*2})\n{T})\n'
            f'{T}(uuid "{u}")\n'
            f'{T}(property "Intersheetrefs" "${{INTERSHEET_REFS}}"\n'
            f'{T*2}(at {x} {y} {angle})\n'
            f'{T*2}(effects\n{T*3}(font\n{T*4}(size 1.27 1.27)\n{T*3})\n'
            f'{T*3}(hide yes)\n{T*2})\n{T})\n'
            f')')

def pwr_flag(lib_id, name, x, y):
    """Power symbol instance (like +5V, GND)."""
    rname = '#PWR' + str(abs(hash(uid())))[:3]
    return (f'(symbol\n'
            f'{T}(lib_id "{lib_id}")\n'
            f'{T}(at {x} {y} 0)\n'
            f'{T}(unit 1)\n'
            f'{T}(exclude_from_sim no)\n{T}(in_bom yes)\n{T}(on_board yes)\n{T}(dnp no)\n'
            f'{T}(uuid "{uid()}")\n'
            f'{T}(property "Reference" "{rname}"\n'
            f'{T*2}(at {x} {y} 0)\n'
            f'{T*2}(effects\n{T*3}(font\n{T*4}(size 1.016 1.016)\n{T*3})\n'
            f'{T*3}(hide yes)\n{T*2})\n{T})\n'
            f'{T}(property "Value" "{name}"\n'
            f'{T*2}(at {x} {y+2.54} 0)\n'
            f'{T*2}(effects\n{T*3}(font\n{T*4}(size 1.016 1.016)\n{T*3})\n{T*2})\n{T})\n'
            f'{T}(property "Footprint" ""\n{T*2}(at {x} {y} 0)\n{T*2}(effects\n{T*3}(font\n{T*4}(size 1.27 1.27)\n{T*3})\n{T*2})\n{T})\n'
            f'{T}(property "Datasheet" ""\n{T*2}(at {x} {y} 0)\n{T*2}(effects\n{T*3}(font\n{T*4}(size 1.27 1.27)\n{T*3})\n{T*2})\n{T})\n'
            f'{T}(property "Description" ""\n{T*2}(at {x} {y} 0)\n{T*2}(effects\n{T*3}(font\n{T*4}(size 1.27 1.27)\n{T*3})\n{T*2})\n{T})\n'
            f'{T}(pin "1"\n{T*2}(uuid "{uid()}")\n{T})\n'
            f'{T}(instances\n'
            f'{T*2}(project "pi-dash-input-hat"\n'
            f'{T*3}(path "/{SCH_UUID}"\n'
            f'{T*4}(reference "{rname}")\n{T*4}(unit 1)\n{T*3})\n{T*2})\n{T})\n'
            f')')

# ── Layout constants  ───────────────────────────────────────────────────────
# Power section placed below existing content (channels end ~y=160)
# Main power rail at y=200.  GND drops to y=220.  +5V rises to y=182.

Y_RAIL  = 200   # main horizontal 12V power rail
Y_GND   = 222   # GND / GND_CAR drops
Y_5V    = 182   # +5V output level

# X positions (left to right flow)
X_J3   = 60
X_F1   = 88
X_TVS  = 110    # D17 tap on rail
X_Q1   = 127
X_C1   = 148    # C1 tap (drain of Q1 / VIN of U9)
X_U9   = 172
X_D18  = 196    # D18 tap (U9 OUT / L1 input)
X_L1   = 212
X_C2   = 232    # C2 / +5V output
X_D19  = 255    # LED
X_R25  = 255    # LED resistor (below D19)

# ── Component instances ─────────────────────────────────────────────────────
new_insts = []

# J3 — 2-pin screw terminal (12V in + GND_CAR)
# Pin 1 at (X_J3+2.54, Y_RAIL-1.27) — top pin = 12V
# Pin 2 at (X_J3+2.54, Y_RAIL+1.27) — bottom pin = GND_CAR
new_insts.append(inst(
    'Connector_Generic:Conn_01x02_Male', 'J3', '12V_PWR_IN',
    X_J3, Y_RAIL, 0, ['1', '2'],
    fp='Connector_Phoenix_MKDS:PhoenixContact_MKDS_1,5_2-5.08_1x02_P5.08mm_Horizontal',
))

# F1 — 2.5A polyfuse
new_insts.append(inst(
    'Device:Polyfuse', 'F1', '2.5A',
    X_F1, Y_RAIL, 90, ['1', '2'],
    fp='Fuse:Fuse_Bourns_MF-R_Radial',
))

# D17 — SMAJ36A TVS (cathode at Y_RAIL, anode at Y_GND, vertical)
new_insts.append(inst(
    'Device:D', 'D17', 'SMAJ36A',
    X_TVS, (Y_RAIL + Y_GND) / 2, 270, ['1', '2'],
    fp='Diode_SMD:D_SMA',
))

# Q1 — P-ch MOSFET reverse polarity protection
new_insts.append(inst(
    'Transistor_FET:Q_PMOS_GSD', 'Q1', 'DMG2305UX',
    X_Q1, Y_RAIL, 0, ['1', '2', '3'],
    fp='Package_TO_SOT_SMD:SOT-23',
))

# C1 — 220µF 35V bulk cap
new_insts.append(inst(
    'Device:C', 'C1', '220u/35V',
    X_C1, (Y_RAIL + Y_GND) / 2, 0, ['1', '2'],
    fp='Capacitor_THT:CP_Radial_D8.0mm_P3.50mm',
))

# U9 — LM2596-5.0 buck converter
new_insts.append(inst(
    'Regulator_Switching:LM2596-5.0', 'U9', 'LM2596-5.0',
    X_U9, Y_RAIL, 0, ['1', '2', '3', '4'],
    fp='Package_TO_SOT_THT:DIP-8_W7.62mm',
))

# D18 — SB360 Schottky freewheeling diode (cathode toward U9 OUT, anode to GND)
new_insts.append(inst(
    'Device:D', 'D18', 'SB360',
    X_D18, (Y_RAIL + Y_GND) / 2, 270, ['1', '2'],
    fp='Diode_SMD:D_SMA',
))

# L1 — 100µH / 3A radial inductor
new_insts.append(inst(
    'Device:L', 'L1', '100u/3A',
    X_L1, Y_RAIL, 90, ['1', '2'],
    fp='Inductor_THT:L_Radial_D8.7mm_P5.00mm',
))

# C2 — 220µF 10V output filter cap
new_insts.append(inst(
    'Device:C', 'C2', '220u/10V',
    X_C2, (Y_RAIL + Y_GND) / 2, 0, ['1', '2'],
    fp='Capacitor_THT:CP_Radial_D8.0mm_P3.50mm',
))

# D19 — green LED power indicator (horizontal, anode left)
new_insts.append(inst(
    'Device:LED', 'D19', 'LED_GRN',
    X_D19, Y_5V + 8, 0, ['1', '2'],
    fp='LED_THT:LED_D3.0mm',
))

# R25 — 1kΩ LED current limiter
new_insts.append(inst(
    'Device:R', 'R25', '1k',
    X_R25, Y_5V + 18, 90, ['1', '2'],
    fp='Resistor_SMD:R_0805_2012Metric',
))

# ── Power / net labels ─────────────────────────────────────────────────────
new_labels = []

# +5V symbols
new_labels.append(pwr_flag('power:+5V', '+5V', X_C2,  Y_5V))
new_labels.append(pwr_flag('power:+5V', '+5V', X_D19, Y_5V + 4))

# GND symbols
for gx, gy in [(X_U9, Y_GND), (X_D18, Y_GND), (X_C2, Y_GND), (X_R25, Y_5V + 24)]:
    new_labels.append(pwr_flag('power:GND', 'GND', gx, gy))

# GND_CAR global labels
for gx, gy in [(X_TVS, Y_GND), (X_C1, Y_GND), (X_J3, Y_RAIL + 6)]:
    new_labels.append(global_label('GND_CAR', gx, gy, 270, 'passive'))

# Net labels on main rail to name key nodes
new_labels.append(net_label('12V_BATT',  X_J3 + 4,  Y_RAIL - 2, 0))
new_labels.append(net_label('12V_CLEAN', X_C1 + 2,  Y_RAIL - 2, 0))
new_labels.append(net_label('+5V_OUT',   X_C2 - 2,  Y_5V + 2,   0))

# ── Wires ──────────────────────────────────────────────────────────────────
new_wires = []

# Main 12V rail (horizontal, Y_RAIL)
new_wires += [
    wire(X_J3 + 2.54, Y_RAIL - 1.27, X_F1 - 3.81, Y_RAIL),  # J3 pin1 → F1
    wire(X_F1 + 3.81, Y_RAIL, X_TVS, Y_RAIL),                 # F1 → TVS tap
    wire(X_TVS, Y_RAIL, X_Q1 - 5.08, Y_RAIL),                 # TVS tap → Q1 source
    wire(X_Q1 + 2.54, Y_RAIL - 2.54, X_C1, Y_RAIL),           # Q1 drain → C1 tap
    wire(X_C1, Y_RAIL, X_U9 - 6.35, Y_RAIL + 2.54),           # C1 tap → U9 VIN
]

# D17 TVS vertical drop from rail to GND_CAR
new_wires += [
    wire(X_TVS, Y_RAIL, X_TVS, (Y_RAIL + Y_GND) / 2 - 3.81),
    wire(X_TVS, (Y_RAIL + Y_GND) / 2 + 3.81, X_TVS, Y_GND),
]

# C1 vertical drop
new_wires += [
    wire(X_C1, Y_RAIL, X_C1, (Y_RAIL + Y_GND) / 2 - 1.524),
    wire(X_C1, (Y_RAIL + Y_GND) / 2 + 1.524, X_C1, Y_GND),
]

# U9 GND and /SHDN → GND
new_wires += [
    wire(X_U9, Y_RAIL + 6.35, X_U9, Y_GND),
    wire(X_U9 - 6.35, Y_RAIL - 2.54, X_U9 - 6.35, Y_GND),   # /SHDN to GND
    wire(X_U9 - 6.35, Y_GND, X_U9, Y_GND),
]

# U9 OUT → D18(K) + L1
new_wires += [
    wire(X_U9 + 6.35, Y_RAIL + 2.54, X_D18, Y_RAIL),
    wire(X_D18, Y_RAIL, X_L1 - 3.81, Y_RAIL),
]

# D18 drop from rail to GND
new_wires += [
    wire(X_D18, Y_RAIL, X_D18, (Y_RAIL + Y_GND) / 2 - 3.81),
    wire(X_D18, (Y_RAIL + Y_GND) / 2 + 3.81, X_D18, Y_GND),
]

# L1 → +5V / C2
new_wires += [
    wire(X_L1 + 3.81, Y_RAIL, X_C2, Y_RAIL),
    wire(X_C2, Y_RAIL, X_C2, Y_5V),                  # up to +5V symbol
    wire(X_C2, Y_RAIL, X_C2, (Y_RAIL + Y_GND) / 2 - 1.524),  # down to C2+
    wire(X_C2, (Y_RAIL + Y_GND) / 2 + 1.524, X_C2, Y_GND),
]

# D19 and R25 (LED chain from +5V to GND)
new_wires += [
    wire(X_D19, Y_5V + 4, X_D19, Y_5V + 5.08),   # +5V → D19 anode
    wire(X_D19, Y_5V + 8 + 1.27, X_D19, Y_5V + 13),  # D19 cathode → R25 top
    wire(X_R25, Y_5V + 23, X_R25, Y_GND),          # R25 bottom → GND
]

# J3 pin2 drop to GND_CAR
new_wires.append(wire(X_J3 + 2.54, Y_RAIL + 1.27, X_J3, Y_RAIL + 6))

# ── Assemble additions ─────────────────────────────────────────────────────
lib_addition = '\n'.join(new_lib_syms)
body_addition = '\n'.join(new_insts + new_labels + new_wires)

# ── Insert into schematic ──────────────────────────────────────────────────
# 1. Insert new lib symbols before closing ) of lib_symbols block
if lib_addition:
    content = content[:lib_end] + '\n' + lib_addition + '\n' + content[lib_end:]
    # Update sch_ins offset accordingly
    sch_ins += len('\n' + lib_addition + '\n')

# 2. Insert components/wires/labels before (embedded_fonts ...) at end
content = content[:sch_ins] + '\n' + body_addition + '\n' + content[sch_ins:]

with open(SCH, 'w') as f:
    f.write(content)

print("Schematic updated — open in KiCad (File > Revert) to review.")
print(f"Added: {len(new_lib_syms)} new lib symbols, {len(new_insts)} components,",
      f"{len(new_labels)} labels/power symbols, {len(new_wires)} wires.")
