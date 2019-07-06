import numpy as np

from atrip import style_bits

from sawx.utils.runtime import get_all_subclasses

import logging
log = logging.getLogger(__name__)
#log.setLevel(logging.DEBUG)


def is_valid_level_segment(segment, strict=True):
    # 283f is always 4c (JMP) because it and the next two bytes are a jump target from the game loop
    # 2848: always 20 (i.e. JSR)
    # 284b: always 60 (i.e. RTS)
    # 284c: always FF (target for harvest table if no action to be taken)
    if len(segment) >= 0x800 and segment[0x3f] == 0x4c and segment[0x48] == 0x20 and segment[0x4b] == 0x60 and segment[0x4c] == 0xff:
        # check for sane level definition table
        if strict:
            addr = segment[0x38]*256 + segment[0x37]
            if addr >= segment.origin and addr < segment.origin + len(segment):
                pass
            else:
                log.debug(f"is_valid_level_segment: failed strict test for {segment.name}: level table=${addr:x} not in segment range ${segment.origin:x} - ${segment.origin + len(segment):x}")
                return False
        log.debug(f"is_valid_level_segment: valid {segment.name}: level table=${addr:x}, segment range ${segment.origin:x} - ${segment.origin + len(segment):x}")
        return True
    return False


def is_bad_harvest_position(x, y, hx, hy):
    hx = hx & 0x1f
    hy = (hy & 0x1f) // 2
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


class DrawObjectBounds:
    @classmethod
    def get_bounds(cls, objects):
        bounds = DrawObjectBounds()
        for o in objects:
            bounds.add_bounds(o.bounds)
        return bounds

    def __init__(self, bounds=None):
        if bounds is None:
            self.xmin, self.ymin = None, None
            self.xmax, self.ymax = None, None
        else:
            (self.xmin, self.ymin), (self.xmax, self.ymax) = bounds

    def __str__(self):
        if self.xmin is None:
            return "(undefined bounds)"
        return "(%d,%d -> %d,%d)" % (self.xmin, self.ymin, self.xmax, self.ymax)

    def __eq__(self, other):
        try:
            return (self.xmin, self.ymin, self.xmax, self.ymax) == (other.xmin, other.ymin, other.xmax, other.ymax)
        except AttributeError:
            pass
        return False

    # to be usable in dicts, py3 needs __hash__ defined if __eq__ is defined
    def __hash__(self):
        return id(self)

    @property
    def w(self):
        return self.xmax - self.xmin + 1

    @property
    def h(self):
        return self.ymax - self.ymin + 1

    def get_offset(self, x, y):
        if self.xmin is None:
            return DrawObjectBounds()
        return DrawObjectBounds(((x + self.xmin, y + self.ymin), (x + self.xmax, y + self.ymax)))

    def add_point(self, x, y):
        if self.xmin is None:
            self.xmin = self.ymin = x
            self.xmax = self.ymax = y
        else:
            if x < self.xmin:
                self.xmin = x
            elif x > self.xmax:
                self.xmax = x
            if y < self.ymin:
                self.ymin = y
            elif y > self.ymax:
                self.ymax = y

    def add_bounds(self, other):
        if self.xmin is None:
            self.xmin, self.ymin, self.xmax, self.ymax = other.xmin, other.ymin, other.xmax, other.ymax
        elif other.xmin is not None:
            self.add_point(other.xmin, other.ymin)
            self.add_point(other.xmax, other.ymax)

    def is_inside(self, other):
        if self.xmin is None or other.xmin is None:
            return False
        return self.xmin >= other.xmin and self.xmax <= other.xmax and self.ymin >= other.ymin and self.ymax <= other.ymax


