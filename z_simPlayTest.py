from go import Position
import numpy as np

go = Position(n=9)

go = go.play_move(tuple([1,2]))
print(go)

go = go.play_move((1,3))
print(go)

go = go.play_move((0,3))
print(go)

go = go.play_move((5,6))
print(go)

go = go.play_move((1,4))
print(go)

go = go.play_move((5,7))
print(go)

preBoard = go.board.copy()
coord = (2,3)
preBoard[coord[0],coord[1]] = 1
print(preBoard)

go = go.play_move((2,3))
print(go)

print(go.board)

print('is_move_legal:',go.is_move_legal(tuple([1,3])))

absdiff = np.abs(preBoard)-np.abs(go.board)
print(absdiff)

absdiff[8,8] = 1

takes = np.nonzero(absdiff)

print(np.transpose(takes))