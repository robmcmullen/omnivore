import numpy as np

from omnivore.utils.runtime import get_all_subclasses

import logging
log = logging.getLogger(__name__)

class JumpmanCommand(object):
    flag = None
    name = ""
    draw = False

    def __init__(self, index, *args):
        self.index = index
        self.process_args(*args)

    def __str__(self):
        a = self.format_args()
        if a:
            a = " " + a
        return "%s%s" % (self.name, a)

    def format_args(self):
        return ""

    def process_args(self, *args):
        pass

    def update_state(self, state):
        pass

    def update_table(self, state):
        pass

    def execute(self, state):
        self.update_state(state)
        if self.draw:
            state.draw_codes()

class Show(JumpmanCommand):
    name = "show"

    def process_args(self, flag):
        self.flag = flag

class End(JumpmanCommand):
    flag = 0xff
    name = "end"

class Spacing(JumpmanCommand):
    flag = 0xfe
    name = "spacing"

    def format_args(self):
        return "%d %d" % (self.x, self.y)

    def process_args(self, x, y):
        self.x = x
        self.y = y

    def update_state(self, state):
        state.dx = self.x
        state.dy = self.y

class ScreenObject(JumpmanCommand):
    flag = 0xfc
    name = "object"

    def format_args(self):
        return "%x" % (self.addr)

    def process_args(self, addr):
        self.addr = addr

    def update_state(self, state):
        state.addr = self.addr
        state.last_object = self

class StaticObject(ScreenObject):
    name = "staticobject"
    addr = None
    x_spacing = 4
    y_spacing = 4
    single = False
    vertical_only = False

    def process_args(self, *args):
        pass

    def format_args(self):
        return ""

class Girder(StaticObject):
    name = "girder"
    addr = 0x4000
    y_spacing = 3

class Ladder(StaticObject):
    name = "ladder"
    addr = 0x402c
    x_spacing = 8
    vertical_only = True

    def update_table(self, state):
        state.add_ladder()

class UpRope(StaticObject):
    name = "uprope"
    addr = 0x40af
    vertical_only = True

class DownRope(StaticObject):
    name = "downrope"
    addr = 0x40c0
    vertical_only = True

    def update_table(self, state):
        state.add_downrope()

class Peanut(StaticObject):
    name = "peanut"
    addr = 0x4083
    y_spacing = 3
    single = True

class EraseGirder(StaticObject):
    name = "girder_erase"
    addr = 0x4016

class EraseLadder(StaticObject):
    name = "ladder_erase"
    addr = 0x4056

class EraseRope(StaticObject):
    name = "rope_erase"
    addr = 0x40d1

class PositionObject(JumpmanCommand):
    flag = 0xfd
    name = "position"

    def format_args(self):
        return "%d %d" % (self.x, self.y)

    def process_args(self, x, y):
        self.x = x
        self.y = y

    def update_state(self, state):
        state.x = self.x
        state.y = self.y
        state.pick_index = self.index

class DrawObject(PositionObject):
    name = "draw"
    draw = True

    def format_args(self):
        return "%d %d %d" % (self.x, self.y, self.count)

    def process_args(self, x, y, count):
        self.x = x
        self.y = y
        self.count = count

    def update_state(self, state):
        PositionObject.update_state(self, state)
        state.count = self.count

class ScreenState(object):
    def __init__(self, segments, current_segment, screen, pick_buffer):
        self.x = self.y = self.dx = self.dy = self.count = 0
        self.pick_index = -1
        self.addr = None
        self.last_object = None

        self.object_code_cache = {}
        self.search_order = []
        self.current_segment = current_segment
        if current_segment is not None:
            self.search_order.append(current_segment)
        self.search_order.extend(segments)
        self.screen = screen
        self.pick_buffer = pick_buffer

        self.ladder_positions = set()
        self.downrope_positions = set()

    def add_ladder(self):
        self.ladder_positions.add(self.x + 0x30)

    def add_downrope(self):
        self.downrope_positions.add(self.x + 0x2e)

    def draw_codes(self):
        if self.addr is None:
            return
        log.debug("addr=%x x=%d y=%d dx=%d dy=%d, num=%d" % (self.addr, self.x, self.y, self.dx, self.dy, self.count))
        codes = self.get_object_code(self.addr)
        if codes is None:
            return
        if self.last_object:
            self.last_object.update_table(self)
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

        x = self.x
        y = self.y
        for i in range(self.count):
            for n, xoffset, yoffset, pixels in lines:
                for i, c in enumerate(pixels):
                    px = x + xoffset + i
                    py = y + yoffset
                    if self.draw_pixel(px, py, c):
                        if self.pick_buffer is not None:
                            self.pick_buffer[px,py] = self.pick_index
            x += self.dx
            y += self.dy

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

    def parse_commands(self, data):
        commands = []
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
                try:
                    if commands[-1].name == "position":
                        command = commands.pop()
                        # change it into a draw command
                        command = DrawObject(command.index, command.x, command.y, c)
                    else:
                        command = Show(index, c)
                except IndexError:
                    pass
            elif c >= 0xfc and c <= 0xfe:
                arg1 = data[index]
                arg2 = data[index + 1]
                index += 2
                if c == 0xfc:
                    command = self.get_object(pick_index, arg2 * 256 + arg1)
                elif c == 0xfd:
                    command = PositionObject(pick_index, arg1, arg2)
                else:
                    dx = int(np.int8(arg1))  # signed!
                    dy = int(np.int8(arg2))
                    command = Spacing(pick_index, dx, dy)
            elif c == 0xff:
                command = End(pick_index)
                last = 0  # force the end
            if command is not None:
                commands.append(command)
        return commands

    def get_object(self, pick, addr):
        found = ScreenObject
        for kls in get_all_subclasses(StaticObject):
            if kls.addr == addr:
                found = kls
                break
        return found(pick, addr)

    def parse_and_draw(self, screen, data, current_segment=None, pick_buffer=None):
        commands = self.parse_commands(data)
        self.draw_commands(screen, commands, current_segment, pick_buffer)

    def draw_commands(self, screen, commands, current_segment=None, pick_buffer=None):
        state = ScreenState(self.segments, current_segment, screen, pick_buffer)
        for c in commands:
            log.debug("Processing command %s" % c)
            c.execute(state)
        return state