class PixelList:
    # map color numbers in drawing codes to ANTIC register order
    # jumpman color numbers are 0 - 3
    # color number 4 is used to draw Jumpman
    # ANTIC player color registers are 0 - 3
    # ANTIC playfield color registers are 4 - 7
    # ANTIC background color is 8
    color_map = {0:8, 1:4, 2:5, 3:6, 4:0}

    def __init__(self, codes, relative_origin):
        self.pixel_list = self.calc_pixel_list(codes)
        self.generate_pixel_array(self.pixel_list)
        self.x_shift, self.y_shift = relative_origin

    def calc_pixel_list(self, codes):
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

    def generate_pixel_array(self, pixel_list):
        bounds = DrawObjectBounds(((0,0), (0,0)))

        # pass 1: compute boundary
        for n, xoffset, yoffset, pixels in self.pixel_list:
            bounds.add_point(xoffset, yoffset)
            bounds.add_point(xoffset + n - 1, yoffset)
        self.h, self.w = bounds.h, bounds.w

        # pass 2: create mask & image
        pixels = np.zeros((self.h, self.w), dtype=np.uint8)
        mask = np.full((self.h, self.w), 0xff, dtype=np.uint8) 
        for n, xoffset, yoffset, colors in self.pixel_list:
            x = bounds.xmin + xoffset
            y = bounds.ymin + yoffset
            for c in colors:
                pixels[y, x] = self.color_map[c]
                mask[y, x] = 0
                x += 1
        self.pixels = pixels
        self.mask = mask

    def draw_array(self, obj, screen2d, style2d, pick2d, highlight):
        # FIXME: the x value is getting constrainted to a uint8 somewhere, so
        # signed values are positive. Force it to be a negative number by
        # checking for outside the width of the screen
        x = int(obj.x) if obj.x < 160 else int(obj.x - 256)
        y = int(obj.y)
        has_trigger_function = bool(obj.trigger_function)
        x += self.x_shift
        y += self.y_shift
        for i in range(obj.count):
            if x < obj.screen_bounds.xmin or x + self.w - 1 > obj.screen_bounds.xmax or y < obj.screen_bounds.ymin or y + self.h - 1 > obj.screen_bounds.ymax:
                log.debug("unit %d of %s off screen at %s(%d),%s(%d)" % (i, obj, type(x), x, type(y), y))
            else:
                screen2d[y:y+self.h,x:x+self.w] &= self.mask
                screen2d[y:y+self.h,x:x+self.w] |= self.pixels
                if highlight:
                    style2d[y:y+self.h,x:x+self.w] = style_bits.selected_bit_mask
                if has_trigger_function:
                    style2d[y:y+self.h,x:x+self.w] |= style_bits.match_bit_mask
                if pick2d is not None:
                    pick2d[y:y+self.h,x:x+self.w] = obj.pick_index
            x += obj.dx
            y += obj.dy


