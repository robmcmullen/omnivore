import numpy as np

from atrcopy import selected_bit_mask

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
    sort_order = 0
    valid_x_mask = 0xff
    drawing_codes = None

    def __init__(self, pick_index, x, y, count, dx=None, dy=None, addr=None):
        self.x = x
        self.y = y
        self.count = count
        self.addr = self.default_addr if addr is None else addr
        self.pick_index = pick_index
        self.dx = self.x_spacing if dx is None else dx
        self.dy = self.y_spacing if dy is None else dy
        self.trigger_function = None
        self.trigger_painting = []

    @property
    def addr_low(self):
        hi, low = divmod(self.addr, 256)
        return low

    @property
    def addr_hi(self):
        hi, low = divmod(self.addr, 256)
        return hi

    @property
    def trigger_function_low(self):
        addr = self.trigger_function
        if addr is None:
            addr = 0x284b
        hi, low = divmod(addr, 256)
        return low

    @property
    def trigger_function_hi(self):
        addr = self.trigger_function
        if addr is None:
            addr = 0x284b
        hi, low = divmod(addr, 256)
        return hi

    def __str__(self):
        extra = ""
        if self.trigger_function is not None:
            extra = " trigger_func=%x" % self.trigger_function
        if self.trigger_painting:
            prefix = "\n  trigger_paint: "
            extra += prefix + prefix.join(str(obj) for obj in self.trigger_painting)
        if self.addr is None:
            addr = "BUILTIN"
        else:
            addr = "%04x" % self.addr
        return "%s %s x=%x y=%x dx=%d dy=%d count=%d%s" % (self.name, addr, self.x, self.y, self.dx, self.dy, self.count, extra)

    def __eq__(self, other):
        if (self.x, self.y, self.count, self.dx, self.dy, self.trigger_function) == (other.x, other.y, other.count, other.dx, other.dy, other.trigger_function):
            for sp, op in zip(self.trigger_painting, other.trigger_painting):
                if sp == op:  # have to use == rather than != because __neq__ isn't defined
                    continue
                else:
                    return False
            return True
        return False

    def update_table(self, state):
        pass

    def harvest_checksum(self, hx, hy):
        return ((self.x + 0x30 + hx) & 0xe0) | (((self.y * 2) + 0x20 + hy) & 0xe0)/0x10

class JumpmanRespawn(JumpmanDrawObject):
    name = "jumpman"
    drawing_codes = np.asarray([
        8, 0, -5,  4, 4, 0, 0, 0, 0, 4, 4,
        8, 0, -4,  0, 4, 4, 0, 0, 4, 4, 0,
        8, 0, -3,  0, 0, 4, 4, 4, 4, 0, 0,
        8, 0, -2,  0, 0, 4, 4, 4, 4, 0, 0,
        8, 0, -1,  0, 4, 4, 0, 0, 4, 4, 0,
        8, 0,  0,  4, 4, 0, 0, 0, 0, 4, 4,
        0xff
    ], dtype=np.uint8)
    default_dx = 8
    default_dy = 0
    valid_x_mask = 0xfe  # Even pixels only

class Girder(JumpmanDrawObject):
    name = "girder"
    default_addr = 0x4000
    default_dy = 3
    sort_order = 0
    drawing_codes = np.fromstring("\x04\x00\x00\x01\x01\x01\x01\x04\x00\x01\x01\x00\x01\x00\x04\x00\x02\x01\x01\x01\x01\xff", dtype=np.uint8)

class Ladder(JumpmanDrawObject):
    name = "ladder"
    default_addr = 0x402c
    default_dx = 8
    vertical_only = True
    sort_order = 10
    valid_x_mask = 0xfe  # Even pixels only
    drawing_codes = np.fromstring("\x02\x00\x00\x02\x02\x02\x06\x00\x02\x02\x02\x00\x01\x02\x02\x02\x06\x01\x02\x02\x08\x00\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x00\x03\x02\x02\x02\x06\x03\x02\x02\xff", dtype=np.uint8)

    def update_table(self, state):
        state.add_ladder(self)

