import bisect
import cStringIO

import numpy as np

from errors import *
from utils import to_numpy, to_numpy_list

user_bit_mask = 0x07
not_user_bit_mask = 0xff ^ user_bit_mask
diff_bit_mask = 0x08
match_bit_mask = 0x10
comment_bit_mask = 0x20
data_bit_mask = 0x40
selected_bit_mask = 0x80


class SegmentSaver(object):
    export_data_name = "Raw Data"
    export_extensions = [".dat"]
    
    @classmethod
    def encode_data(cls, segment):
        return segment.tostring()


class OrderWrapper(object):
    """Wrapper for numpy data so that manipulations can use normal numpy syntax
    and still affect the data according to the byte ordering.
    
    Numpy's fancy indexing can't be used for setting set values, so this
    intermediate layer is needed that defines the __setitem__ method that
    explicitly references the byte ordering in the data array.
    """
    def __init__(self, data, byte_order):
        self.np_data = data
        self.base = data.base  # base array for numpy bounds determination
        self.order = byte_order
    
    def __len__(self):
        return np.alen(self.order)
    
    def __and__(self, other):
        return self.np_data[self.order] & other
    
    def __iand__(self, other):
        self.np_data[self.order] &= other
        return self
    
    def __getitem__(self, index):
        return self.np_data[self.order[index]]
    
    def __setitem__(self, index, value):
        self.np_data[self.order[index]] = value
    
    def sub_index(self, index):
        """Return index of index so it can be used directly in a new
        SegmentData object, rather than propagating multiple index lookups by
        contructing a new OrderWrapper that calls parent OrderWrapper objects.
        """
        return self.order[index]


class SegmentData(object):
    def __init__(self, data, style=None, comments=None, debug=False, order=None):
        """Storage for raw data
        
        order is a list into the base array's data; each item in the list is an
        index of the base array. E.g. if the base array is the 20 element list
        containing the data [100, 101, ... 119] and the order is [10, 0, 5, 2],
        the segment data used is [110, 100, 105, 102]
        """
        self.order = order
        self.is_indexed = order is not None
        if self.is_indexed:
            self.data = OrderWrapper(data, order)
        else:
            self.data = to_numpy(data)
        if style is None:
            if debug:
                self.style = np.arange(len(self), dtype=np.uint8)
            else:
                self.style = np.zeros(len(self), dtype=np.uint8)
        else:
            if self.is_indexed:
                self.style = OrderWrapper(style, order)
            else:
                self.style = style
        if comments is None:
            comments = dict()
        self.comments = comments
        self.reverse_index_mapping = None
    
    def __str__(self):
        return "SegmentData id=%x indexed=%s data=%s" % (id(self), self.is_indexed, type(self.data))
    
    def __len__(self):
        return len(self.data)

    @property
    def stringio(self):
        buf = cStringIO.StringIO(self.data[:])
        return buf
    
    def get_data(self):
        return self.data
    
    def get_style(self):
        return self.style
    
    def get_comments(self):
        return self.comments
    
    def byte_bounds_offset(self):
        """Return start and end offsets of this segment's data into the
        base array's data.
        
        This ignores the byte order index. Arrays using the byte order index
        will have the entire base array's raw data.
        """
        if self.data.base is None:
            if self.is_indexed:
                basearray = self.data.np_data
            else:
                basearray = self.data
            return 0, len(basearray)
        data_start, data_end = np.byte_bounds(self.data)
        base_start, base_end = np.byte_bounds(self.data.base)
        return int(data_start - base_start), int(data_end - base_start)
    
    def get_raw_index(self, i):
        """Get index into base array's raw data, given the index into this
        segment
        """
        if self.is_indexed:
            return int(self.order[i])
        if self.data.base is None:
            return int(i)
        data_start, data_end = np.byte_bounds(self.data)
        base_start, base_end = np.byte_bounds(self.data.base)
        return int(data_start - base_start + i)
    
    def get_indexes_from_base(self):
        """Get array of indexes from the base array, as if this raw data were
        indexed. 
        """
        if self.is_indexed:
            return np.copy(self.order[i])
        if self.data.base is None:
            i = 0
        else:
            i = self.get_raw_index(0)
        return np.arange(i, i + len(self), dtype=np.uint32)
    
    def __getitem__(self, index):
        if self.is_indexed:
            order = self.data.sub_index(index)
            d = self.data.np_data
            s = self.style.np_data
        else:
            order = None
            d = self.data[index]
            s = self.style[index]
        c = self.comments
        return SegmentData(d, s, c, order=order)
    
    def get_bases(self):
        if self.data.base is None:
            data_base = self.data
            style_base = self.style
        else:
            data_base = self.data.base
            style_base = self.style.base
        return data_base, style_base
    
    def get_indexed(self, index):
        index = to_numpy_list(index)
        if self.is_indexed:
            return self[index]
        
        # check to make sure all indexes are valid, raises IndexError if not
        check = self.data[index]
        
        # index needs to be relative to the base array
        base_index = index + self.get_raw_index(0)
        data_base, style_base = self.get_bases()
        return SegmentData(data_base, style_base, self.comments, order=base_index)
    
    def get_reverse_index(self, base_index):
        """Get index into this segment's data given the index into the base data
        
        Raises IndexError if the base index doesn't map to anything in this
        segment's data
        """
        if not self.reverse_index_mapping:
            self.reverse_index_mapping = dict([(k,i) for i,k in enumerate(self.order)])
        try:
            return self.reverse_index_mapping[base_index]
        except KeyError:
            raise IndexError("index %d not mapped in this segment" % base_index)


