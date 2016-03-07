import numpy as np

from errors import *
from utils import to_numpy_list


class SegmentSaver(object):
    name = "Raw Data"
    extensions = [".dat"]
    
    @classmethod
    def encode_data(cls, segment):
        return segment.tostring()

    @classmethod
    def get_file_dialog_wildcard(cls):
        # Using only the first extension
        wildcards = []
        if cls.extensions:
            ext = cls.extensions[0]
            wildcards.append("%s (*%s)|*%s" % (cls.name, ext, ext))
        return "|".join(wildcards)


class DefaultSegment(object):
    savers = [SegmentSaver]
    
    def __init__(self, data, style, start_addr=0, name="All", error=None, verbose_name=None):
        self.start_addr = int(start_addr)  # force python int to decouple from possibly being a numpy datatype
        self.data = data
        self.style = style
        self.error = error
        self.name = name
        self.verbose_name = verbose_name
        self.page_size = -1
        self.map_width = 40
        self._search_copy = None
    
    def __str__(self):
        s = "%s ($%x bytes)" % (self.name, len(self))
        if self.error:
            s += " " + self.error
        return s
    
    @property
    def verbose_info(self):
        name = self.verbose_name or self.name
        s = "%s ($%x bytes)" % (name, len(self))
        if self.error:
            s += "  error='%s'" % self.error
        return s
    
    def __len__(self):
        return np.alen(self.data)
    
    def __getitem__(self, index):
        return self.data[index]
    
    def __setitem__(self, index, value):
        self.data[index] = value
        self._search_copy = None
    
    def byte_bounds_offset(self):
        return np.byte_bounds(self.data)[0]

    def tostring(self):
        return self.data.tostring()
    
    def get_style_bits(self, match=False, comment=False, selected=False, data=False):
        """ Return an int value that contains the specified style bits set.
        
        Available styles for each byte are:
        
        match: part of the currently matched search
        comment: user commented area
        selected: selected region
        data: labeled in the disassembler as a data region (i.e. not disassembled)
        """
        style_bits = 0
        if match:
            style_bits |= 1
        if comment:
            style_bits |= 2
        if data:
            style_bits |= 4
        if selected:
            style_bits |= 0x80
        return style_bits
    
    def get_style_mask(self, **kwargs):
        return 0xff ^ self.get_style_bits(**kwargs)
    
    def set_style_ranges(self, ranges, **kwargs):
        style_bits = self.get_style_bits(**kwargs)
        s = self.style
        for start, end in ranges:
            if end < start:
                start, end = end, start
            s[start:end] |= style_bits
    
    def get_style_ranges(self, **kwargs):
        style_bits = self.get_style_bits(**kwargs)
        matches = (self.style & style_bits) > 0
        return self.bool_to_ranges(matches)
    
    def bool_to_ranges(self, matches):
        w = np.where(matches == True)[0]
        # split into groups with consecutive numbers
        groups = np.split(w, np.where(np.diff(w) != 1)[0] + 1)
        ranges = []
        for group in groups:
            if np.alen(group) > 0:
                ranges.append((int(group[0]), int(group[-1]) + 1))
        return ranges
    
    def get_rect_indexes(self, anchor_start, anchor_end):
        # determine row,col of upper left and lower right of selected
        # rectangle.  The values are inclusive, so ul=(0,0) and lr=(1,2)
        # is 2 rows and 3 columns.  Columns need to be adjusted slightly
        # depending on quadrant of selection because anchor indexes are
        # measured as cursor positions, that is: positions between the
        # bytes where as rect select needs to think of the selections as
        # on the byte positions themselves, not in between.
        bpr = self.map_width
        r1, c1 = divmod(anchor_start, bpr)
        r2, c2 = divmod(anchor_end, bpr)
        if c1 >= c2:
            # start column is to the right of the end column so columns
            # need to be swapped
            if r1 >= r2:
                # start row is below end row, so rows swapped as well
                c1, c2 = c2, c1 + 1
                r1, r2 = r2, r1
            elif c2 == 0:
                # When the cursor is at the end of a line, anchor_end points
                # to the first character of the next line.  Handle this
                # special case by pointing to end of the previous line.
                c2 = bpr
                r2 -= 1
            else:
                c1, c2 = c2 - 1, c1 + 1
        else:
            # start column is to the left of the end column, so don't need
            # to swap columns
            if r1 > r2:
                # start row is below end row
                r1, r2 = r2, r1
                c2 += 1
        anchor_start = r1 * bpr + c1
        anchor_end = r2 * bpr + c2
        r2 += 1
        return anchor_start, anchor_end, (r1, c1), (r2, c2)
    
    def set_style_ranges_rect(self, ranges, **kwargs):
        style_bits = self.get_style_bits(**kwargs)
        s = self.style
        for start, end in ranges:
            start, end, (r1, c1), (r2, c2) = self.get_rect_indexes(start, end)
            # Numpy tricks!
            # >>> c1 = 15
            # >>> r = 4 # r2 - r1
            # >>> c = 10 # c2 - c1
            # >>> width = 40
            # >>> np.arange(c)
            #array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
            # >>> np.arange(r) * width
            #array([  0,  40,  80, 120])
            # >>> np.tile(np.arange(c), r) + np.repeat(np.arange(r)*width, c)
            #array([  0,   1,   2,   3,   4,   5,   6,   7,   8,   9,  40,  41,  42,
            #        43,  44,  45,  46,  47,  48,  49,  80,  81,  82,  83,  84,  85,
            #        86,  87,  88,  89, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129])
            # >>> np.tile(np.arange(c), r) + np.repeat(np.arange(r)*width, c) + c1
            #array([ 15,  16,  17,  18,  19,  20,  21,  22,  23,  24,  55,  56,  57,
            #        58,  59,  60,  61,  62,  63,  64,  95,  96,  97,  98,  99, 100,
            #       101, 102, 103, 104, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144])
            r = r2 - r1
            c = c2 - c1
            indexes = np.tile(np.arange(c), r) + np.repeat(np.arange(r) * self.map_width, c) + start
            s[indexes] |= style_bits
    
    def rects_to_ranges(self, rects):
        ranges = []
        bpr = self.map_width
        for (r1, c1), (r2, c2) in rects:
            start = r1 * bpr + c1
            end = (r2 - 1) * bpr + c2
            ranges.append((start, end))
        return ranges
    
    def clear_style_bits(self, **kwargs):
        style_mask = self.get_style_mask(**kwargs)
        self.style &= style_mask
    
    def label(self, index, lower_case=True):
        if lower_case:
            return "%04x" % (index + self.start_addr)
        else:
            return "%04X" % (index + self.start_addr)
    
    @property
    def search_copy(self):
        if self._search_copy is None:
            self._search_copy = self.data.tostring()
        return self._search_copy


