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
        self.illegalBoard = np.zeros((9,9),int)
        self.num_oppStones = 0    # 对手棋子总数

        if color == -1:
            self.num_oppStones = 1

        self.scoreNet = dual_net.DualNetwork(modelDir)    # 计算落子得分的网络

        self.board_flat_idx = np.array([idx for idx in range(81)])

        # 空间位置概率
        self.basePb = np.array([1, 2, 1, 2, 1, 2, 1, 2, 1,
                               2, 1, 2, 2, 2, 2, 2, 1, 2,
                               1, 2, 3, 3, 3, 3, 3, 2, 1,
                               2, 2, 3, 4, 4, 4, 3, 2, 2,
                               1, 2, 3, 4, 5, 4, 3, 2, 1,
                               2, 2, 3, 4, 4, 4, 3, 2, 2,
                               1, 2, 3, 3, 3, 3, 3, 2, 1,
                               2, 1, 2, 2, 2, 2, 2, 1, 2,
                               1, 2, 1, 2, 1, 2, 1, 2, 1], dtype=float)
        self.basePb = self.basePb
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
                self.board_opp_known[qi[0],qi[1]] += 5000

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
        if not pb.sum():
            return
        pb = pb / pb.sum()

        for t in range(800):
            tmpPb = pb.copy()

            tmpGo = Position(n=9, board=self.board_selfNow, to_play=-self.color)

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

            # 对手的最后一次落子
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

