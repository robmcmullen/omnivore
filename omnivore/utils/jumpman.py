import numpy as np

class JumpmanLevelBuilder(object):
    def __init__(self, segments):
        self.segments = segments

    def clear_screen(self, screen):
        screen[:] = 0

    def draw_commands(self, screen, commands):
        self.clear_screen(screen)
        x = y = dx = dy = num = 0
        addr = None
        index = 0
        last = len(commands)
        while index < last:
            c = commands[index]
            print "index=%d, command=%x" % (index, c)
            index += 1
            if c < 0xfb:
                if addr is not None:
                    self.draw(addr, x, y, dx, dy, c)
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
                    dx = arg1
                    dy = arg2
                elif c == 0xff:
                    return

    def draw(self, addr, x, y, dx, dy, repeat):
        print "addr=%x x=%d y=%d dx=%d dy=%d, num=%d" % (addr, x, y, dx, dy, repeat)
        codes = self.get_object_code(addr)
        if codes is None:
            return
        print "  found codes:", codes
        index = 0
        last = len(codes)
        while index < last:
            prefix = list(codes[index:index + 3])
            if len(prefix) < 3:
                if prefix[0] != 0xff:
                    print "  short prefix", prefix
                return
            n, xoffset, yoffset = prefix
            index += 3
            pixels = list(codes[index:index + n])
            if len(pixels) < n:
                print "  %d pixels expected, %d found" % (n, len(pixels))
                return
            print "pixels: n=%d x=%d y=%d pixels=%s" % (n, xoffset, yoffset, pixels)
            index += n



    def get_object_code(self, addr):
        for s in self.segments:
            index = addr - s.start_addr
            if s.is_valid_index(index):
                codes = s[index:]
                end = np.nonzero(codes==255)[0]
                print end
                if len(end) > 0:
                    print end
                    end = end[0] + 1
                else:
                    continue
                codes = s[index:index + end]
                return codes