class JumpmanDrawObject:
    name = "object"
    default_addr = None
    default_dx = 4
    default_dy = 3
    vertical_only = False
    single = False
    sort_order = 0
    valid_x_mask = 0xff
    drawing_codes = None
    drawing_codes_relative_origin = (0, 0)
    _pixel_list = None
    error_drawing_codes = np.asarray([
        6, 0,  0,  3, 0, 0, 0, 0, 3,
        6, 0,  1,  0, 3, 0, 0, 3, 0,
        6, 0,  2,  0, 0, 3, 3, 0, 0,
        6, 0,  3,  0, 3, 0, 0, 3, 0,
        6, 0,  4,  3, 0, 0, 0, 0, 3,
        0xff
    ], dtype=np.uint8)
    error_drawing_codes_relative_origin = (-1, -1)
    _error_pixel_list = None
    screen_bounds = DrawObjectBounds(((0, 0), (159, 87)))

    def __init__(self, pick_index, x, y, count, dx=None, dy=None, addr=None):
        self.x = int(x)
        self.y = int(y)
        self.count = count
        self.addr = self.default_addr if addr is None else addr
        self.pick_index = pick_index
        self.dx = self.default_dx if dx is None else dx
        self.dy = self.default_dy if dy is None else dy
        self.trigger_function = None
        self.trigger_painting = []
        self.error = False
        self._local_bounds = self.get_local_bounds()

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
    def bounds(self):
        return self._local_bounds.get_offset(self.x, self.y)

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
            self.__class__._pixel_list = PixelList(self.drawing_codes, self.drawing_codes_relative_origin)
        return self.__class__._pixel_list

    @property
    def error_pixel_list(self):
        if self.__class__._error_pixel_list is None:
            self.__class__._error_pixel_list = PixelList(self.error_drawing_codes, self.error_drawing_codes_relative_origin)
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

    # to be usable in dicts, py3 needs __hash__ defined if __eq__ is defined
    def __hash__(self):
        return id(self)

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
        return ((self.x + 0x30 + hx) & 0xe0) | (((self.y * 2) + 0x20 + hy) & 0xe0) // 0x10

    def is_bad_location(self, hx, hy):
        return is_bad_harvest_position(self.x, self.y, hx, hy) or is_bad_harvest_position(self.x + self.default_dx - 1, self.y + self.default_dy - 1, hx, hy)

    def get_local_bounds(self):
        bounds = DrawObjectBounds()
        bounds.add_point(0, 0)
        bounds.add_point(self.default_dx - 1, self.default_dy - 1)
        if self.count > 1:
            c = self.count - 1
            lx = c * self.dx
            ly = c * self.dy
            if lx < 0:
                px = lx
            else:
                px = self.default_dx - 1 + lx
            if ly < 0:
                py = ly
            else:
                py = self.default_dy - 1 + ly
            bounds.add_point(px, py)
        return bounds

    def is_offscreen(self):
        return not self.bounds.is_inside(self.screen_bounds)

    def clip(self):
        x = int(self.x) if self.x < 160 else int(self.x - 256)
        y = int(self.y)
        visible_count = 0
        for i in range(self.count):
            if x < self.screen_bounds.xmin or y < self.screen_bounds.ymin:
                # from the left, find the first unit that's fully on screen
                self.x += self.dx
                self.y += self.dy
            elif x + self.default_dx - 1 > self.screen_bounds.xmax or y + self.default_dy - 1 > self.screen_bounds.ymax:
                # at the right, if we go offscreen, we're done.
                break
            else:
                visible_count += 1
            x += self.dx
            y += self.dy
        self.count = visible_count

    def flip_vertical(self, bounds):
        """Reflect the object vertically (i.e. top to bottom). The X
        coordinates stay the same; the Y coordinates are flipped within the
        bounding box of the given area
        """
        self.y = bounds.ymax - (self.y - bounds.ymin) - self.default_dy + 1
        self.orig_y = self.y
        self.dy = -self.dy
        self._local_bounds = self.get_local_bounds()

    def flip_horizontal(self, bounds):
        """Reflect the object horizontally (i.e. left to right). The Y
        coordinates stay the same; the X coordinates are flipped within the
        bounding box of the given area
        """
        self.x = bounds.xmax - (self.x - bounds.xmin) - self.default_dx + 1
        self.orig_x = self.x
        self.dx = -self.dx
        self._local_bounds = self.get_local_bounds()


class JumpmanRespawn(JumpmanDrawObject):
    name = "jumpman"
    drawing_codes = np.asarray([
        6, 0, 0,  4, 4, 4, 4, 4, 4,
        6, 0, 1,  4, 0, 0, 0, 0, 4,
        6, 0, 2,  4, 0, 0, 0, 0, 4,
        6, 0, 3,  4, 0, 0, 0, 0, 4,
        6, 0, 4,  4, 0, 0, 0, 0, 4,
        6, 0, 5,  4, 4, 4, 4, 4, 4,
        0xff
    ], dtype=np.uint8)
    drawing_codes_relative_origin = (0, -5)
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


class Coin(JumpmanDrawObject):
    name = "coin"
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


