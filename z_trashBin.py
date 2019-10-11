"""幻影围棋AI by LiuYiGuang"""

import numpy as np
from go import Position
from go import is_koish
import dual_net
# from strategies import MCTSPlayer
import utils
# import threading
import shelve
from contextlib import closing


modelDir = './models/000496/v3-9x9_models_000496-polite-ray-upgrade'


class Ghost():
    def __init__(self, color, buffer = None):
        self.color = color    # 己方棋子颜色（先后手信息），1:黑，-1:白

        self.board_selfNow = np.zeros((9,9),int)    # 己方当前棋面
        self.board_opp_known = np.zeros((9,9),int)    # 已知的对手棋盘信息（不包含历史信息）
        self.board_sims = []    # 模拟出的完全信息棋盘
        self.tryAction = []
        self.prevAction = []
        self.illegalBoard = np.zeros((9,9),int)
        self.num_oppStones = 0    # 对手棋子总数

        if color == -1:
            self.num_oppStones = 1

        self.scoreNet = dual_net.DualNetwork(modelDir)    # 计算落子得分的网络

        self.board_flat_idx = np.array([idx for idx in range(81)])

        # 空间位置概率
        self.basePb = np.array([1, 1, 1, 1, 1, 1, 1, 1, 1,
                               1, 2, 2, 2, 2, 2, 2, 2, 1,
                               1, 2, 3, 3, 3, 3, 3, 2, 1,
                               1, 2, 3, 4, 4, 4, 3, 2, 1,
                               1, 2, 3, 4, 5, 4, 3, 2, 1,
                               1, 2, 3, 4, 4, 4, 3, 2, 1,
                               1, 2, 3, 3, 3, 3, 3, 2, 1,
                               1, 2, 2, 2, 2, 2, 2, 2, 1,
                               1, 1, 1, 1, 1, 1, 1, 1, 1], dtype=float)
        self.basePb = self.basePb / 3
        self.basePb = np.reshape(self.basePb, (9, 9))

        # 复盘时用
        if buffer is not None:
            with closing(shelve.open(buffer,'r')) as shelf:
                self.color = shelf['color']
                self.board_selfNow = shelf['board_selfNow']
                self.board_opp_known = shelf['board_opp_known']
                self.num_oppStones = shelf['num_oppStones']


    def action(self):
        """计算落子并返回坐标"""

        # 1、模拟完全信息棋面
        with utils.logged_timer("simulation"):
            self.board_sims = []
            self.simOppLatest()

        print('num_sims: ',len(self.board_sims))

        #print('one of sim:\n',self.board_sims[-1])

        if len(self.board_sims) == 0:
            # 若模拟对手棋面失败，仅输入己方棋面信息
            tmpGo = Position(n=9,board=self.board_selfNow,to_play=self.color)
            self.board_sims.append(tmpGo)

        # 2、计算每个可行位置的总得分
        with utils.logged_timer("calculation"):
            pbs,vs = self.scoreNet.run_many(self.board_sims)
            scoreBoard = np.sum(pbs,axis=0)

        # 自己的位置得分设为零
        selfPlaces = np.transpose(np.nonzero(self.board_selfNow))
        for sp in selfPlaces:
            scoreBoard[sp[0]*9+sp[1]] = 0

        # 自己内部的气不准下
        board_innerQi = self.findInnerQi()
        scoreBoard.flat[[i for (i, x) in enumerate(board_innerQi.flat) if x == 1]] = 0

        # illegal的位置得分设为零
        scoreBoard.flat[[i for (i, x) in enumerate(self.illegalBoard.flat) if x == 1]] = 0

        # 不主动pass
        scoreBoard = scoreBoard[:81]

        #print('scoreBoard:\n',scoreBoard)

        # pass的情况
        if scoreBoard.sum() == 0:
            action = [-1, -1]
            self.tryAction = action
        else:
            flatMaxIdx = np.argmax(scoreBoard)
            action = [int(flatMaxIdx/9), int(flatMaxIdx%9)]
            self.tryAction = action

        with closing(shelve.open('buffer', 'c')) as shelf:
            shelf['color'] = self.color
            shelf['board_selfNow'] = self.board_selfNow
            shelf['board_opp_known'] = self.board_opp_known
            shelf['num_oppStones'] = self.num_oppStones

        return action

    def on_legalInfo(self, is_legal):
        """
        上一步落子合法时，更新board_opp_known和己方棋面信息，以及对手棋子总数
        上一步落子不合法时，更新board_opp_known，再action一次
        """
        if is_legal:
            self.illegalBoard = np.zeros((9,9),int)

            if self.tryAction == [-1,-1]:    # 上一步自己pass的情况
                return

            self.board_selfNow[self.tryAction[0], self.tryAction[1]] = self.color
            self.board_opp_known[self.tryAction[0], self.tryAction[1]] = 0
            self.num_oppStones += 1

            self.prevAction = [self.tryAction[0], self.tryAction[1]]
        else:
            self.board_opp_known[self.tryAction[0], self.tryAction[1]] += 80
            self.illegalBoard[self.tryAction[0], self.tryAction[1]] = 1
            return self.action()

    def on_takeInfo(self, takes):
        """
        提子时，更新对手棋子总数和board_known
        被提子时，更新己方棋面
        """
        if len(takes) == 0:
            return

        if self.board_selfNow[takes[0][0],takes[0][1]] == self.color:    # 被提子
            # 周围的气设成对手棋子
            qis = []
            for t in range(len(takes)):
                r = takes[t][0]
                c = takes[t][1]
                tmpQis = [[r-1,c],[r+1,c],[r,c-1],[r,c+1]]
                for tmpQi in tmpQis:
                    if tmpQi[0] >= 0 and tmpQi[0] <=8 and tmpQi[1] >= 0 and tmpQi[1] <= 8 and self.board_selfNow[tmpQi[0],tmpQi[1]] != self.color:
                        qis.append(tmpQi)
            for qi in qis:
                self.board_opp_known[qi[0],qi[1]] += 100

            # 提子位置设为无棋子状态
            for t in range(len(takes)):
                self.board_selfNow[takes[t][0],takes[t][1]] = 0

        else:    # 提对方的子
            # 对手棋子数减少
            self.num_oppStones -= len(takes)
            # 提子位置设为无棋子状态
            for t in range(len(takes)):
                self.board_opp_known[takes[t][0], takes[t][1]] = 0


    # ------------------------------------------------------------

    def findInnerQi(self):
        """找到内部的、且不可能被对手占据的气"""
        board_innnerQi = np.zeros((9,9),int)
        for r in range(9):
            for c in range(9):
                # 判定是否为eye
                if is_koish(self.board_selfNow,(r,c)) != self.color:
                    continue

                # 是否可能被占据
                J = [[r-1,c-1], [r-1,c+1], [r+1,c+1], [r+1,c-1]]
                is_side = False
                A = 0
                for j in J:
                    if j[0] >= 0 and j[0] <=8 and j[1] >= 0 and j[1] <= 8:
                        if self.board_selfNow[j[0],j[1]] != self.color and is_koish(self.board_selfNow,(j[0],j[1])) != self.color:
                            A += 1
                    else:
                        is_side = True

                if A >= 2 or (is_side and A):
                    continue

                board_innnerQi[r,c] = 1

        return board_innnerQi

    def simOppLatest(self):
        """ 从对手的上一步落子开始模拟，在此之前的直接随机抽样，不记录中间过程 """
        pb = self.board_opp_known.copy()
        pb.astype(float)
        pb = pb + self.basePb

        # 判断对手棋子总数上限，num_oppStones不能大于上限
        board_innerQi = self.findInnerQi()
        num_oppStoneUpperLimit = 81 - len(np.transpose(np.nonzero(self.board_selfNow))) - len(np.transpose(np.nonzero(board_innerQi)))
        if self.num_oppStones > num_oppStoneUpperLimit:
            self.num_oppStones = num_oppStoneUpperLimit

        # 对手不可能在我方落子处或我方eye处有落子
        pb.flat[[i for (i, x) in enumerate(self.board_selfNow.flat) if x == self.color]] = 0
        pb.flat[[i for (i, x) in enumerate(board_innerQi.flat) if x == 1]] = 0
        pb = pb / pb.sum()

        # 是否模拟自己的最后一次落子
        flag_simSelfLatest = False
        board_selfPrev = self.board_selfNow.copy()
        if self.prevAction != [] and self.board_selfNow[self.prevAction[0], self.prevAction[1]] == self.color:
            flag_simSelfLatest = True
            board_selfPrev[self.prevAction[0], self.prevAction[1]] = 0

        for t in range(200):
            tmpPb = pb.copy()

            tmpGo = Position(n=9, board=board_selfPrev, to_play=-self.color)

            # 对手落子
            for i in range(self.num_oppStones - 1):
                for ntry in range(5):
                    flatIdx = np.random.choice(self.board_flat_idx, 1, p=tmpPb.flat)
                    action_opp = (int(flatIdx / 9), int(flatIdx % 9))

                    if not tmpGo.is_move_legal(action_opp):
                        continue

                    preBoard = tmpGo.board.copy()
                    preBoard[action_opp[0], action_opp[1]] = 1
                    tmpGo_sub = tmpGo.play_move(action_opp)
                    absDiff = np.abs(preBoard) - np.abs(tmpGo_sub.board)
                    if len(np.transpose(np.nonzero(absDiff))):
                        continue

                    tmpGo = tmpGo_sub
                    tmpGo.to_play = -self.color

                    tmpPb.flat[flatIdx] = 0
                    tmpPb = tmpPb / tmpPb.sum()
                    break

            # 我方最后一次落子
            if flag_simSelfLatest:
                tmpGo.to_play = self.color
                if not tmpGo.is_move_legal(tuple(self.prevAction)):
                    continue
                tmpGo = tmpGo.play_move(tuple(self.prevAction))

            # 对手的最后一次落子
            for q in range(20):
                flatIdx = np.random.choice(self.board_flat_idx, 1, p=tmpPb.flat)
                action_opp = (int(flatIdx / 9), int(flatIdx % 9))

                if not tmpGo.is_move_legal(action_opp):
                    continue

                preBoard = tmpGo.board.copy()
                preBoard[action_opp[0], action_opp[1]] = 1
                tmpGo = tmpGo.play_move(action_opp)
                absDiff = np.abs(preBoard) - np.abs(tmpGo.board)
                if len(np.transpose(np.nonzero(absDiff))):
                    continue
                else:
                    self.board_sims.append(tmpGo)
                    break

        """
        # 记得加多线程

        def simTrd(trdId):
            trdId = int(trdId)
            num_suc = 0
            for t in range(200):
                tmpPb = pb.copy()

                tmpGo = Position(n=9, board=self.board_selfNow, to_play=-self.color)

                for i in range(self.num_oppStones - 1):
                    for ntry in range(5):
                        flatIdx = np.random.choice(self.board_flat_idx, 1, p=tmpPb.flat)
                        action_opp = (int(flatIdx / 9), int(flatIdx % 9))

                        if not tmpGo.is_move_legal(action_opp):
                            continue

                        preBoard = tmpGo.board.copy()
                        preBoard[action_opp[0], action_opp[1]] = 1
                        tmpGo_sub = tmpGo.play_move(action_opp)
                        absDiff = np.abs(preBoard) - np.abs(tmpGo_sub.board)
                        if len(np.transpose(np.nonzero(absDiff))):
                            continue

                        tmpGo = tmpGo_sub
                        tmpGo.to_play = -self.color

                        tmpPb.flat[flatIdx] = 0
                        tmpPb = tmpPb / tmpPb.sum()
                        break

                for q in range(10):
                    flatIdx = np.random.choice(self.board_flat_idx, 1, p=tmpPb.flat)
                    action_opp = (int(flatIdx / 9), int(flatIdx % 9))

                    if not tmpGo.is_move_legal(action_opp):
                        continue

                    preBoard = tmpGo.board.copy()
                    preBoard[action_opp[0], action_opp[1]] = 1
                    tmpGo = tmpGo.play_move(action_opp)
                    absDiff = np.abs(preBoard) - np.abs(tmpGo.board)
                    if len(np.transpose(np.nonzero(absDiff))):
                        continue
                    else:
                        # self.tmpSims[trdId].append(tmpGo)
                        self.tmpSims[trdId*200+num_suc, :, :] = tmpGo.board
                        num_suc += 1
                        break
            self.tmpSims_numPerTrd[trdId] = num_suc

        threads = []
        for i in range(4):
            t = threading.Thread(target=simTrd, args=(str(i)))
            threads.append(t)
            t.start()
        for t in threads:
            t.join()

        for i in range(4):
            self.board_sims = self.board_sims + self.tmpSims

        self.board_sims = self.tmpSims[0] + self.tmpSims[1] + self.tmpSims[2] + self.tmpSims[3]
        self.tmpSims = [[], [], [], []]
        """

