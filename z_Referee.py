""" 幻影围棋裁判 by LiuYiGuang """

from go import Position
import numpy as np

class Referee():
    def __init__(self):
        self.go = Position(n=9,komi=3.25)

    def action(self,coord):
        """ 
        输入：落子坐标
        输出：是否合法，提子列表，胜负(0:未决出胜负，1:胜，-1:负)
        """

        # 判断是否pass
        if coord == [-1,-1]:
            self.go = self.go.pass_move()

            # 检查胜负情况
            winner = 0
            if self.go.is_game_over():
                winner = self.go.result()
                print(self.go.result_string())

            return [True,[],winner]

        # 检查是否合法
        if not self.go.is_move_legal(tuple(coord)):
            return (False,[],0)

        # 棋盘信息备份
        preBoard = self.go.board.copy()
        preBoard[coord[0],coord[1]] = 1

        # 落子
        self.go = self.go.play_move(tuple(coord))

        # 检查是否提子，若提子则存储提子信息到列表
        absDiff = np.abs(preBoard) - np.abs(self.go.board)
        takes = np.transpose(np.nonzero(absDiff))

        return (True,takes,0)
