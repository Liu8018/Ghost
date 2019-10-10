from absl import app
import numpy as np
from Ghost import Ghost
from Referee import Referee
import random

def main(argv):
    referee = Referee()

    colorList = [-1,1]
    ghost_color = colorList[random.randint(0,1)]
    ghost = Ghost(ghost_color)

    print('Ghost color:',ghost_color)
    print('Human player color:',-ghost_color)

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
            print("Human player's turn")

            action = input('Please input your move:')
            action = action.split(',')
            action = [int(action[0]), int(action[1])]

            is_legal, takes, winner = referee.action(action)
            while not is_legal:
                action = input('Illegal, please input again:')
                action = action.split(',')
                action = [int(action[0]), int(action[1])]
                is_legal, takes, winner = referee.action(action)

            print('action:', action)

            if len(takes):
                print('Human player takes:\n',takes)

                # 告知ghost被提子信息
                ghost.on_takeInfo(takes)

        if winner == ghost_color:
            print('Ghost wins!')
            exit(0)
        if winner == -ghost_color:
            print('Human player wins!')
            exit(0)

        num_move += 1


if __name__ == '__main__':
    app.run(main)
