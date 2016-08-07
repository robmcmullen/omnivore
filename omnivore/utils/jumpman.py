import numpy as np

from atrcopy import selected_bit_mask, match_bit_mask, data_bit_mask, comment_bit_mask

from omnivore.utils.runtime import get_all_subclasses

import logging
log = logging.getLogger(__name__)
#log.setLevel(logging.DEBUG)


def is_bad_harvest_position(x, y, hx, hy):
    hx = hx & 0x1f
    hy = (hy & 0x1f) / 2
    startx = (16 - hx) & 0x1f
    starty = (0 - hy) & 0xf
    endx = (startx + 8) & 0x1f
    endy = (starty + 4) & 0xf
    x = x & 0x1f
    y = y & 0xf
    #print "harvest_location: hx=%d x=%d startx=%d  hy=%d y=%d starty=%d" % (hx, x, startx, hy, y, starty)
    if endx > startx:
        if x >= startx and x < endx:
            return True
    else:
        # the grid is wrapped around, e.g. XX------------------------XXXXXX
        if x >= startx or x < endx:
            return True

    if endy > starty:
        if y >= starty and y < endy:
            return True
    else:
        if y >= starty or y < endy:
            return True
    
    return False

class JumpmanDrawObject(object):
    name = "object"
    default_addr = None
    default_dx = 4
    default_dy = 3
    vertical_only = False
    single = False
    sort_order = 0
    valid_x_mask = 0xff
    drawing_codes = None
    _pixel_list = None
    error_drawing_codes = np.asarray([
        6, 0, -1,  3, 0, 0, 0, 0, 3,
        6, 0,  0,  0, 3, 0, 0, 3, 0,
        6, 0,  1,  0, 0, 3, 3, 0, 0,
        6, 0,  2,  0, 3, 0, 0, 3, 0,
        6, 0,  3,  3, 0, 0, 0, 0, 3,
        0xff
    ], dtype=np.uint8)
    _error_pixel_list = None

    def __init__(self, pick_index, x, y, count, dx=None, dy=None, addr=None):
        self.x = x
        self.y = y
        self.count = count
        self.addr = self.default_addr if addr is None else addr
        self.pick_index = pick_index
        self.dx = self.default_dx if dx is None else dx
        self.dy = self.default_dy if dy is None else dy
        self.trigger_function = None
        self.trigger_painting = []
        self.error = False

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

    @property
    def distance(self):
        """Proportional value to distance from upper left corner, used for
        sorting
        """
        x = int(self.x)  # make sure the math is not done on uint8!
        y = int(self.y)
        return x * x + y * y

    @property
    def trigger_str(self):
        n = len(self.trigger_painting)
        if n > 0:
            paint = ": %d painted object" % n
            if n > 1:
                paint += "s"
        else:
            paint = ""
        return "x=%d y=%d%s" % (self.x, self.y, paint)

    @property
    def pixel_list(self):
        if self.__class__._pixel_list is None:
            self.__class__._pixel_list = self.generate_pixel_list(self.drawing_codes)
        return self.__class__._pixel_list

    @property
    def error_pixel_list(self):
        if self.__class__._error_pixel_list is None:
            self.__class__._error_pixel_list = self.generate_pixel_list(self.error_drawing_codes)
        return self.__class__._error_pixel_list

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
        return "%s %x %s x=%x y=%x dx=%d dy=%d count=%d%s" % (self.name, id(self), addr, self.x, self.y, self.dx, self.dy, self.count, extra)

    def __eq__(self, other):
        try:
            if (self.x, self.y, self.count, self.dx, self.dy, self.trigger_function) == (other.x, other.y, other.count, other.dx, other.dy, other.trigger_function):
                for sp, op in zip(self.trigger_painting, other.trigger_painting):
                    if sp == op:  # have to use == rather than != because __neq__ isn't defined
                        continue
                    else:
                        return False
                return True
        except AttributeError:
            pass
        return False

    def generate_pixel_list(self, codes):
        log.debug("generating pixel list from codes: %s" % str(codes))
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
        return lines

    def equal_except_painting(self, other):
        try:
            if (self.x, self.y, self.count, self.dx, self.dy, self.trigger_function) == (other.x, other.y, other.count, other.dx, other.dy, other.trigger_function):
                return True
        except AttributeError:
            pass
        return False

    def update_table(self, state):
        pass

    def harvest_checksum(self, hx, hy):
        return ((self.x + 0x30 + hx) & 0xe0) | (((self.y * 2) + 0x20 + hy) & 0xe0)/0x10

    def is_bad_location(self, hx, hy):
        return is_bad_harvest_position(self.x, self.y, hx, hy) or is_bad_harvest_position(self.x + self.default_dx - 1, self.y + self.default_dy - 1, hx, hy)

    def is_offscreen(self):
        # check bounds of starting item
        x = self.x
        y = self.y
        if y < 0 or y + abs(self.default_dy) > 88 or x < 0 or x + abs(self.default_dx) > 160:
            return True

        # check bounds of last item
        x = self.x + (self.count - 1) * self.dx
        y = self.y + (self.count - 1) * self.dy
        if y < 0 or y + abs(self.default_dy) > 88 or x < 0 or x + abs(self.default_dx) > 160:
            return True
        return False


