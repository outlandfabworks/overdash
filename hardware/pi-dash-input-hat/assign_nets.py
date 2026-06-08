import pcbnew

BOARD_FILE = '/home/zach/Documents/pi-dash/hardware/pi-dash-input-hat/pi-dash-input-hat.kicad_pcb'
board = pcbnew.LoadBoard(BOARD_FILE)

_net_cache = {}

def get_or_create_net(name):
    if name in _net_cache:
        return _net_cache[name]
    net = pcbnew.NETINFO_ITEM(board, name)
    board.Add(net)
    _net_cache[name] = net
    return net

def find_pad(fp, num):
    for pad in fp.Pads():
        if pad.GetNumber() == str(num):
            return pad
    return None

def assign(ref, pad_num, net_name):
    fp = board.FindFootprintByReference(ref)
    if not fp:
        print(f"FP not found: {ref}")
        return
    pad = find_pad(fp, pad_num)
    if not pad:
        print(f"Pad '{pad_num}' not found on {ref}")
        return
    pad.SetNet(get_or_create_net(net_name))

# Create all nets up front
for name in [
    'GND', 'GND_CAR', '+3V3', '+5V',
    'IN1_LT', 'IN2_RT', 'IN3_HB', 'IN4_PK',
    'IN5_HZ', 'IN6_RV', 'IN7_IL', 'IN8_SP',
    'GPIO4', 'GPIO5', 'GPIO6', 'GPIO13',
    'GPIO17', 'GPIO19', 'GPIO22', 'GPIO27',
    # Power section nets
    '12V_BATT', '12V_CLEAN', 'VIN_BUCK', 'SW_NODE', 'LED_PWR',
] + [f'CH{n}_MID' for n in range(1, 9)] \
  + [f'CH{n}_LED' for n in range(1, 9)]:
    get_or_create_net(name)

# Per-channel: D_TVS, R_560, U_PC817, R_pullup_10k, R_led_1k, D_LED, IN_net, GPIO_net
channels = [
    ('D1','R1', 'U1','R9', 'R17','D9',  'IN1_LT','GPIO4'),
    ('D2','R2', 'U2','R10','R18','D10', 'IN2_RT','GPIO17'),
    ('D3','R3', 'U3','R11','R19','D11', 'IN3_HB','GPIO27'),
    ('D4','R4', 'U4','R12','R20','D12', 'IN4_PK','GPIO22'),
    ('D5','R5', 'U5','R13','R21','D13', 'IN5_HZ','GPIO5'),
    ('D6','R6', 'U6','R14','R22','D14', 'IN6_RV','GPIO6'),
    ('D7','R7', 'U7','R15','R23','D15', 'IN7_IL','GPIO13'),
    ('D8','R8', 'U8','R16','R24','D16', 'IN8_SP','GPIO19'),
]

for i, (dn, rn, un, rpn, rln, dln, in_net, gpio) in enumerate(channels):
    ch   = i + 1
    mid  = f'CH{ch}_MID'
    led  = f'CH{ch}_LED'

    # TVS diode (SMAJ15A, D_SMA): pad 1 = A → car GND, pad 2 = K → input signal
    assign(dn, '1', 'GND_CAR')
    assign(dn, '2', in_net)

    # 560Ω input resistor (R_0805): pad 1 → input signal, pad 2 → opto input
    assign(rn, '1', in_net)
    assign(rn, '2', mid)

    # PC817 optocoupler (DIP-4):
    #   pin 1 A  → opto input (after R560)
    #   pin 2 K  → car GND
    #   pin 3 C  → GPIO / pull-up node
    #   pin 4 E  → Pi GND
    assign(un, '1', mid)
    assign(un, '2', 'GND_CAR')
    assign(un, '3', gpio)
    assign(un, '4', 'GND')

    # 10kΩ pull-up (R_0805): pad 1 → GPIO node, pad 2 → +3V3
    assign(rpn, '1', gpio)
    assign(rpn, '2', '+3V3')

    # 1kΩ LED resistor (R_0805): pad 1 → GPIO node, pad 2 → LED anode
    assign(rln, '1', gpio)
    assign(rln, '2', led)

    # Status LED (LED_D3.0mm): pad 1 A → LED anode, pad 2 K → Pi GND
    assign(dln, '1', led)
    assign(dln, '2', 'GND')

