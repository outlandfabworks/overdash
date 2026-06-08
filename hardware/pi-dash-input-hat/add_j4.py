"""
Adds J4 — 2×5 2.54mm sensor board connector — to the PCB.
Assigns SPI, I2C, 3.3V, 5V, and GND nets to its pins.

Pin map:
  1  3.3V        2  GND
  3  5V          4  GND
  5  SPI_MOSI    6  SPI_MISO
  7  SPI_SCLK    8  SPI_CS0
  9  I2C_SDA    10  I2C_SCL

Run from KiCad scripting console:
  exec(open('/home/zach/Documents/pi-dash/hardware/pi-dash-input-hat/add_j4.py').read())
"""
import pcbnew

BOARD_FILE = '/home/zach/Documents/pi-dash/hardware/pi-dash-input-hat/pi-dash-input-hat.kicad_pcb'
FP_LIB     = '/snap/kicad/22/usr/share/kicad/footprints/Connector_PinHeader_2.54mm.pretty'
FP_NAME    = 'PinHeader_2x05_P2.54mm_Vertical'

board = pcbnew.LoadBoard(BOARD_FILE)

# ── Load and place footprint ──────────────────────────────────────────────
fp = pcbnew.FootprintLoad(FP_LIB, FP_NAME)
fp.SetReference('J4')
fp.SetValue('Sensor_Connector')

# Place on bottom-left of board, near bottom edge, away from H3 (3.5,53)
fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(25), pcbnew.FromMM(49)))
board.Add(fp)

# ── Net assignment ────────────────────────────────────────────────────────
_net_cache = {}

def get_net(name):
    if name in _net_cache:
        return _net_cache[name]
    net = board.FindNet(name)
    if not net:
        net = pcbnew.NETINFO_ITEM(board, name)
        board.Add(net)
    _net_cache[name] = net
    return net

pin_nets = {
    '1': '+3V3',
    '2': 'GND',
    '3': '+5V',
    '4': 'GND',
    '5': 'GPIO10',   # SPI MOSI
    '6': 'GPIO9',    # SPI MISO
    '7': 'GPIO11',   # SPI SCLK
    '8': 'GPIO8',    # SPI CS0
    '9': 'GPIO2',    # I2C SDA
    '10': 'GPIO3',   # I2C SCL
}

for pad in fp.Pads():
    net_name = pin_nets.get(pad.GetNumber())
    if net_name:
        pad.SetNet(get_net(net_name))
        print(f"  J4 pin {pad.GetNumber()} → {net_name}")

board.Save(BOARD_FILE)
print("Done — J4 added at (25, 49). Open in KiCad and route the ratsnest connections.")