class JumpmanRespawn(JumpmanDrawObject):
    name = "jumpman"
    drawing_codes = np.asarray([
        6, 0, -5,  4, 4, 4, 4, 4, 4,
        6, 0, -4,  4, 0, 0, 0, 0, 4,
        6, 0, -3,  4, 0, 0, 0, 0, 4,
        6, 0, -2,  4, 0, 0, 0, 0, 4,
        6, 0, -1,  4, 0, 0, 0, 0, 4,
        6, 0,  0,  4, 4, 4, 4, 4, 4,
        0xff
    ], dtype=np.uint8)
    default_dx = 6
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
    default_dy = 4
    vertical_only = True
    sort_order = 10
    valid_x_mask = 0xfe  # Even pixels only
    drawing_codes = np.fromstring("\x02\x00\x00\x02\x02\x02\x06\x00\x02\x02\x02\x00\x01\x02\x02\x02\x06\x01\x02\x02\x08\x00\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x00\x03\x02\x02\x02\x06\x03\x02\x02\xff", dtype=np.uint8)

    def update_table(self, state):
        state.add_ladder(self)

class UpRope(JumpmanDrawObject):
    name = "uprope"
    default_addr = 0x40af
    default_dx = 2
    default_dy = 4
    vertical_only = True
    sort_order = 20
    drawing_codes = np.fromstring("\x01\x00\x00\x01\x01\x01\x01\x01\x01\x00\x02\x01\x01\x01\x03\x01\xff", dtype=np.uint8)

class DownRope(JumpmanDrawObject):
    name = "downrope"
    default_addr = 0x40c0
    default_dx = 2
    default_dy = 4
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

    def harvest_entry(self, hx, hy):
        # default to empty painting table list at 0x284c
        return [self.harvest_checksum(hx, hy), self.x, self.y, self.trigger_function_low, self.trigger_function_hi, 0x4c, 0x28]

class EraseGirder(JumpmanDrawObject):
    name = "girder_erase"
    default_addr = 0x4016
    sort_order = 35
    drawing_codes = np.fromstring("\x04\x00\x00\x00\x00\x00\x00\x04\x00\x01\x00\x00\x00\x00\x04\x00\x02\x00\x00\x00\x00\xff", dtype=np.uint8)

class EraseLadder(JumpmanDrawObject):
    name = "ladder_erase"
    default_addr = 0x4056
    default_dx = 8
    default_dy = 4
    vertical_only = True
    sort_order = 36
    valid_x_mask = 0xfe  # Even pixels only
    drawing_codes = np.fromstring("\x08\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x08\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00\x08\x00\x03\x00\x00\x00\x00\x00\x00\x00\x00\xff", dtype=np.uint8)

class EraseRope(JumpmanDrawObject):
    name = "rope_erase"
    default_addr = 0x40d1
    default_dx = 2
    default_dy = 4
    vertical_only = True
    sort_order = 37
    drawing_codes = np.fromstring("\x02\x00\x00\x00\x00\x02\x00\x01\x00\x00\x02\x00\x02\x00\x00\x02\x00\x03\x00\x00\xff", dtype=np.uint8)


