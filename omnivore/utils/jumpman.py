import numpy as np

import logging
log = logging.getLogger(__name__)

class JumpmanLevelBuilder(object):
    def __init__(self, segments):
        self.segments = segments

    def draw_commands(self, screen, commands, current_segment=None):
        self.clear_object_code_cache()
        x = y = dx = dy = num = 0
        addr = None
        index = 0
        commands = np.array(commands, dtype=np.uint8)
        last = len(commands)
        while index < last:
            c = commands[index]
            log.debug("index=%d, command=%x" % (index, c))
            index += 1
            if c < 0xfb:
                if addr is not None:
                    self.draw_codes(screen, addr, x, y, dx, dy, c, current_segment)
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
                    dx = int(np.int8(arg1))  # signed!
                    dy = int(np.int8(arg2))
                elif c == 0xff:
                    return

    def draw_codes(self, screen, addr, x, y, dx, dy, repeat, current_segment):
        log.debug("addr=%x x=%d y=%d dx=%d dy=%d, num=%d" % (addr, x, y, dx, dy, repeat))
        codes = self.get_object_code(addr, current_segment)
        if codes is None:
            return
        log.debug("  found codes: %s" % str(codes))
        index = 0
        last = len(codes)
        lines = []
        while index < last:
            prefix = codes[index:index + 3]
            if len(prefix) < 3:
                if prefix[0] != 0xff:
                    log.warning("  short prefix: %s" % str(prefix))
                break
            n , xoffset, yoffset = prefix.view(dtype=np.int8)
            index += 3
            pixels = list(codes[index:index + n])
            if len(pixels) < n:
                log.debug("  %d pixels expected, %d found" % (n, len(pixels)))
                return
            log.debug("pixels: n=%d x=%d y=%d pixels=%s" % (n, xoffset, yoffset, pixels))
            lines.append((n, xoffset, yoffset, pixels))
            index += n

        for i in range(repeat):
            for n, xoffset, yoffset, pixels in lines:
                for i, c in enumerate(pixels):
                    self.draw_pixel(screen, x + xoffset + i, y + yoffset, c)
            x += dx
            y += dy

    bit_offset = [6, 4, 2, 0]
    mask = [0b00111111, 0b11001111, 0b11110011, 0b11111100]

    def draw_pixel(self, screen, x, y, color):
        x_byte, x_bit = divmod(x, 4)
        color = color << self.bit_offset[x_bit]
        index = y * 40 + x_byte
        if index < 0 or index > len(screen):
            return
        screen[index] &= self.mask[x_bit]
        screen[index] |= color

    def clear_object_code_cache(self):
        self.object_code_cache = {}

    def get_object_code(self, addr, current_segment):
        if addr in self.object_code_cache:
            return self.object_code_cache[addr]
        search_order = []
        if current_segment is not None:
            search_order.append(current_segment)
        search_order.extend(self.segments)
        for s in search_order:
            log.debug("checking segment %s for object code %x" % (s.name, addr))
            index = addr - s.start_addr
            if s.is_valid_index(index):
                codes = s[index:]

                # get codes up to first 255
                end = np.nonzero(codes==255)[0]
                if len(end) > 0:
                    end = end[0] + 1
                else:
                    # skip to next segment
                    continue
                codes = s[index:index + end]
                self.object_code_cache[addr] = codes
                return codes

