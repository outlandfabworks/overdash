import pcbnew
board = pcbnew.GetBoard()

def place(ref, x, y, rot=0):
    fp = board.FindFootprintByReference(ref)
    if fp:
        fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
        fp.SetOrientationDegrees(rot)
    else:
        print("Not found:", ref)

# J1 — 1x9 Molex connector, clear of H1 mounting hole at (3.5, 3.5)
place('J1', 20, 5)

# Layout: 2 columns x 4 rows
#
# cx_col1=8, cx_col2=37  (col2 must be ≥ cx1+28.17 so DIP right cx+24.67 clears TVS left cx2−3.5)
# Row cy values: 14, 25, 36, 47  (11 mm row pitch)

layout = [
    # dn     rn     un     rpn    rln    dln     cx   cy
    ('D1', 'R1',  'U1', 'R9',  'R17', 'D9',    8,  14),   # CH1 Left Turn
    ('D2', 'R2',  'U2', 'R10', 'R18', 'D10',  37,  14),   # CH2 Right Turn
    ('D3', 'R3',  'U3', 'R11', 'R19', 'D11',   8,  25),   # CH3 High Beam
    ('D4', 'R4',  'U4', 'R12', 'R20', 'D12',  37,  25),   # CH4 Parking
    ('D5', 'R5',  'U5', 'R13', 'R21', 'D13',   8,  36),   # CH5 Hazards
    ('D6', 'R6',  'U6', 'R14', 'R22', 'D14',  37,  36),   # CH6 Reverse
    ('D7', 'R7',  'U7', 'R15', 'R23', 'D15',   8,  47),   # CH7 Illumination
    ('D8', 'R8',  'U8', 'R16', 'R24', 'D16',  37,  47),   # CH8 Spare
]

# Component offsets from channel origin (cx, cy):
#   D  TVS  SMAJ15A  → cx+0,  cy      SMA, courtyard ±3.5×1.75
#   R  560Ω  0805   → cx+7,  cy      0805 courtyard ±1.68×0.95
#   U  PC817  DIP-4 → cx+16, cy      courtyard −1.06..+8.67 × −1.52..+4.07
#   R  10kΩ  0805   → cx+16, cy-4    above DIP; courtyard bottom cy-3.05 clears DIP top cy-1.52
#   R  1kΩ   0805   → cx+12, cy-5    x gap to DIP=1.26mm, to rpn=0.64mm; x gap to LED row above=4.17mm
#   D  LED   3mm    → cx+19, cy+7 @0° DIP gap=0.72mm; pad2 at cx+21.54 clears H4(61.5,53)
for dn, rn, un, rpn, rln, dln, cx, cy in layout:
    place(dn,  cx,     cy,     0)   # TVS diode (SMA)
    place(rn,  cx+7,   cy,     0)   # 560Ω 0805
    place(un,  cx+16,  cy,     0)   # PC817 optocoupler (DIP-4)
    place(rpn, cx+16,  cy-4,   0)   # 10kΩ 0805 pull-up
    place(rln, cx+12,  cy-5,   0)   # 1kΩ 0805
    place(dln, cx+19,  cy+7,   0)   # Status LED (3mm, horizontal)

pcbnew.Refresh()
print("Done — 8 channels in 2-column x 4-row grid, cy=14/25/36/47")