class LevelDef(object):
    def __init__(self, origin):
        self.origin = origin
        self.level_data = []
        self.harvest_entries = []
        self.painting_entries = []
        self.ladder_positions = set()
        self.downrope_positions = set()
        self.peanuts = set()
        self.pick_dict = dict()

    @property
    def sorted_peanuts(self):
        return sorted(self.peanuts, key=lambda a:a.distance)

    def add_ladder(self, obj):
        self.ladder_positions.add(obj.x + 0x30)

    def add_downrope(self, obj):
        self.downrope_positions.add(obj.x + 0x2e)

    def add_pick(self, obj):
        self.pick_dict[obj.pick_index] = obj

    def check_object(self, obj):
        obj.update_table(self)
        if obj.single:
            self.peanuts.add(obj)

    def get_picked(self, pick_index):
        return self.pick_dict[pick_index]

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

    def get_painting_table(self, objects):
        """Create bytes that define the level.

        Orders the objects into groups (sorted by the sort_order) and returns a
        list of bytes terminated with 0xff
        """
        groups = self.group_objects(objects)
        dx = dy = 999999
        level_data = []
        if groups[0]:
            for group in groups:
                obj = group[0]
                level_data.extend([0xfc, obj.addr_low, obj.addr_hi])
                for obj in group:
                    if obj.dx != dx or obj.dy != dy:
                        dx, dy = obj.dx, obj.dy
                        level_data.extend([0xfe, dx, dy])
                    level_data.extend([0xfd, obj.x, obj.y, obj.count])
        level_data.append(0xff)
        return level_data

    def get_harvest_entry(self, obj, hx, hy):
        entries = []
        self.check_object(obj)
        harvest_entry = obj.harvest_entry(hx, hy)
        if obj.trigger_painting:
            painting_data = self.get_painting_table(obj.trigger_painting)
            entries.append([harvest_entry, painting_data])
            for sub_obj in obj.trigger_painting:
                self.check_object(sub_obj)
                if sub_obj.single:
                    entries.extend(self.get_harvest_entry(sub_obj, hx, hy))
        else:
            entries.append([harvest_entry, []])
        return entries

    def get_ropeladder_data(self):
        ropeladder_data = np.zeros([18], dtype=np.uint8)
        d = sorted(self.ladder_positions)[0:12]
        ropeladder_data[0:len(d)] = d
        d = sorted(self.downrope_positions)[0:6]
        ropeladder_data[12:12 + len(d)] = d
        return ropeladder_data

    def process_objects(self, objects, hx, hy):
        main_level_data = self.get_painting_table(objects)

        # process any object characteristics
        trigger_objects = []
        for obj in objects:
            self.check_object(obj)
            if obj.single:
                trigger_objects.append(obj)

        # At this point, the main layer level definition is complete. We
        # now need to create the harvest table entries and painting table
        # entries from the peanuts that have triggers
        harvest_entries = []
        for obj in trigger_objects:
            h = self.get_harvest_entry(obj, hx, hy)
            print "harvest entry for", obj, h
            harvest_entries.extend(h)

        # Step 1: gather harvest table and painting table entries to determine
        # total length of harvest table so that addresses can be calculated.
        level_data = list(main_level_data)
        harvest_data = []
        painting_data = []
        harvest_index = len(level_data)

        # Step 2: start of painting table is after all harvest table entries,
        # plus an additional 0xff byte marking the end of the table
        painting_index = harvest_index + (len(harvest_entries) * 7) + 1

        # Step 3: create the harvest table and modify each entry to point to
        # the painting table entries
        for harvest, painting in harvest_entries:
            # painting table entries consisting of only 0xff will be ignored,
            # pointing to the default 0x284c
            print "processing", harvest, painting
            if len(painting) > 1:
                addr = self.origin + painting_index
                hi, low = divmod(addr, 256)
                harvest[5:7] = [low, hi]
                painting_data.extend(painting)
                painting_index += len(painting)
            harvest_data.extend(harvest)
        harvest_data.append(0xff)

        print "level data", level_data
        print "harvest table", harvest_data
        print "painting table", painting_data

        level_data.extend(harvest_data)
        level_data.extend(painting_data)

        return np.asarray(level_data, dtype=np.uint8), self.origin + harvest_index, self.get_ropeladder_data(), len(self.peanuts)


