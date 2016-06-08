import numpy as np

class JumpmanLevelBuilder(object):
    def __init__(self, screen, source):
        self.screen = screen
        self.clear_screen()
        self.parse_commands(source)

    def clear_screen(self):
        self.screen[:] = 0

    def parse_commands(self, commands):
        x = y = deltax = deltay = num = 0
        addr = None
        index = 0
        last = len(commands)
        while index < last:
            c = commands[index]
            index += 1
            if c < 0xfb:
                if index < last:
                    num = commands[index]
                    self.draw(addr, x, y, deltax, deltay, num)
                    index += 1
            elif index + 1 < last:
                arg1 = commands[index]
                arg2 = commands[index + 1]
                index += 2
                if c == 0xfc:
                    addr = arg2 * 256 + arg1
                elif c == 0xfd:
                    x = arg1
                    y = arg2
                elif c == 0xfe:
                    deltax = arg1
                    deltay = arg2
                elif c == 0xff:
                    return

    def draw(self, addr, x, y, deltax, deltay, num):
        pass

