from absl import app
import numpy as np
from Ghost import Ghost
from Referee import Referee
import random

basePb = np.array([1,2,3,4,5,4,3,2,1],dtype=float)
basePb = basePb / basePb.sum()
axis = np.array([0,1,2,3,4,5,6,7,8],dtype=int)

def main(argv):
    referee = Referee()

    colorList = [-1,1]
    ghost_color = colorList[random.randint(0,1)]
    ghost = Ghost(ghost_color)

    print('Ghost color:',ghost_color)
    print('Random player color:',-ghost_color)

    num_move = 0

    while True:
        print(referee.go)

        winner = 0

        if -(num_move%2-0.5)*2 == ghost.color:
            print("Ghost's turn")

            action = ghost.action()
            is_legal, takes, winner = referee.action(action)
            while not is_legal:
                print('Ghost try:',action)
                action = ghost.on_legalInfo(is_legal)
                is_legal, takes, winner = referee.action(action)

            print('action:', action)

            if len(takes):
                print('Ghost takes:\n', takes)

            ghost.on_legalInfo(True)
            ghost.on_takeInfo(takes)

        else:
            print("Random player's turn")

            action = [int(np.random.choice(axis,1,p=basePb)), int(np.random.choice(axis,1,p=basePb))]

            is_legal, takes, winner = referee.action(action)
            num_try = 0
            while not is_legal:
                action = [int(np.random.choice(axis, 1, p=basePb)), int(np.random.choice(axis, 1, p=basePb))]
                is_legal, takes, winner = referee.action(action)
                num_try += 1
                if num_try > 80:
                    action = [-1,-1]    # pass的情况
                    is_legal, takes, winner = referee.action(action)
                    break

            print('action:', action)

            if len(takes):
                print('Random player takes:\n',takes)

                # 告知ghost被提子信息
                ghost.on_takeInfo(takes)

        if winner == ghost_color:
            print('Ghost wins!')
            exit(0)
        if winner == -ghost_color:
            print('Random player wins!')
            exit(0)

        num_move += 1


if __name__ == '__main__':
    app.run(main)
