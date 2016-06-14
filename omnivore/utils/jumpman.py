import numpy as np

from omnivore.utils.runtime import get_all_subclasses

import logging
log = logging.getLogger(__name__)
#log.setLevel(logging.DEBUG)


class JumpmanDrawObject(object):
    name = "object"
    default_addr = None
    default_dx = 4
    default_dy = 4
    vertical_only = False
    single = False

    def __init__(self, pick_index, x, y, count, dx=None, dy=None, addr=None):
        self.x = x
        self.y = y
        self.count = count
        self.addr = self.default_addr if addr is None else addr
        self.pick_index = pick_index
        self.dx = self.x_spacing if dx is None else dx
        self.dy = self.y_spacing if dy is None else dy
        self.trigger_function = None
        self.trigger_painting = None

    def __str__(self):
        extra = ""
        if self.trigger_function is not None:
            extra = " trigger_func=%x" % self.trigger_function
        if self.trigger_painting is not None:
            prefix = "\n  trigger_paint: "
            extra += prefix + prefix.join(str(obj) for obj in self.trigger_painting)
        return "draw %x x=%x y=%x dx=%d dy=%d count=%d%s" % (self.addr, self.x, self.y, self.dx, self.dy, self.count, extra)

    def update_table(self, state):
        pass

class Girder(JumpmanDrawObject):
    name = "girder"
    default_addr = 0x4000
    default_dy = 3

class Ladder(JumpmanDrawObject):
    name = "ladder"
    default_addr = 0x402c
    default_dx = 8
    vertical_only = True

    def update_table(self, state):
        state.add_ladder(self)

class UpRope(JumpmanDrawObject):
    name = "uprope"
    default_addr = 0x40af
    vertical_only = True

class DownRope(JumpmanDrawObject):
    name = "downrope"
    default_addr = 0x40c0
    vertical_only = True

    def update_table(self, state):
        state.add_downrope(self)

class Peanut(JumpmanDrawObject):
    name = "peanut"
    default_addr = 0x4083
    default_dy = 3
    single = True

class EraseGirder(JumpmanDrawObject):
    name = "girder_erase"
    default_addr = 0x4016

class EraseLadder(JumpmanDrawObject):
    name = "ladder_erase"
    default_addr = 0x4056

class EraseRope(JumpmanDrawObject):
    name = "rope_erase"
    default_addr = 0x40d1


class ScreenState(object):
    def __init__(self, segments, current_segment, screen, pick_buffer):
        self.object_code_cache = {}
        self.search_order = []
        self.current_segment = current_segment
        if current_segment is not None:
            self.search_order.append(current_segment)
        self.search_order.extend(segments)
        self.screen = screen
        self.pick_buffer = pick_buffer

        self.pick_dict = dict()
        self.ladder_positions = set()
        self.downrope_positions = set()

    def add_ladder(self, obj):
        self.ladder_positions.add(obj.x + 0x30)

    def add_downrope(self, obj):
        self.downrope_positions.add(obj.x + 0x2e)

    def draw_object(self, obj):
        if obj.addr is None:
            return
        log.debug("addr=%x x=%d y=%d dx=%d dy=%d, num=%d" % (obj.addr, obj.x, obj.y, obj.dx, obj.dy, obj.count))
        codes = self.get_object_code(obj.addr)
        if codes is None:
            return
        log.debug("  found codes: %s" % str(codes))
        index = 0
        last = len(codes)
        lines = []
        while index < last:
            prefix = codes[index:index + 3]
            if len(prefix) < 3:
                if len(prefix) == 0 or prefix[0] != 0xff:
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

        x = obj.x
        y = obj.y
        for i in range(obj.count):
            for n, xoffset, yoffset, pixels in lines:
                for i, c in enumerate(pixels):
                    px = x + xoffset + i
                    py = y + yoffset
                    if self.draw_pixel(px, py, c):
                        if self.pick_buffer is not None:
                            self.pick_buffer[px,py] = obj.pick_index
            x += obj.dx
            y += obj.dy
        self.pick_dict[obj.pick_index] = obj
        obj.update_table(self)

    bit_offset = [6, 4, 2, 0]
    mask = [0b00111111, 0b11001111, 0b11110011, 0b11111100]

    def draw_pixel(self, x, y, color):
        x_byte, x_bit = divmod(x, 4)
        color = color << self.bit_offset[x_bit]
        index = y * 40 + x_byte
        if index < 0 or index > len(self.screen):
            return False
        self.screen[index] &= self.mask[x_bit]
        self.screen[index] |= color
        return True

    def get_object_code(self, addr):
        if addr in self.object_code_cache:
            return self.object_code_cache[addr]
        for s in self.search_order:
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


class JumpmanLevelBuilder(object):
    def __init__(self, segments):
        self.segments = segments

    def parse_objects(self, data):
        x = y = dx = dy = count = 0
        addr = None
        objects = []
        data = np.array(data, dtype=np.uint8)
        last = len(data)
        index = 0
        while index < last:
            c = data[index]
            log.debug("index=%d, command=%x" % (index, c))
            pick_index = index
            index += 1
            command = None
            if c < 0xfb:
                if addr is not None:
                    obj = self.get_object(pick_index, x, y, c, dx, dy, addr)
                    objects.append(obj)
            elif c >= 0xfc and c <= 0xfe:
                arg1 = data[index]
                arg2 = data[index + 1]
                index += 2
                if c == 0xfc:
                    addr = arg2 * 256 + arg1
                elif c == 0xfd:
                    x = arg1
                    y = arg2
                else:
                    dx = int(np.int8(arg1))  # signed!
                    dy = int(np.int8(arg2))
            elif c == 0xff:
                last = 0  # force the end
        return objects

    def get_object(self, pick, x, y, c, dx, dy, addr):
        found = JumpmanDrawObject
        for kls in get_all_subclasses(JumpmanDrawObject):
            if kls.default_addr == addr:
                found = kls
                break
        return found(pick, x, y, c, dx, dy, addr)

    def parse_harvest_table(self, objects, origin, h):
        objmap = {(obj.x, obj.y):obj for obj in objects if obj.single}
        data = np.array(h, dtype=np.uint8)
        last = len(data)
        index = 0
        while index < last:
            c = data[index]
            if c == 0xff:
                break
            entry = data[index:index + 7]
            print "harvest entry: %s" % str(entry)
            try:
                obj = objmap[entry[1], entry[2]]
                obj.trigger_function = entry[3] + 256*entry[4]
                addr = entry[5] + 256*entry[6]
                if addr >= origin and addr <= origin + len(h):
                    obj.trigger_painting = self.parse_objects(h[addr - origin:])
                print obj
            except KeyError:
                log.error("Invalid harvest table entry %s" % (str(entry)))
            index += 7

    def parse_and_draw(self, screen, data, current_segment=None, pick_buffer=None):
        objects = self.parse_objects(data)
        self.draw_objects(screen, objects, current_segment, pick_buffer)

    def draw_objects(self, screen, objects, current_segment=None, pick_buffer=None):
        state = ScreenState(self.segments, current_segment, screen, pick_buffer)
        for obj in objects:
            log.debug("Processing draw object %s" % obj)
            state.draw_object(obj)
        return state