class UpRope(JumpmanDrawObject):
    name = "uprope"
    default_addr = 0x40af
    vertical_only = True
    sort_order = 20
    drawing_codes = np.fromstring("\x01\x00\x00\x01\x01\x01\x01\x01\x01\x00\x02\x01\x01\x01\x03\x01\xff", dtype=np.uint8)

class DownRope(JumpmanDrawObject):
    name = "downrope"
    default_addr = 0x40c0
    vertical_only = True
    sort_order = 30
    valid_x_mask = 0xfe  # Even pixels only
    drawing_codes = np.fromstring("\x01\x00\x00\x02\x01\x00\x01\x02\x01\x01\x02\x02\x01\x01\x03\x02\xff", dtype=np.uint8)

    def update_table(self, state):
        state.add_downrope(self)

class Peanut(JumpmanDrawObject):
    name = "peanut"
    default_addr = 0x4083
    default_dy = 3
    single = True
    sort_order = 40
    drawing_codes = np.fromstring("\x04\x00\x00\x00\x03\x03\x00\x04\x00\x01\x03\x00\x00\x03\x04\x00\x02\x00\x03\x03\x00\xff", dtype=np.uint8)

class EraseGirder(JumpmanDrawObject):
    name = "girder_erase"
    default_addr = 0x4016
    sort_order = 35
    drawing_codes = np.fromstring("\x04\x00\x00\x00\x00\x00\x00\x04\x00\x01\x00\x00\x00\x00\x04\x00\x02\x00\x00\x00\x00\xff", dtype=np.uint8)

class EraseLadder(JumpmanDrawObject):
    name = "ladder_erase"
    default_addr = 0x4056
    sort_order = 36
    valid_x_mask = 0xfe  # Even pixels only
    drawing_codes = np.fromstring("\x08\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x08\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00\x08\x00\x03\x00\x00\x00\x00\x00\x00\x00\x00\xff", dtype=np.uint8)

class EraseRope(JumpmanDrawObject):
    name = "rope_erase"
    default_addr = 0x40d1
    sort_order = 37
    drawing_codes = np.fromstring("\x02\x00\x00\x00\x00\x02\x00\x01\x00\x00\x02\x00\x02\x00\x00\x02\x00\x03\x00\x00\xff", dtype=np.uint8)


class ScreenState(object):
    def __init__(self, segments, current_segment, screen, pick_buffer):
        self.object_code_cache = {}
        self.missing_object_codes = set()
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
        self.harvest_objects = set()

    def __str__(self):
        return "current segment: %s\nsearch order: %s\nladders: %s\ndownropes: %s" % (self.current_segment, self.search_order, self.ladder_positions, self.downrope_positions)

    def add_ladder(self, obj):
        self.ladder_positions.add(obj.x + 0x30)

    def add_downrope(self, obj):
        self.downrope_positions.add(obj.x + 0x2e)

    def draw_object(self, obj, highlight=False):
        if obj.drawing_codes is None:
            if obj.addr is None:
                return
            log.debug("addr=%x x=%d y=%d dx=%d dy=%d, num=%d" % (obj.addr, obj.x, obj.y, obj.dx, obj.dy, obj.count))
            codes = self.get_object_code(obj.addr)
            if codes is None:
                return
            log.debug("  found codes: %s" % str(codes))
        else:
            codes = obj.drawing_codes
            log.debug("addr=BUILTIN x=%d y=%d dx=%d dy=%d, num=%d" % (obj.x, obj.y, obj.dx, obj.dy, obj.count))
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
                    index = self.draw_pixel(px, py, c, highlight)
                    if index is not None and self.pick_buffer is not None:
                        self.pick_buffer[index] = obj.pick_index
            x += obj.dx
            y += obj.dy
        self.pick_dict[obj.pick_index] = obj
        obj.update_table(self)

    def check_object(self, obj):
        obj.update_table(self)
        if obj.single:
            self.harvest_objects.add(obj)

    def get_picked(self, pick_index):
        return self.pick_dict[pick_index]

    # map color numbers in drawing codes to ANTIC register order
    # jumpman color numbers are 0 - 3
    # color number 4 is used to draw Jumpman
    # ANTIC player color registers are 0 - 3
    # ANTIC playfield color registers are 4 - 7
    # ANTIC background color is 8
    color_map = {0:8, 1:4, 2:5, 3:6, 4:0}

    def draw_pixel(self, x, y, color, highlight):
        index = y * 160 + x
        if index < 0 or index >= len(self.screen):
            return None
        self.screen[index] = self.color_map[color]
        if highlight:
            self.screen.style[index] = selected_bit_mask
        return index

    def get_object_code(self, addr):
        if addr in self.object_code_cache:
            return self.object_code_cache[addr]
        if addr in self.missing_object_codes:
            return None
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
        self.missing_object_codes.add(addr)


