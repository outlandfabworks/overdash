import pcbnew
board = pcbnew.GetBoard()
fp = board.FindFootprintByReference('U9')
fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(87), pcbnew.FromMM(17)))
board.Save(board.GetFileName())
pcbnew.Refresh()
print("U9 moved to (87, 17)")