# J1 — 9-pin Molex: pads 1-8 = input signals, pad 9 = GND_CAR
for i, net in enumerate(['IN1_LT','IN2_RT','IN3_HB','IN4_PK',
                          'IN5_HZ','IN6_RV','IN7_IL','IN8_SP']):
    assign('J1', str(i + 1), net)
assign('J1', '9', 'GND_CAR')

# J2 — 2×20 Pi GPIO header (pad numbers = physical Pi pin numbers)
j2 = {
     1: '+3V3',   2: '+5V',    3: 'GPIO2',  4: '+5V',
     5: 'GPIO3',  6: 'GND',    7: 'GPIO4',  8: 'GPIO14',
     9: 'GND',   10: 'GPIO15', 11: 'GPIO17',12: 'GPIO18',
    13: 'GPIO27', 14: 'GND',   15: 'GPIO22',16: 'GPIO23',
    17: '+3V3',  18: 'GPIO24', 19: 'GPIO10',20: 'GND',
    21: 'GPIO9', 22: 'GPIO25', 23: 'GPIO11',24: 'GPIO8',
    25: 'GND',   26: 'GPIO7',  27: 'GPIO0', 28: 'GPIO1',
    29: 'GPIO5', 30: 'GND',   31: 'GPIO6', 32: 'GPIO12',
    33: 'GPIO13',34: 'GND',   35: 'GPIO19',36: 'GPIO16',
    37: 'GPIO26',38: 'GPIO20', 39: 'GND',  40: 'GPIO21',
}
for pad_num, net_name in j2.items():
    assign('J2', str(pad_num), net_name)

# ── Power section ─────────────────────────────────────────────────────────────
# J3 — 2-pin Phoenix screw terminal (12V input + GND_CAR)
assign('J3', '1', '12V_BATT')
assign('J3', '2', 'GND_CAR')

# F1 — series polyfuse (2.5A resettable)
assign('F1', '1', '12V_BATT')
assign('F1', '2', '12V_CLEAN')

# D17 — SMAJ36A TVS clamp (K on rail, A to car GND)
assign('D17', '1', 'GND_CAR')   # Anode
assign('D17', '2', '12V_CLEAN') # Cathode

# Q1 — DMG2305UX P-ch MOSFET reverse-polarity protection (SOT-23)
# Pad 1=G, 2=S, 3=D  (G→GND_CAR keeps MOSFET on; reversed polarity turns it off)
assign('Q1', '1', 'GND_CAR')    # Gate  → GND_CAR
assign('Q1', '2', '12V_CLEAN')  # Source → post-fuse rail
assign('Q1', '3', 'VIN_BUCK')   # Drain  → U9 VIN / C1 +

# C1 — 220µF/35V bulk input capacitor
assign('C1', '1', 'VIN_BUCK')   # +
assign('C1', '2', 'GND_CAR')    # −

# U9 — LM2596-5.0 buck converter (TO-220-5)
# Physical LM2596 pins: 1=OUT(switch), 2=VIN, 3=GND, 4=FB(fixed), 5=/ON-OFF
assign('U9', '1', 'SW_NODE')    # Switch output
assign('U9', '2', 'VIN_BUCK')   # VIN
assign('U9', '3', 'GND')        # GND (also exposed tab)
assign('U9', '4', 'GND')        # FB fixed internally; tie /ON-OFF to GND = always on
assign('U9', '5', 'GND')        # /ON-OFF → GND (always enabled)

# D18 — SB360 Schottky freewheeling diode (K toward switch node, A to GND)
assign('D18', '1', 'GND')       # Anode
assign('D18', '2', 'SW_NODE')   # Cathode → switch node

# L1 — 100µH/3A output inductor
assign('L1', '1', 'SW_NODE')    # pin 1 → switch node
assign('L1', '2', '+5V')        # pin 2 → +5V output

# C2 — 220µF/10V output filter capacitor
assign('C2', '1', '+5V')        # +
assign('C2', '2', 'GND')        # −

# D19 — green power LED (A→+5V, K→LED_PWR node)
assign('D19', '1', '+5V')       # Anode
assign('D19', '2', 'LED_PWR')   # Cathode → R25

# R25 — 1kΩ LED current limiter
assign('R25', '1', 'LED_PWR')   # → D19 cathode
assign('R25', '2', 'GND')       # → GND

board.Save(BOARD_FILE)
print("Done — all pads assigned, ratsnest ready.")