class LevelDef:
    def __init__(self, origin):
        self.origin = origin
        self.level_data = []
        self.harvest_entries = []
        self.painting_entries = []
        self.ladder_positions = set()
        self.downrope_positions = set()
        self.coins = set()
        self.pick_dict = dict()

    @property
    def sorted_coins(self):
        return sorted(self.coins, key=lambda a:a.distance)

    def add_ladder(self, obj):
        self.ladder_positions.add(obj.x + 0x30)

    def add_downrope(self, obj):
        self.downrope_positions.add(obj.x + 0x2e)

    def add_pick(self, obj):
        self.pick_dict[obj.pick_index] = obj

    def check_object(self, obj):
        obj.update_table(self)
        if obj.single:
            self.coins.add(obj)

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

    def clip_objects(self, objects):
        visible = []
        for obj in objects:
            orig_count = obj.count
            obj.clip()
            if obj.count > 0:
                if orig_count > obj.count:
                    log.debug("clip_objects: partially visible: %s" % obj)
                else:
                    log.debug("clip_objects: fully visible: %s" % obj)
                visible.append(obj)
            else:
                log.debug("clip_objects: fully clipped")
        return visible

    def process_objects(self, objects, hx, hy):
        objects = self.clip_objects(objects)
        main_level_data = self.get_painting_table(objects)

        # process any object characteristics
        trigger_objects = []
        for obj in objects:
            self.check_object(obj)
            if obj.single:
                trigger_objects.append(obj)

        # At this point, the main layer level definition is complete. We
        # now need to create the harvest table entries and painting table
        # entries from the coins that have triggers
        harvest_entries = []
        for obj in trigger_objects:
            h = self.get_harvest_entry(obj, hx, hy)
            log.debug("harvest entry for %s: %s" % (obj, h))
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
            log.debug("processing %s %s" % (harvest, painting))
            if len(painting) > 1:
                addr = self.origin + painting_index
                hi, low = divmod(addr, 256)
                harvest[5:7] = [low, hi]
                painting_data.extend(painting)
                painting_index += len(painting)
            harvest_data.extend(harvest)
        harvest_data.append(0xff)

        log.debug("level data %s" % (level_data))
        log.debug("harvest table %s" % (harvest_data))
        log.debug("painting table %s" % (painting_data))

        level_data.extend(harvest_data)
        level_data.extend(painting_data)

        return np.asarray(level_data, dtype=np.uint8), self.origin + harvest_index, self.get_ropeladder_data(), len(self.coins)


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
        if screen is not None:
            self.screen_2d = screen.container.data.reshape((88, 160))
            self.screen_style_2d = screen.container.style.reshape((88, 160))
        self.pick_buffer = pick_buffer
        if pick_buffer is not None:
            self.pick_buffer_2d = pick_buffer.reshape((88, 160))
        else:
            self.pick_buffer_2d = None

    def __str__(self):
        return "current segment: %s\nsearch order: %s\nladders: %s\ndownropes: %s" % (self.current_segment, self.search_order, self.ladder_positions, self.downrope_positions)

    # The following commented out code generates the text string
    #circle = np.zeros((7, 8), dtype=np.uint8)
    #circle[0,2:6] = circle[6,2:6] = circle[2:5,0] = circle[2:5,7] = circle[1,1] = circle[1,6] = circle[5,6] = circle[5,1] = style_bits.match_bit_mask
    trigger_circle = np.fromstring('\x00\x00    \x00\x00\x00 \x00\x00\x00\x00 \x00 \x00\x00\x00\x00\x00\x00  \x00\x00\x00\x00\x00\x00  \x00\x00\x00\x00\x00\x00 \x00 \x00\x00\x00\x00 \x00\x00\x00    \x00\x00', dtype=np.uint8).reshape((7,8))

    def draw_object(self, obj, highlight=False):
        if obj.drawing_codes is None:
            if obj.addr is None:
                return
            log.debug("addr=%x x=%d y=%d dx=%d dy=%d, num=%d" % (obj.addr, obj.x, obj.y, obj.dx, obj.dy, obj.count))
            codes = self.get_object_code(obj.addr)
            if codes is None:
                log.warning("  no drawing codes found for %s" % str(obj.addr))
                return
            pixel_list = PixelList(codes)
        else:
            log.debug("addr=BUILTIN x=%d y=%d dx=%d dy=%d, num=%d" % (obj.x, obj.y, obj.dx, obj.dy, obj.count))
            pixel_list = obj.pixel_list

        self.add_pick(obj)
        if obj.error:
            pixel_list = obj.error_pixel_list
        pixel_list.draw_array(obj, self.screen_2d, self.screen_style_2d, self.pick_buffer_2d, highlight)

        # Draw extra highlight around coin if has trigger painting functions
        if obj.trigger_painting:
            ox = obj.x + obj.default_dx
            oy = obj.y + obj.default_dy
            if obj.x < 0 or ox > 160 or obj.y < 0 or oy > 88:
                return  # offscreen

            cx = 0
            cy = 0
            cx2 = self.trigger_circle.shape[1]
            cy2 = self.trigger_circle.shape[0]

            x = obj.x - 2
            y = obj.y - 2
            x2 = x + cx2
            y2 = y + cy2

            if x < 0:
                cx = -x
                x = 0
            if y < 0:
                cy = -y
                y = 0

            if x2 > 160:
                cx2 = 160 - x2
                x2 = 160
            if y2 > 88:
                cy2 = 88 - y2
                y2 = 88

            self.screen_style_2d[y:y2,x:x2] |= self.trigger_circle[cy:cy2,cx:cx2]

        self.check_object(obj)

    def get_object_code(self, addr):
        if addr in self.object_code_cache:
            return self.object_code_cache[addr]
        if addr in self.missing_object_codes:
            return None
        for s in self.search_order:
            log.debug("checking segment %s for object code %x" % (s.name, addr))
            index = addr - s.origin
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


