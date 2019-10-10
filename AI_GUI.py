# -*- coding:utf-8 -*-
# Author:Yuntian

# 程序接口说明
# bf_PhantomGo：主程序传入(x,y)坐标，棋盘可视化棋子，并在显示框中显示坐标
# bf_illegal：裁判指出illegal，返回信息至主程序
# 提子：左键单击要提取的棋子即可

from absl import app
from tkinter import *
from tkinter.messagebox import *

from Ghost1 import Ghost

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