class EmptySegment(DefaultSegment):
    def __init__(self, data, style, name="", error=None):
        DefaultSegment.__init__(self, data, style, 0, name, error)
    
    def __str__(self):
        s = "%s (empty file)" % (self.name, )
        if self.error:
            s += " " + self.error
        return s
    
    @property
    def verbose_info(self):
        s = "%s (empty file)" % (self.name, )
        if self.error:
            s += "  error='%s'" % self.error
        return s
    
    def __len__(self):
        return 0


class ObjSegment(DefaultSegment):
    def __init__(self, data, style, metadata_start, data_start, start_addr, end_addr,  name="", **kwargs):
        DefaultSegment.__init__(self, data, style, start_addr, name, **kwargs)
        self.metadata_start = metadata_start
        self.data_start = data_start
    
    def __str__(self):
        count = len(self)
        s = "%s $%04x-$%04x ($%04x @ $%04x)" % (self.name, self.start_addr, self.start_addr + count, count, self.data_start)
        if self.error:
            s += " " + self.error
        return s
    
    @property
    def verbose_info(self):
        count = len(self)
        name = self.verbose_name or self.name
        s = "%s  address range: $%04x-$%04x ($%04x bytes), file index of first byte: $%04x" % (name, self.start_addr, self.start_addr + count, count, self.data_start)
        if self.error:
            s += "  error='%s'" % self.error
        return s


