from absl import app
import numpy as np
from Ghost1 import Ghost as Ghost1
from Ghost import Ghost as Ghost2
from Referee import Referee
import random

def main(argv):
    # 记录两方胜局数
    num_vs = int(argv[1])
    num_g1win = 0
    num_g2win = 0

    for vsIdx in range(num_vs):
        referee = Referee()

        colorList = [-1, 1]
        ghost1_color = colorList[random.randint(0, 1)]
        ghost1 = Ghost1(ghost1_color)

        ghost2 = Ghost2(-ghost1_color)

        print('Ghost1 color:', ghost1_color)
        print('Ghost2 color:', -ghost1_color)

        num_move = 0

        while True:
            print('g1win:', num_g1win, ' ', 'g2win:', num_g2win)
            print(referee.go)

            winner = 0

            if -(num_move%2-0.5)*2 == ghost1.color:
                print("Ghost1's turn")

                action = ghost1.action()
                is_legal, takes, winner = referee.action(action)
                while not is_legal:
                    print('Ghost1 try:',action)
                    action = ghost1.on_legalInfo(is_legal)
                    is_legal, takes, winner = referee.action(action)

                print('action:', action)

                if len(takes):
                    print('Ghost1 takes:\n', takes)

                ghost1.on_legalInfo(True)

                # 告知双方提子信息
                ghost1.on_takeInfo(takes)
                ghost2.on_takeInfo(takes)

            else:
                print("Ghost2's turn")

                action = ghost2.action()
                is_legal, takes, winner = referee.action(action)
                while not is_legal:
                    print('Ghost2 try:', action)
                    action = ghost2.on_legalInfo(is_legal)
                    is_legal, takes, winner = referee.action(action)

                print('action:', action)

                if len(takes):
                    print('Ghost2 takes:\n', takes)

                ghost2.on_legalInfo(True)

                # 告知双方提子信息
                ghost2.on_takeInfo(takes)
                ghost1.on_takeInfo(takes)

            if winner == ghost1_color:
                print('Ghost1 wins!')
                num_g1win += 1
                break
            if winner == -ghost1_color:
                print('Ghost2 wins!')
                num_g2win += 1
                break

            num_move += 1


if __name__ == '__main__':
    app.run(main)