class JumpmanLevelBuilder:
    def __init__(self, segments):
        self.segments = segments
        self.objects = []
        self.pick_index = 0
        self.harvest_offset = (0, 0)
        self.harvest_offset_seen = set()
        self.harvest_offset_dups = set()
        self.harvest_bad_locations = 0
        self.harvest_ok = True

    def set_harvest_offset(self, offset):
        self.harvest_offset = tuple(offset)
        self.harvest_offset_seen = set()
        self.harvest_offset_dups = set()
        self.harvest_bad_locations = 0
        self.check_harvest()

    def check_harvest(self):
        self.check_invalid_harvest(self.objects)
        self.check_coin_grid(self.objects)
        self.harvest_ok = not bool(self.harvest_offset_dups) and not bool(self.harvest_bad_locations)

    def harvest_reason(self):
        reasons = []
        if self.harvest_offset_dups:
            reasons.append("* Multiple coins in same grid square!\nJumpman will not collect those coins properly.")
        if self.harvest_bad_locations:
            reasons.append("* Coins in border area between grid squares!\nGame will crash when collecting those coins.")
        return "\n\n".join(reasons)

    def check_invalid_harvest(self, objs):
        for obj in objs:
            if obj.single:
                grid = obj.harvest_checksum(*self.harvest_offset)
                if grid in self.harvest_offset_seen:
                    self.harvest_offset_dups.add(grid)
                else:
                    self.harvest_offset_seen.add(grid)
                if obj.is_bad_location(*self.harvest_offset):
                    self.harvest_bad_locations += 1
            if obj.trigger_painting:
                self.check_invalid_harvest(obj.trigger_painting)

    def check_coin_grid(self, objs):
        for obj in objs:
            if obj.single:
                grid = obj.harvest_checksum(*self.harvest_offset)
                obj.error = grid in self.harvest_offset_dups
                if obj.error:
                    log.error("found duplicate coin @ %s" % grid)
                else:
                    obj.error = obj.is_bad_location(*self.harvest_offset)
                    if obj.error:
                        log.error("found bad object location")
            if obj.trigger_painting:
                self.check_coin_grid(obj.trigger_painting)

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
                    objects.append(obj)
            elif c >= 0xfc and c <= 0xfe:
                arg1 = data[index]
                arg2 = data[index + 1]
                index += 2
                if c == 0xfc:
                    addr = arg2 * 256 + arg1
                elif c == 0xfd:
                    x = int(arg1)
                    y = int(arg2)
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
        # might be coins
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
        self.pick_index = 0
        self.objects = self.parse_objects(segment[level_addr - segment.origin:])
        self.parse_harvest_table(segment, segment.origin, harvest_addr)

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

    def find_equivalent_coin(self, old, objects=None):
        """ Find the equivalent coin object.

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
            found = self.find_equivalent_coin(old, obj.trigger_painting)
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

    def change_trigger(self, objs, rev_old_map, new_map, changed, orphaned, not_labeled):
        for obj in objs:
            if obj.single:
                t = obj.trigger_function
                if t in rev_old_map:
                    name = rev_old_map[t]
                    if name in new_map:
                        new_t = new_map[name]
                        if t != new_t:
                            log.debug("changed %s trigger function to $%04x" % (obj, new_t))
                            obj.trigger_function = new_map[name]
                            changed.append(obj)
                    else:
                        orphaned.append(obj)
                else:
                    not_labeled.append(obj)
            if obj.trigger_painting:
                self.change_trigger(obj.trigger_painting, rev_old_map, new_map, changed, orphaned, not_labeled)

    def update_triggers(self, old_map, new_map, objects=None):
        if objects is None:
            objects = self.objects
        rev_old_map = {v: k for k, v in old_map.items()}
        changed = []
        orphaned = []
        not_labeled = []
        self.change_trigger(objects, rev_old_map, new_map, changed, orphaned, not_labeled)
        return changed, orphaned, not_labeled


class JumpmanCustomCode:
    vector_storage = {
        "vbi1": 0x2802,
        "vbi2": 0x2804,
        "vbi3": 0x2806,
        "vbi4": 0x2808,
        "dead_begin": 0x2810,
        "dead_at_bottom": 0x2812,
        "dead_falling": 0x2814,
        "gameloop": 0x283b,
        "out_of_lives": 0x2840,
        "level_complete": 0x2844,
        "collect_callback": 0x2849,
    }

    vector_defaults = {
        0x2802: 0x311b,
        0x2804: 0x311b,
        0x2806: 0x311b,
        0x2808: 0x49a0,
        0x2810: 0x4200,
        0x2812: 0x4580,
        0x2814: 0x311b,
        0x2816: 0x30e0,
        0x283b: 0x2860,
        0x2840: 0x4ffd,
        0x2844: 0x4c00,
        0x2849: 0x284b,
    }

    std_gameloop = [ord(x) for x in " \xd0I \x00K\xad>(\xc9\x00\xf0\x11\xad\xbe0\xc9\x08\x90\xef\xad\xf00\xc9\xff\xd0\xe5L?(lD("]

    def __init__(self, filename):
        # raise ImportError and let caller handle it
        from pyatasm import Assemble
        asm = Assemble(filename)
        if not asm:
            raise SyntaxError(asm.errors)
        self.filename = filename
        self.asm = asm
        self.ranges = []
        self.data = []
        self.labels_used = {}
        self.vector_labels_used = {}
        self.vectors_used = set()
        self.triggers = {}
        self.custom_gameloop = False
        self.parse()

    @property
    def info(self):
        ranges = []
        total = 0
        for first, last, raw in self.asm.segments:
            ranges.append("$%04x-$%04x" % (first, last))
            total += len(raw)
        return f"""\
{self.filename}
Total bytes: {total} (${total:x})
Ranges: {",".join(ranges)}
Game loop: {"Custom" if self.custom_gameloop else "Standard"}
"""

    @property
    def vector_summary(self):
        summary = []
        for name, addr in self.vector_storage.items():
            summary.append((addr, self.vector_labels_used.get(name, self.vector_defaults[addr]), name))
        print(summary)
        summary.sort()
        return "\n".join(["$%04x    %s = $%04x" % (addr, name, subroutine) for addr, subroutine, name in summary]) + "\n"

    @property
    def coin_trigger_summary(self):
        t = sorted(["$%04x    %s" % (addr, name) for name, addr in self.triggers.items()])
        if not t:
            t = ["No trigger functions defined"]
        return "\n".join(t) + "\n"

    @property
    def label_summary(self):
        t = sorted(["$%04x    %s" % (addr, name) for name, addr in self.labels_used.items()])
        if not t:
            t = ["No labels defined"]
        return "\n".join(t) + "\n"

    def add_vector(self, vector, subroutine):
        self.vectors_used.add(vector)
        self.ranges.append((vector, vector + 2))
        hi, lo = divmod(subroutine, 256)
        self.data.extend([lo, hi])

    def parse(self):
        for first, last, raw in self.asm.segments:
            self.ranges.append((first, last))
            self.data.extend(raw)
        for label, addr in self.asm.labels.items():
            if label in self.vector_storage:
                self.vector_labels_used[label] = addr
                vector = self.vector_storage[label]
                self.add_vector(vector, addr)
            elif label.startswith("trigger"):
                self.triggers[label] = addr
            else:
                self.labels_used[label] = addr

        # force unused labels to revert to default values. This is needed, for
        # example, to overwrite a label that is unused in the current
        # development iteration but was present in the prior iteration. Without
        # overwriting this, the old vector would still be present in the data
        # and it would get called even though the current code doesn't use that
        # vector.
        for vector, default in self.vector_defaults.items():
            if vector in self.vectors_used:
                continue
            self.add_vector(vector, default)

        # check for a gameloop, otherwise add the standard gameloop
        if "gameloop" not in self.labels_used:
            vector = self.vector_storage["gameloop"]
            first = 0x2860
            self.add_vector(vector, first)
            last = first + len(self.std_gameloop)
            self.ranges.append((first, last))
            self.data.extend(self.std_gameloop)
        else:
            self.custom_gameloop = True

    def get_ranges(self, segment):
        ranges = []
        for first, last in self.ranges:
            ranges.append((first - segment.origin, last - segment.origin))

        return ranges, self.data