class JumpmanLevelBuilder(object):
    def __init__(self, segments):
        self.segments = segments
        self.objects = []

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

    def parse_harvest_table(self, d, origin, horigin, objects=None):
        if objects is None:
            objects = self.objects
        objmap = {(obj.x, obj.y):obj for obj in objects if obj.single}
        data = np.array(d, dtype=np.uint8)
        last = len(data)
        index = horigin - origin

        # Walk through the entire list first to pull out any paint objects that
        # might be peanuts
        harvest_info = []
        while index < last:
            c = data[index]
            if c >= 0xf0:
                # ordinarily, the table is suppost to be delimited by an 0xff,
                # but Grand Puzzle II has a bug in the harvest table definition
                # and starts right up with the painting table without an 0xff.
                # But as it turns out, because the code to generate the
                # checksum ands the checksum with 0xee, a checksum value can
                # never be 0xfx. Checking for that case should be sufficient to
                # stop processing
                break
            entry = data[index:index + 7]
            log.debug("harvest entry: ck=%x x=%x y=%x trig=%02x%02x paint=%02x%02x" % (entry[0], entry[1], entry[2], entry[4], entry[3], entry[6], entry[5]))

            addr = entry[5] + 256*entry[6]
            paint_objs = []
            if addr >= origin and addr <= origin + len(d):
                paint_objs = self.parse_objects(d[addr - origin:])
                for obj in paint_objs:
                    if obj.single:
                        objmap[(obj.x, obj.y)] = obj
            elif addr != 0x284c:
                log.error("  trigger paint addr %04x not found in segment!" % addr)

            addr = entry[3] + 256*entry[4]
            if addr == 0x284b:
                addr = None

            harvest_info.append((entry, paint_objs, addr))
            index += 7

        # go back through the list and update any referenced objects
        for entry, paint_objs, addr in harvest_info:
            try:
                obj = objmap[entry[1], entry[2]]
                obj.trigger_function = addr
                obj.trigger_painting = paint_objs
            except KeyError:
                log.error("Invalid harvest table entry %s" % (str(entry)))

    def parse_and_draw(self, screen, segment, level_addr, harvest_addr, pick_buffer=None):
        self.objects = self.parse_objects(segment[level_addr - segment.start_addr:])
        self.parse_harvest_table(segment, segment.start_addr, harvest_addr)
        return self.draw_objects(screen, self.objects, segment, pick_buffer)

    def find_equivalent(self, old_objects):
        """ Find the equivalent objects in the current list. JumpmanDrawObjects
        will get regenerated after each call to parse_objects, so they will get
        new object IDs. The select UI in JumpmanEditor keeps track of objects,
        but after the call to parse_objects they won't match object IDs. This
        function compares each of the specified objects in the argument list to
        the newly created objects to find equivalents that can be highlighted
        in the UI.
        """
        found = []
        for old in old_objects:
            for obj in self.objects:
                if old == obj:
                    obj.orig_x = obj.x
                    obj.orig_y = obj.y
                    found.append(obj)
                    break
        return found

    def draw_objects(self, screen, objects, current_segment=None, pick_buffer=None, highlight=[]):
        state = ScreenState(self.segments, current_segment, screen, pick_buffer)
        highlight = set(highlight)
        for obj in objects:
            log.debug("Processing draw object %s" % obj)
            state.draw_object(obj, obj in highlight)
        return state

    def get_harvest_state(self, objects=None, state=None):
        if objects is None:
            objects = self.objects
        if state is None:
            state = ScreenState([], None, None, None)
        for obj in objects:
            state.check_object(obj)

            # recurse into trigger painting objects
            self.get_harvest_state(obj.trigger_painting, state)
        return state

    def add_objects(self, new_objects, objects=None):
        if objects is None:
            objects = self.objects
        objects.extend(new_objects)
        objects.sort(key=lambda a:a.sort_order)

    def delete_objects(self, to_remove, objects=None):
        if objects is None:
            objects = self.objects
        for obj in to_remove:
            try:
                objects.remove(obj)
            except ValueError:
                log.error("Attempting to remove object not in list: %s" % obj)
        objects.sort(key=lambda a:a.sort_order)

    def group_objects(self, objects):
        groups = []
        current = []
        for obj in objects:
            if not current or current[-1].__class__ == obj.__class__:
                current.append(obj)
            else:
                groups.append(current)
                current = [obj]
        groups.append(current)
        return groups

    class LevelDef(object):
        def __init__(self, origin):
            self.origin = origin
            self.level_data = []
            self.harvest_entries = []
            self.painting_entries = []
            self.ladder_positions = set()
            self.downrope_positions = set()

        def add_ladder(self, obj):
            self.ladder_positions.add(obj.x + 0x30)

        def add_downrope(self, obj):
            self.downrope_positions.add(obj.x + 0x2e)

        def add_level_data(self, commands):
            self.level_data.extend(commands)

        def add_harvest_entry(self, h, sublevdef):
            self.harvest_entries.append((h, sublevdef))

        def process_harvest(self):
            for h, sublevdef in self.harvest_entries:
                sublevdef.process_harvest()
                self.painting_entries.append((h, sublevdef.level_data))
                self.ladder_positions.update(sublevdef.ladder_positions)
                self.downrope_positions.update(sublevdef.downrope_positions)

            painting_data = []
            harvest_data = []
            painting_index = len(self.level_data)
            for h, painting in self.painting_entries:
                if len(painting) > 1:
                    addr = self.origin + painting_index
                    painting_data.extend(painting)
                    painting_index += len(painting)
                else:
                    addr = 0x284c
                hi, low = divmod(addr, 256)
                h.extend([low, hi])
                harvest_data.extend(h)
            harvest_data.append(0xff)

            # print "level:", self.level_data
            # print "painting:", painting_data
            # print "harvest:", harvest_data

            data = self.level_data + painting_data + harvest_data

            ropeladder_data = np.zeros([18], dtype=np.uint8)
            d = sorted(self.ladder_positions)[0:12]
            ropeladder_data[0:len(d)] = d
            d = sorted(self.downrope_positions)[0:6]
            ropeladder_data[12:12 + len(d)] = d

            return np.asarray(data, dtype=np.uint8), painting_index, ropeladder_data


    def create_level_definition(self, level_data_origin, hx, hy, objects=None, levdef=None):
        if objects is None:
            objects = self.objects
        groups = self.group_objects(objects)
        dx = dy = 999999
        if levdef is None:
            levdef = JumpmanLevelBuilder.LevelDef(level_data_origin)
        if groups[0]:
            for group in groups:
                obj = group[0]
                levdef.add_level_data([0xfc, obj.addr_low, obj.addr_hi])
                for obj in group:
                    if obj.dx != dx or obj.dy != dy:
                        dx, dy = obj.dx, obj.dy
                        levdef.add_level_data([0xfe, dx, dy])
                    levdef.add_level_data([0xfd, obj.x, obj.y, obj.count])
                    obj.update_table(levdef)
                    if obj.single:
                        # create temporary harvest table entry; can't create full
                        # one until length of level data is known since it's stored
                        # right after that
                        h = [obj.harvest_checksum(hx, hy), obj.x, obj.y, obj.trigger_function_low, obj.trigger_function_hi]
                        sublevdef = JumpmanLevelBuilder.LevelDef(level_data_origin)
                        self.create_level_definition(level_data_origin, hx, hy, obj.trigger_painting, sublevdef)
                        levdef.add_harvest_entry(h, sublevdef)
            levdef.add_level_data([0xff])

        # Create harvest table and painting tables now that the length of
        # everything is known
        level_data, harvest_index, ropeladder_data = levdef.process_harvest()
        return level_data, level_data_origin + harvest_index, ropeladder_data