class DefaultSegment(object):
    savers = [SegmentSaver]
    
    def __init__(self, rawdata, start_addr=0, name="All", error=None, verbose_name=None):
        self.start_addr = int(start_addr)  # force python int to decouple from possibly being a numpy datatype
        self.set_raw(rawdata)
        self.error = error
        self.name = name
        self.verbose_name = verbose_name
        self.page_size = -1
        self.map_width = 40
    
    def set_raw(self, rawdata):
        self.rawdata = rawdata
        self.data = rawdata.get_data()
        self.style = rawdata.get_style()
        self._search_copy = None
    
    def get_raw(self):
        return self.rawdata
    
    def __getstate__(self):
        state = dict()
        for key in ['start_addr', 'error', 'name', 'verbose_name', 'page_size', 'map_width']:
            state[key] = getattr(self, key)
        r = self.rawdata
        state['_rawdata_bounds'] = list(r.byte_bounds_offset())
        if r.is_indexed:
            state['_order_list'] = r.order.tolist()  # more compact serialization in python list
        else:
            state['_order_list'] = None
        return state
    
    def reconstruct_raw(self, rawdata):
        start, end = self._rawdata_bounds
        r = rawdata[start:end]
        delattr(self, '_rawdata_bounds')
        try:
            if self._order_list:
                order = to_numpy_list(self._order_list)
                r = r.get_indexed(order)
                delattr(self, '_order_list')
        except AttributeError:
            pass
        self.set_raw(r)
    
    def get_parallel_raw_data(self, other):
        """ Get the raw data that is similar to the specified other segment
        """
        start, end = other.byte_bounds_offset()
        r = self.rawdata[start:end]
        if other.rawdata.is_indexed:
            r = r.get_indexed[other.order]
        return r
    
    def __str__(self):
        s = "%s ($%x bytes)" % (self.name, len(self))
        if self.error:
            s += " " + self.error
        return s
    
    @property
    def verbose_info(self):
        name = self.verbose_name or self.name
        if self.rawdata.is_indexed:
            s = "%s ($%04x bytes) non-contiguous file; file index of first byte: $%04x" % (name, len(self), self.rawdata.order[0])
        else:
            s = "%s ($%04x bytes)" % (name, len(self))
        if self.error:
            s += "  error='%s'" % self.error
        return s
    
    def __len__(self):
        return len(self.rawdata)
    
    def __getitem__(self, index):
        return self.data[index]
    
    def __setitem__(self, index, value):
        self.data[index] = value
        self._search_copy = None
    
    def byte_bounds_offset(self):
        """Return start and end offsets of this segment's data into the
        base array's data
        """
        return self.rawdata.byte_bounds_offset()
    
    def is_valid_index(self, i):
        return i >= 0 and i < len(self)
    
    def get_raw_index(self, i):
        """Get index into base array's raw data, given the index into this
        segment
        """
        return self.rawdata.get_raw_index(i)
    
    def get_index_from_base_index(self, base_index):
        """Get index into this array's data given the index into the base array
        """
        r = self.rawdata
        if r.is_indexed:
            index = r.get_reverse_index(base_index)
        else:
            index = base_index - r.get_raw_index(0)
            if not self.is_valid_index(index):
                raise IndexError("index %d not in this segment" % base_index)
        return index

    def tostring(self):
        return self.data.tostring()
    
    def get_style_bits(self, match=False, comment=False, selected=False, data=False, diff=False, user=0):
        """ Return an int value that contains the specified style bits set.
        
        Available styles for each byte are:
        
        match: part of the currently matched search
        comment: user commented area
        selected: selected region
        data: labeled in the disassembler as a data region (i.e. not disassembled)
        """
        style_bits = 0
        if user:
            style_bits |= (user & user_bit_mask)
        if diff:
            style_bits |= diff_bit_mask
        if match:
            style_bits |= match_bit_mask
        if comment:
            style_bits |= comment_bit_mask
        if data:
            style_bits |= data_bit_mask
        if selected:
            style_bits |= selected_bit_mask
        return style_bits
    
    def get_style_mask(self, **kwargs):
        """Get the bit mask that, when anded with data, will turn off the
        selected bits
        """
        bits = self.get_style_bits(**kwargs)
        if 'user' in kwargs and kwargs['user']:
            bits |= user_bit_mask
        else:
            bits &= (0xff ^ user_bit_mask)
        return 0xff ^ bits
    
    def set_style_ranges(self, ranges, **kwargs):
        style_bits = self.get_style_bits(**kwargs)
        s = self.style
        for start, end in ranges:
            if end < start:
                start, end = end, start
            s[start:end] |= style_bits
    
    def clear_style_ranges(self, ranges, **kwargs):
        style_mask = self.get_style_mask(**kwargs)
        s = self.style
        for start, end in ranges:
            if end < start:
                start, end = end, start
            s[start:end] &= style_mask
    
    def get_style_ranges(self, **kwargs):
        style_bits = self.get_style_bits(**kwargs)
        matches = (self.style & style_bits) == style_bits
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
    
    def find_next(self, index, **kwargs):
        ranges = self.get_style_ranges(**kwargs)
        if len(ranges) > 0:
            index_tuple = (index + 1, 0)
            match_index = bisect.bisect_right(ranges, index_tuple)
            if match_index >= len(ranges):
                match_index = 0
            return ranges[match_index][0]
        return None
    
    def find_previous(self, index, **kwargs):
        ranges = self.get_style_ranges(**kwargs)
        if len(ranges) > 0:
            index_tuple = (index - 1, 0)
            match_index = bisect.bisect_left(ranges, index_tuple)
            match_index -= 1
            if match_index < 0:
                match_index = len(ranges) - 1
            return ranges[match_index][0]
        return None
    
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
    
    def set_comment(self, ranges, text):
        self.set_style_ranges(ranges, comment=True)
        for start, end in ranges:
            rawindex = self.get_raw_index(start)
            self.rawdata.comments[rawindex] = text
    
    def get_comment(self, index):
        rawindex = self.get_raw_index(index)
        return self.rawdata.comments.get(rawindex, "")
    
    def get_first_comment(self, ranges):
        start = reduce(min, [r[0] for r in ranges])
        rawindex = self.get_raw_index(start)
        return self.rawdata.comments.get(rawindex, "")
    
    def clear_comment(self, ranges):
        self.clear_style_ranges(ranges, comment=True)
        for start, end in ranges:
            rawindex = self.get_raw_index(start)
            if rawindex in self.rawdata.comments:
                del self.rawdata.comments[rawindex]
    
    def get_sorted_comments(self):
        return sorted([[k, v] for k, v in self.rawdata.comments.iteritems()])
    
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
    
    def compare_segment(self, other_segment):
        self.clear_style_bits(diff=True)
        diff = self.rawdata.data != other_segment.rawdata.data
        print diff, diff.dtype
        d = diff * np.uint8(diff_bit_mask)
        print d
        self.style |= (diff * np.uint8(diff_bit_mask))
        print "# entries", len(diff), "# diffs:", len(np.where(diff == True)[0])