# --------------------------------------------------------------------------------------------------------------------

# -*- coding:utf-8 -*-
# Author:Yuntian

# 程序接口说明
# bf_PhantomGo：主程序传入(x,y)坐标，棋盘可视化棋子，并在显示框中显示坐标
# bf_illegal：裁判指出illegal，返回信息至主程序
# 提子：左键单击要提取的棋子即可

from absl import app
from tkinter import *
from tkinter.messagebox import *

from Ghost import Ghost
import numpy as np
from go import find_reached

class Chess(object):

    def __init__(self):
        #############
        #   param   #
        #######################################
        self.row, self.column = 9, 9
        self.mesh = 50.1
        self.ratio = 0.9
        self.board_color = "#CDBA96"
        self.header_bg = "#CDC0B0"
        self.btn_font = ("黑体", 15, "bold")
        self.step = self.mesh / 2
        self.chess_r = self.step * self.ratio
        # 设置棋盘网格交点的半径
        self.point_r = self.step * 0.15
        # create the matrix
        self.matrix = [[0 for y in range(self.column)] for x in range(self.row)]
        self.is_start = False
        self.is_chess = True
        self.last_p = None
        self.text = ''
        self.takechess_storage = []
        self.state = 0

        ###########
        #   GUI   #
        #######################################
        self.root = Tk()

        self.root.title("幻影围棋")
        self.root.resizable(width=False, height=False)
        self.label = Label(self.root, text=self.text,
                     width=45, height=1, font=self.btn_font, bg='#eae2d2')
        self.label.pack()

        # 定义放置按钮与标签的父框
        self.f_header = Frame(self.root, highlightthickness=0, bg=self.header_bg)
        self.f_header.pack(fill=BOTH, ipadx=10)
        self.BOTTOM_operation = Frame(self.root, highlightthickness=0, bg=self.header_bg)
        self.BOTTOM_operation.pack(fill=BOTH, side=BOTTOM, ipadx=10)

        # 定义按钮与标签
        # parameter state
        self.b_initial = Button(self.f_header, text="初始化", command=self.bf_initial, font=self.btn_font)
        self.b_takechess = Button(self.f_header, text="提子", command=self.bf_takechess_start, font=self.btn_font)
        self.b_takechess_end = Button(self.f_header, text="提子结束", command=self.bf_takechess_end, font=self.btn_font)
        self.b_PhantomGo = Button(self.BOTTOM_operation, text="下棋", command=self.cf_board, font=self.btn_font)

        # 调整按钮与标签的位置
        self.b_initial.pack(side=LEFT, padx=50)
        self.b_takechess.pack(side=RIGHT, padx=50)
        self.b_takechess_end.pack(side=BOTTOM)
        self.b_PhantomGo.pack(side=BOTTOM)

        self.c_chess = Canvas(self.root, bg=self.board_color, width=(self.column + 1) * self.mesh,
                              height=(self.row + 1) * self.mesh, highlightthickness=0)
        self.c_chess.bind("<Button-1>", self.bf_takechess)
        self.c_chess.pack()

        self.root.mainloop()

    # x, y遵循二维数组索引
    def draw_mesh(self, x, y):
        # 倍率
        ratio = (1 - self.ratio) * 0.99 + 1
        center_x, center_y = self.mesh * (x + 1), self.mesh * (y + 1)
        # 先画背景色
        self.c_chess.create_rectangle(center_y - self.step, center_x - self.step,
                                      center_y + self.step, center_x + self.step,
                                      fill=self.board_color, outline=self.board_color)
        # 画网格线
        a, b = [0, ratio] if y == 0 else [-ratio, 0] if y == self.row - 1 else [-ratio, ratio]
        c, d = [0, ratio] if x == 0 else [-ratio, 0] if x == self.column - 1 else [-ratio, ratio]
        self.c_chess.create_line(center_y + a * self.step, center_x, center_y + b * self.step, center_x)
        self.c_chess.create_line(center_y, center_x + c * self.step, center_y, center_x + d * self.step)

    # 画x行y列处的棋子，color指定棋子颜色
    def draw_chess(self, x, y, color):
        center_x, center_y = self.mesh * (x + 1), self.mesh * (y + 1)
        # 画圆可视化棋子
        self.c_chess.create_oval(center_y - self.chess_r, center_x - self.chess_r,
                                 center_y + self.chess_r, center_x + self.chess_r,
                                 fill=color)

    # 画整个棋盘
    def draw_board(self):
        # list generated
        [self.draw_mesh(x, y) for y in range(self.column) for x in range(self.row)]

    # 设置各组件，变量的状态，初始化matrix，初始化棋盘，初始化信息
    def bf_initial(self):
        self.is_start = True
        self.is_chess = False
        self.matrix = [[0 for y in range(self.column)] for x in range(self.row)]
        self.draw_board()
        for i in range(9):
            self.c_chess.create_text(485, 55+i*49, text=9-i, font=self.btn_font)
        for j in range(9):
            self.c_chess.create_text(52+j*50, 485, text=chr(ord('A')+j), font=self.btn_font)
        for i in range(9):
            self.c_chess.create_text(15, 55+i*49, text=i, font=self.btn_font)
        for j in range(9):
            self.c_chess.create_text(52+j*50, 15, text=j, font=self.btn_font)


        color_info = askquestion("确定我方先后手", "先手？")
        color = 0
        if color_info == 'yes':
           color = 1
        else:
           color = -1
        self.ghost = Ghost(color)


        """
        # 复盘时用
        self.ghost = Ghost(1, 'buffer')

        stoneList = np.transpose(np.nonzero(self.ghost.board_selfNow))

        color = "black" if self.ghost.color == 1 else "white"
        for stone in stoneList:
            x = stone[0]
            y = stone[1]
            self.draw_chess(x, y, color)
            self.last_p = [x, y]
            self.label['text'] = '(' + str(9 - x) + ', ' + chr(ord('A') + y) + ')' + '    ' + '(' + str(x) + ', ' + str(y) + ')'
        """

    # 程序接口
    def bf_takechess_start(self):
        self.state = 1
        return self.state

    # 程序接口
    def bf_takechess_end(self):
        print(self.takechess_storage)
        self.ghost.on_takeInfo(self.takechess_storage)
        self.takechess_storage = []
        self.state = 0

    # 用网格覆盖掉棋子，操作相应变量，matrix[x][y]置空
    def bf_takechess(self, click):
        if self.state:
            # 找到离点击点最近的坐标
            x, y = int((click.y - self.step) / self.mesh), int((click.x - self.step) / self.mesh)
            # 找到该坐标的中心点位置
            center_x, center_y = self.mesh * (x + 1), self.mesh * (y + 1)
            # 计算点击点到中心的距离
            distance = ((center_x - click.y) ** 2 + (center_y - click.x) ** 2) ** 0.5
            # 如果距离不在规定的圆内，退出//如果这个位置已经有棋子，退出//如果游戏还没开始，退出
            # 双方子皆可被提出
            if distance > self.step * 0.95:
                return
            self.draw_mesh(x, y)
            self.matrix[x][y] = 0
            self.takechess_storage.append([x, y])
        return self.takechess_storage

    # 程序接口
    def bf_PhantomGo(self):
        action = self.ghost.action()
        return action[0], action[1]

    def cf_board(self):
        x, y = self.bf_PhantomGo()
        self.cf_board_input(x,y)

    def cf_board_input(self, x, y):
        if (x == -1) and (y == -1):
            self.label['text'] = 'pass'
            return 0
        else:
            # 此时棋子的颜色，和matrix中该棋子的标识。
            color = "black" if self.ghost.color == 1 else "white"
            # tag = self.bf_color(1, -1)
            # 先画棋子，在修改matrix相应点的值，用last_p记录本次操作点
            self.draw_chess(x, y, color)
            # self.matrix[x][y] = tag
            self.last_p = [x, y]
            self.label['text'] = '(' + str(9-x) + ', ' + chr(ord('A')+y) + ')'+ '    '+'(' + str(x) + ', ' + str(y) + ')'
            legal_info = askquestion("判定合法情况", "legal？")
            if legal_info == 'yes':
                self.ghost.on_legalInfo(True)
            else:
                x, y = self.last_p
                self.draw_mesh(x, y)
                self.matrix[x][y] = 0
                self.last_p = None
                action = self.ghost.on_legalInfo(False)
                self.cf_board_input(action[0],action[1])

    def bf_color(self, true, false):
        return true if self.is_chess else false

def main(argv):
    Chess()

if __name__ == '__main__':
    app.run(main)