class RawSectorsSegment(DefaultSegment):
    def __init__(self, data, style, first_sector, num_sectors, count, boot_sector_size, num_boot_sectors, sector_size, **kwargs):
        DefaultSegment.__init__(self, data, style, 0, **kwargs)
        self.boot_sector_size = boot_sector_size
        self.num_boot_sectors = num_boot_sectors
        self.page_size = sector_size
        self.first_sector = first_sector
        self.num_sectors = num_sectors
    
    def __str__(self):
        if self.num_sectors > 1:
            s = "%s (sectors %d-%d)" % (self.name, self.first_sector, self.first_sector + self.num_sectors - 1)
        else:
            s = "%s (sector %d)" % (self.name, self.first_sector)
        if self.error:
            s += " " + self.error
        return s
    
    @property
    def verbose_info(self):
        name = self.verbose_name or self.name
        if self.num_sectors > 1:
            s = "%s (sectors %d-%d)" % (name, self.first_sector, self.first_sector + self.num_sectors - 1)
        else:
            s = "%s (sector %d)" % (name, self.first_sector)
        s += " $%x bytes" % (len(self), )
        if self.error:
            s += "  error='%s'" % self.error
        return s
    
    def label(self, index, lower_case=True):
        boot_size = self.num_boot_sectors * self.boot_sector_size
        if index >= boot_size:
            sector, byte = divmod(index - boot_size, self.page_size)
            sector += self.num_boot_sectors
        else:
            sector, byte = divmod(index, self.boot_sector_size)
        if lower_case:
            return "s%03d:%02x" % (sector + self.first_sector, byte)
        return "s%03d:%02X" % (sector + self.first_sector, byte)


class IndexedStyleWrapper(object):
    """Wrapper for style data so that style manipulations can use normal
    numpy syntax and still affect the style according to the byte ordering
    """
    def __init__(self, style, byte_order):
        self.style = style
        self.order = byte_order
    
    def __len__(self):
        return np.alen(self.order)
    
    def __and__(self, other):
        return self.style[self.order] & other
    
    def __iand__(self, other):
        self.style[self.order] &= other
        return self
    
    def __getitem__(self, index):
        return self.style[self.order[index]]
    
    def __setitem__(self, index, value):
        self.style[self.order[index]] = value


class IndexedByteSegment(DefaultSegment):
    def __init__(self, data, style, byte_order, **kwargs):
        # Convert to numpy list so fancy indexing works as argument to __getitem__
        self.order = to_numpy_list(byte_order)
        DefaultSegment.__init__(self, data, IndexedStyleWrapper(style, byte_order), 0, **kwargs)
    
    def __str__(self):
        s = "%s ($%x @ $%x)" % (self.name, len(self), self.order[0])
        if self.error:
            s += " " + self.error
        return s
    
    @property
    def verbose_info(self):
        name = self.verbose_name or self.name
        s = "%s ($%04x bytes) non-contiguous file; file index of first byte: $%04x" % (name, len(self), self.order[0])
        if self.error:
            s += "  error='%s'" % self.error
        return s
    
    def __len__(self):
        return np.alen(self.order)
    
    def __getitem__(self, index):
        return self.data[self.order[index]]
    
    def __setitem__(self, index, value):
        self.data[self.order[index]] = value
        self._search_copy = None
    
    def byte_bounds_offset(self):
        return np.byte_bounds(self.data)[0] + self.order[0]
    
    def tostring(self):
        return self.data[self.order[:]].tostring()
