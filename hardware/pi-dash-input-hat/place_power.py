"""
KiPython script — run in KiCad PCB editor scripting console.
Loads power section footprints from the KiCad library and places them
in the expanded right section of the board (X = 66–99 mm).

Run after resize_board.py + File > Revert.
Then run assign_nets.py to assign nets.

exec(open('/home/zach/Documents/pi-dash/hardware/pi-dash-input-hat/place_power.py').read())
"""
import pcbnew, os

board = pcbnew.GetBoard()
FP = '/snap/kicad/22/usr/share/kicad/footprints'

def place(lib, name, ref, value, x_mm, y_mm, angle=0):
    path = os.path.join(FP, f'{lib}.pretty')
    fp = pcbnew.FootprintLoad(path, name)
    if not fp:
        print(f"  FAILED to load {lib}:{name}")
        return None
    fp.SetReference(ref)
    fp.SetValue(value)
    fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x_mm), pcbnew.FromMM(y_mm)))
    fp.SetOrientationDegrees(angle)
    board.Add(fp)
    print(f"  {ref} ({value})  at ({x_mm}, {y_mm})")
    return fp

print("Placing power section components...")

# ── Layout (power section: X = 66–99 mm, Y = 3–53 mm) ──────────────────────
#
#  Top row  (y≈14): [U9 LM2596 TO-220-5]      [L1 inductor]
#  Mid rail (y≈25): [J3 Phoenix]  [F1 poly]   [Q1 SOT-23]
#  Low row  (y≈39): [D17 TVS]  [C1 bulk]  [D18 Schottky]  [C2 output]
#  Bottom   (y≈48): [D19 LED]  [R25 1k]
#
# 12V flow: J3→F1→(D17 TVS shunt)→Q1 S→D→(C1 bulk)→U9 VIN
# 5V out:   U9 OUT → (D18 fly-diode) → L1 → +5V → C2 → GND
# LED:      +5V → D19 → R25 → GND

place('Connector_Phoenix_MSTB',
      'PhoenixContact_MSTBA_2,5_2-G-5,08_1x02_P5.08mm_Horizontal',
      'J3', '12V_PWR_IN', 69, 25)

place('Resistor_THT',
      'R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal',
      'F1', '2.5A_Poly', 76, 25)

place('Diode_SMD', 'D_SMA',
      'D17', 'SMAJ36A', 76, 39, 270)       # vertical: K up (toward rail)

place('Package_TO_SOT_SMD', 'SOT-23',
      'Q1', 'DMG2305UX', 82, 25)

place('Capacitor_THT', 'CP_Radial_D8.0mm_P3.50mm',
      'C1', '220u/35V', 82, 39)

place('Package_TO_SOT_THT', 'TO-220-5_Vertical',
      'U9', 'LM2596-5.0', 87, 13)

place('Diode_SMD', 'D_SMA',
      'D18', 'SB360', 90, 39, 270)         # vertical: K up (toward switch node)

place('Inductor_THT', 'L_Radial_D10.0mm_P5.00mm_Fastron_07P',
      'L1', '100u/3A', 90, 25)

place('Capacitor_THT', 'CP_Radial_D8.0mm_P3.50mm',
      'C2', '220u/10V', 95, 39)

place('LED_THT', 'LED_D3.0mm',
      'D19', 'LED_GRN', 95, 50)

place('Resistor_SMD', 'R_0805_2012Metric',
      'R25', '1k', 95, 46)

board.Save(board.GetFileName())
pcbnew.Refresh()
print("Done. Now run assign_nets.py to connect nets.")