class EmptySegment(DefaultSegment):
    def __init__(self, rawdata, name="", error=None):
        DefaultSegment.__init__(self, rawdata, 0, name, error)
    
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
    def __init__(self, rawdata, metadata_start, data_start, start_addr, end_addr=0,  name="", **kwargs):
        DefaultSegment.__init__(self, rawdata, start_addr, name, **kwargs)
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
    def __init__(self, rawdata, first_sector, num_sectors, count, boot_sector_size, num_boot_sectors, sector_size, **kwargs):
        DefaultSegment.__init__(self, rawdata, 0, **kwargs)
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

def interleave_indexes(segments, num_bytes):
    num_segments = len(segments)
    size = len(segments[0])
    for s in segments[1:]:
        if size != len(s):
            raise ValueError("All segments to interleave must be the same size")
    _, rem = divmod(size, num_bytes)
    if rem != 0:
        raise ValueError("Segment size must be a multiple of the byte interleave")
    interleave = np.empty(size * num_segments, dtype=np.uint32)
    factor = num_bytes * num_segments
    start = 0
    for s in segments:
        order = s.rawdata.get_indexes_from_base()
        for i in range(num_bytes):
            interleave[start::factor] = order[i::num_bytes]
            start += 1
    return interleave

def interleave_segments(segments, num_bytes):
    new_index = interleave_indexes(segments, num_bytes)
    data_base, style_base = segments[0].rawdata.get_bases()
    for s in segments[1:]:
        d, s = s.rawdata.get_bases()
        if id(d) != id(data_base) or id(s) != id(style_base):
            raise ValueError("Can't interleave segments with different base arrays")
    raw = SegmentData(data_base, style_base, segments[0].rawdata.comments, order=new_index)
    segment = DefaultSegment(raw, 0)
    return segment
