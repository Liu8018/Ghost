from absl import app
from z_Ghost import Ghost

def main(argv):
    g = Ghost(-1)

    action = g.action()
    print('action 0:',action)

    g.on_legalInfo(True)

    action = g.action()
    print('action 1:', action)

    action = g.on_legalInfo(False)

    g.on_legalInfo(True)
    print('action 2:', action)
    g.on_takeInfo([[3, 3]])

    g.on_legalInfo(True)

    action = g.action()
    print('action 3:', action)

    g.on_legalInfo(True)

    action = g.action()
    print('action 4:', action)

    print('finish')


if __name__ == '__main__':
    app.run(main)