class ScreenState(LevelDef):
    def __init__(self, segments, current_segment, screen, pick_buffer):
        LevelDef.__init__(self, -1)
        self.object_code_cache = {}
        self.missing_object_codes = set()
        self.search_order = []
        self.current_segment = current_segment
        if current_segment is not None:
            self.search_order.append(current_segment)
        self.search_order.extend(segments)
        self.screen = screen
        self.pick_buffer = pick_buffer

    def __str__(self):
        return "current segment: %s\nsearch order: %s\nladders: %s\ndownropes: %s" % (self.current_segment, self.search_order, self.ladder_positions, self.downrope_positions)

    # The following commented out code generates the text string
    #circle = np.zeros((7, 8), dtype=np.uint8)
    #circle[0,2:6] = circle[6,2:6] = circle[2:5,0] = circle[2:5,7] = circle[1,1] = circle[1,6] = circle[5,6] = circle[5,1] = match_bit_mask
    circle = np.fromstring('\x00\x00\x10\x10\x10\x10\x00\x00\x00\x10\x00\x00\x00\x00\x10\x00\x10\x00\x00\x00\x00\x00\x00\x10\x10\x00\x00\x00\x00\x00\x00\x10\x10\x00\x00\x00\x00\x00\x00\x10\x00\x10\x00\x00\x00\x00\x10\x00\x00\x00\x10\x10\x10\x10\x00\x00', dtype=np.uint8).reshape((7,8))
    trigger_circle = np.zeros((7,160), dtype=np.uint8)
    trigger_circle[0:7,0:8] = circle
    trigger_circle = trigger_circle.flatten()

    def draw_object(self, obj, highlight=False):
        if obj.drawing_codes is None:
            if obj.addr is None:
                return
            log.debug("addr=%x x=%d y=%d dx=%d dy=%d, num=%d" % (obj.addr, obj.x, obj.y, obj.dx, obj.dy, obj.count))
            codes = self.get_object_code(obj.addr)
            if codes is None:
                log.warning("  no drawing codes found for %s" % str(obj.addr))
                return
            pixel_list = obj.generate_pixel_list(codes)
        else:
            log.debug("addr=BUILTIN x=%d y=%d dx=%d dy=%d, num=%d" % (obj.x, obj.y, obj.dx, obj.dy, obj.count))
            pixel_list = obj.pixel_list

        x = obj.x
        y = obj.y
        self.add_pick(obj)
        if obj.error:
            pixel_list = obj.error_pixel_list
            for i in range(obj.count):
                for n, xoffset, yoffset, pixels in pixel_list:
                    for i, c in enumerate(pixels):
                        px = x + xoffset + i
                        py = y + yoffset
                        index = self.draw_pixel(px, py, c, highlight, False)
                        if index is not None and self.pick_buffer is not None:
                            self.pick_buffer[index] = obj.pick_index
                x += obj.dx
                y += obj.dy
        else:
            has_trigger_function = bool(obj.trigger_function)
            for i in range(obj.count):
                for n, xoffset, yoffset, pixels in pixel_list:
                    for i, c in enumerate(pixels):
                        px = x + xoffset + i
                        py = y + yoffset
                        index = self.draw_pixel(px, py, c, highlight, has_trigger_function)
                        if index is not None and self.pick_buffer is not None:
                            self.pick_buffer[index] = obj.pick_index
                x += obj.dx
                y += obj.dy

            # Draw extra highlight around peanut if has trigger painting functions
            if obj.trigger_painting:
                index = (obj.y - 2) * 160 + obj.x - 2
                if index > len(self.screen):
                    return
                if index < 0:
                    cindex = -index
                    index = 0
                else:
                    cindex = 0
                cend = len(self.trigger_circle)
                if index + cend > len(self.screen):
                    iend = len(self.screen)
                    cend = cindex + iend - index
                else:
                    iend = index + cend - cindex
                self.screen.style[index:iend] |= self.trigger_circle[cindex:cend]

        self.check_object(obj)

    # map color numbers in drawing codes to ANTIC register order
    # jumpman color numbers are 0 - 3
    # color number 4 is used to draw Jumpman
    # ANTIC player color registers are 0 - 3
    # ANTIC playfield color registers are 4 - 7
    # ANTIC background color is 8
    color_map = {0:8, 1:4, 2:5, 3:6, 4:0}

    def draw_pixel(self, x, y, color, highlight, trigger):
        index = y * 160 + x
        if index < 0 or index >= len(self.screen):
            return None
        self.screen[index] = self.color_map[color]
        s = 0
        if highlight:
            s = selected_bit_mask
        if trigger:
            s |= match_bit_mask
        self.screen.style[index] |= s
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
        self.pick_index = 0
        self.harvest_offset = (0, 0)
        self.harvest_offset_seen = set()
        self.harvest_offset_dups = set()

    def set_harvest_offset(self, offset):
        self.harvest_offset = tuple(offset)
        self.harvest_offset_seen = set()
        self.harvest_offset_dups = set()
        self.check_harvest()

    def check_harvest(self):
        self.check_invalid_harvest(self.objects)
        self.check_peanut_grid(self.objects)

    def check_invalid_harvest(self, objs):
        for obj in objs:
            if obj.single:
                grid = obj.harvest_checksum(*self.harvest_offset)
                if grid in self.harvest_offset_seen:
                    self.harvest_offset_dups.add(grid)
                else:
                    self.harvest_offset_seen.add(grid)
            if obj.trigger_painting:
                self.check_invalid_harvest(obj.trigger_painting)

    def check_peanut_grid(self, objs):
        for obj in objs:
            if obj.single:
                grid = obj.harvest_checksum(*self.harvest_offset)
                obj.error = grid in self.harvest_offset_dups
                if obj.error:
                    print "found duplicate peanut @ ", grid
                else:
                    obj.error = obj.is_bad_location(*self.harvest_offset)
                    if obj.error:
                        print "found bad object location"
            if obj.trigger_painting:
                self.check_peanut_grid(obj.trigger_painting)

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
            self.pick_index += 1
            index += 1
            command = None
            if c < 0xfb:
                if addr is not None:
                    obj = self.get_object(self.pick_index, x, y, c, dx, dy, addr)
                    print "parse_objects: new", obj
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

    def parse_level_data(self, segment, level_addr, harvest_addr):
        print "parse level data", segment
        self.pick_index = 0
        self.objects = self.parse_objects(segment[level_addr - segment.start_addr:])
        self.parse_harvest_table(segment, segment.start_addr, harvest_addr)

    def find_equivalent_object(self, old, objects=None):
        found = None
        if objects is None:
            objects = self.objects
        for obj in objects:
            if obj.pick_index == old.pick_index:
                found = obj
                break
            found = self.find_equivalent_object(old, obj.trigger_painting)
            if found is not None:
                break
        return found

    def find_equivalent(self, old_objects, objects=None):
        """ Find the equivalent objects

        JumpmanDrawObjects get regenerated after each call to parse_objects, so
        they will get new object IDs. The select UI in JumpmanEditor keeps
        track of objects, but after the call to parse_objects they won't match
        object IDs. This function compares each objects in the argument list to
        the newly created objects to find equivalents that can be highlighted
        in the UI.
        """
        found = []
        if objects is None:
            objects = self.objects
        for old in old_objects:
            for obj in objects:
                if old == obj:
                    obj.orig_x = obj.x
                    obj.orig_y = obj.y
                    found.append(obj)
                    break
                if obj.single:
                    found.extend(self.find_equivalent(old_objects, obj.trigger_painting))
        return found

    def find_equivalent_peanut(self, old, objects=None):
        """ Find the equivalent peanut object.

        (see find_equivalent for more info on why this is necessary)
        """
        found = None
        if objects is None:
            objects = self.objects
        for obj in objects:
            if obj.equal_except_painting(old):
                obj.orig_x = obj.x
                obj.orig_y = obj.y
                found = obj
                break
            found = self.find_equivalent_peanut(old, obj.trigger_painting)
            if found is not None:
                break
        return found

    def draw_objects(self, screen, objects=None, current_segment=None, pick_buffer=None, highlight=[], state=None):
        if objects is None:
            objects = self.objects
        if state is None:
            state = ScreenState(self.segments, current_segment, screen, pick_buffer)
        highlight = set(highlight)
        for obj in objects:
            log.debug("Processing draw object %s" % obj)
            state.draw_object(obj, obj in highlight)
        return state

    def fade_screen(self, screen):
        # +16 activates the dim color palette
        screen[:] |= 0x10

    def get_harvest_state(self, objects=None, state=None, indent=""):
        if objects is None:
            objects = self.objects
        if state is None:
            state = ScreenState([], None, None, None)
        for obj in objects:
            state.check_object(obj)

            # recurse into trigger painting objects
            log.debug("%sharvest state %s, painting: %s" % (indent, obj, obj.trigger_painting))
            self.get_harvest_state(obj.trigger_painting, state, indent + "  ")
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

    def create_level_definition(self, level_data_origin, hx, hy, objects=None):
        if objects is None:
            objects = self.objects
        levdef = LevelDef(level_data_origin)
        return levdef.process_objects(objects, hx, hy)
