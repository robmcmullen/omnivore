import bisect
import io

import numpy as np

from . import errors
from .utils import to_numpy, to_numpy_list, uuid
from functools import reduce

user_bit_mask = 0x07
data_style = 0x1
not_user_bit_mask = 0xff ^ user_bit_mask
diff_bit_mask = 0x10
match_bit_mask = 0x20
comment_bit_mask = 0x40
selected_bit_mask = 0x80

import logging
log = logging.getLogger(__name__)


def get_style_bits(match=False, comment=False, selected=False, data=False, diff=False, user=0):
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
        style_bits |= (data_style & user_bit_mask)
    if selected:
        style_bits |= selected_bit_mask
    return style_bits


def get_style_mask(**kwargs):
    """Get the bit mask that, when anded with data, will turn off the
    selected bits
    """
    bits = get_style_bits(**kwargs)
    if 'user' in kwargs and kwargs['user']:
        bits |= user_bit_mask
    else:
        bits &= (0xff ^ user_bit_mask)
    return 0xff ^ bits


class SegmentSaver:
    export_data_name = "Raw Data"
    export_extensions = [".dat"]

    @classmethod
    def encode_data(cls, segment, ui_control):
        return segment.tobytes()


class BSAVESaver:
    export_data_name = "Apple ][ Binary"
    export_extensions = [".bsave"]

    @classmethod
    def encode_data(cls, segment, ui_control):
        data = segment.tobytes()
        header = np.empty(2, dtype="<u2")
        header[0] = segment.origin
        header[1] = len(data)
        print("binary data: %x bytes at %x" % (header[1], header[0]))
        return header.tobytes() + segment.tobytes()


class OrderWrapper:
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

    def __str__(self):
        return f"OrderWrapper at {hex(id(self))} count={len(self)} order={self.order} base: count={len(self.np_data)}"

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

    @property
    def shape(self):
        return (len(self),)

    @property
    def unindexed(self):
        return self.np_data[self.order]

    def tobytes(self):
        return self.np_data[self.order].tobytes()


class UserExtraData:
    def __init__(self):
        self.comments = dict()
        self.user_data = dict()
        for i in range(1, user_bit_mask):
            self.user_data[i] = dict()


class SegmentData:
    def __init__(self, data, style=None, extra=None, debug=False, order=None):
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
        self.calc_lookups()
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
        if extra is None:
            extra = UserExtraData()
        self.extra = extra

    def __str__(self):
        return "SegmentData id=%x indexed=%s data=%s len=%s" % (id(self), self.is_indexed, type(self.data), len(self.data))

    def __len__(self):
        return self.data_length

    def resize(self, newsize):
        if self.data.base is None:
            try:
                newdata = np.resize(self.data, (newsize,))
                newstyle = np.resize(self.style, (newsize,))
            except:
                raise
            else:
                self.data = newdata
                self.style = newstyle
        else:
            raise ValueError("Can't resize a view of a segment")
        self.calc_lookups()

    def replace_arrays(self, base_raw):
        newsize = len(base_raw)
        oldsize = len(self.data_base)
        if newsize < oldsize:
            raise errors.NotImplementedError("Can't truncate yet")
        if self.is_indexed:
            self.data.np_data = base_raw.data
            self.data.base = base_raw.data.base
            self.style.np_data = base_raw.style
            self.style.base = base_raw.style.base
        elif self.data.base is not None:
            # if there is no base array, we aren't looking at a slice so we
            # must be copying the entire array.
            start, end = self.byte_bounds_offset()
            self.data = base_raw.data[start:end]
            self.style = base_raw.style[start:end]
        else:
            raise ValueError("The base SegmentData object should use the resize method to replace arrays")
        self.calc_lookups()

    def calc_lookups(self):
        if self.is_indexed:
            end = len(self.data.np_data)
            self.data_start, self.data_end = 0, end
            self.base_start, self.base_end = 0, end
            base_size = end
        elif self.data.base is None:
            end = len(self.data)
            self.data_start, self.data_end = 0, end
            self.base_start, self.base_end = 0, end
            base_size = end
        else:
            self.data_start, self.data_end = np.byte_bounds(self.data)
            self.base_start, self.base_end = np.byte_bounds(self.data.base)
            base_size = len(self.data.base)
        self.base_length = base_size
        self.data_length = len(self.data)
        # Force regeneration of reverse index mapping the next time it's needed
        self._reverse_index_mapping = None

    @property
    def bufferedio(self):
        buf = io.BytesIO(self.data[:])
        return buf

    @property
    def is_base(self):
        return not self.is_indexed and self.data.base is None

    @property
    def data_base(self):
        return self.data.np_data if self.is_indexed else self.data.base if self.data.base is not None else self.data

    @property
    def style_base(self):
        return self.style.np_data if self.is_indexed else self.style.base if self.style.base is not None else self.style

    def get_data(self):
        return self.data

    def get_style(self):
        return self.style

    @property
    def unindexed_data(self):
        if self.is_indexed:
            return self.data.unindexed
        return self.data

    @property
    def unindexed_style(self):
        if self.is_indexed:
            return self.style.unindexed
        return self.style

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
        return int(self.data_start - self.base_start), int(self.data_end - self.base_start)

    def get_raw_index(self, i):
        """Get index into base array's raw data, given the index into this
        segment
        """
        if self.is_indexed:
            return int(self.order[i])
        if self.data.base is None:
            return int(i)
        return int(self.data_start - self.base_start + i)

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
        e = self.extra
        return SegmentData(d, s, e, order=order)

    def copy(self):
        if self.is_indexed:
            d = self.data.np_data.copy()
            s = self.style.np_data.copy()
            copy = SegmentData(d, s, order=self.order)
        elif self.data.base is None:
            # if there is no base array, we aren't looking at a slice so we
            # must be copying the entire array.
            d = self.data.copy()
            s = self.style.copy()
            copy = SegmentData(d, s)
        else:
            d = self.data.base.copy()
            s = self.style.base.copy()
            start, end = self.byte_bounds_offset()
            copy = SegmentData(d[start:end], s[start:end])
        return copy

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
        return SegmentData(data_base, style_base, self.extra, order=base_index)

    @property
    def reverse_index_mapping(self):
        """Get mapping from this segment's indexes to the indexes of
        the base array.

        If the index is < 0, the index is out of range, meaning that it doesn't
        exist in this segment and is not mapped to the base array
        """
        if self._reverse_index_mapping is None:
            if self.is_indexed:
                # Initialize array to out of range
                r = np.zeros(self.base_length, dtype=np.int32) - 1
                r[self.order] = np.arange(len(self.order), dtype=np.int32)
            elif self.data.base is None:
                # Starts at the beginning; produces the identity
                r = np.arange(self.data_length, dtype=np.int32)
            else:
                r = np.zeros(self.base_length, dtype=np.int32) - 1
                r[self.data_start - self.base_start:self.data_end - self.base_start] = np.arange(self.data_length, dtype=np.int32)
            self._reverse_index_mapping = r
        return self._reverse_index_mapping

    def get_reverse_index(self, base_index):
        """Get index into this segment's data given the index into the base data

        Raises IndexError if the base index doesn't map to anything in this
        segment's data
        """
        r = self.reverse_index_mapping[base_index]
        if r < 0:
            raise IndexError("index %d not mapped in this segment" % base_index)
        return r


class DefaultSegment:
    savers = [SegmentSaver, BSAVESaver]
    can_resize_default = False

    base_serializable_attributes = ['origin', 'error', 'name', 'verbose_name', 'page_size', 'map_width', 'uuid', 'can_resize']
    extra_serializable_attributes = []

    def __init__(self, rawdata, origin=0, name="All", error=None, verbose_name=None, memory_map=None):
        self.origin = int(origin)  # force python int to decouple from possibly being a numpy datatype
        self.set_raw(rawdata)
        self.error = error
        self.name = name
        self.verbose_name = verbose_name
        self.page_size = -1
        self.map_width = 40
        self.uuid = uuid()
        if memory_map is None:
            memory_map = {}
        self.memory_map = memory_map

        # Some segments may be resized to contain additional segments not
        # present when the segment was created.
        self.can_resize = self.__class__.can_resize_default

    def set_raw(self, rawdata):
        if type(rawdata) != SegmentData:
            log.warning(f"data not in SegmentData format: {type(rawdata)}")
            rawdata = SegmentData(rawdata)
        self.rawdata = rawdata
        self.update_raw_pointers()

    def get_raw(self):
        return self.rawdata

    def update_raw_pointers(self):
        self.data = self.rawdata.get_data()
        self.style = self.rawdata.get_style()
        self._search_copy = None

    def resize(self, newsize, zeros=True):
        """ Resize the data arrays.

        This can only be performed on the container segment. Child segments
        must adjust their rawdata to point to the correct place.

        Since segments don't keep references to other segments, it is the
        user's responsibility to update any child segments that point to this
        segment's data.

        Numpy can't do an in-place resize on an array that has a view, so the
        data must be replaced and all segments that point to that raw data must
        also be changed. This has to happen outside this method because it
        doesn't know the segment list of segments using itself as a base.
        """
        if not self.can_resize:
            raise ValueError("Segment %s can't be resized" % str(self))
        # only makes sense for the container (outermost) object
        if not self.rawdata.is_base:
            raise ValueError("Only container segments can be resized")
        origsize = len(self)
        self.rawdata.resize(newsize)
        self.set_raw(self.rawdata)  # force attributes to be reset
        newsize = len(self)
        if zeros:
            if newsize > origsize:
                self.data[origsize:] = 0
                self.style[origsize:] = 0
        return origsize, newsize

    def replace_data(self, container):
        self.rawdata.replace_arrays(container.rawdata)
        self.update_raw_pointers()

    def create_subset(self, new_order, name, verbose_name=""):
        raw = self.rawdata.get_indexed(new_order)
        if not verbose_name:
            verbose_name = name
        segment = DefaultSegment(raw, name=name, verbose_name=verbose_name)
        return segment

    def __getstate__(self):
        """Custom jsonpickle state save routine

        This routine culls down the list of attributes that should be
        serialized, and in some cases changes their format slightly so they
        have a better mapping to json objects. For instance, json can't handle
        dicts with integer keys, so dicts are turned into lists of lists.
        Tuples are also turned into lists because tuples don't have a direct
        representation in json, while lists have a compact representation in
        json.
        """
        state = dict()
        for key in self.base_serializable_attributes:
            state[key] = getattr(self, key)
        for key in self.extra_serializable_attributes:
            state[key] = getattr(self, key)
        r = self.rawdata
        state['_rawdata_bounds'] = list(r.byte_bounds_offset())
        if r.is_indexed:
            state['_order_list'] = r.order.tolist()  # more compact serialization in python list
        else:
            state['_order_list'] = None
        state['memory_map'] = sorted([list(i) for i in self.memory_map.items()])
        return state

    def __setstate__(self, state):
        """Custom jsonpickle state restore routine

        The use of jsonpickle to recreate objects doesn't go through __init__,
        so there will be missing attributes when restoring old versions of the
        json. Once a version gets out in the wild and additional attributes are
        added to a segment, a default value should be applied here.
        """
        self.memory_map = dict(state.pop('memory_map', []))
        self.uuid = state.pop('uuid', uuid())
        self.can_resize = state.pop('can_resize', self.__class__.can_resize_default)
        self.restore_missing_serializable_defaults()
        self.__dict__.update(state)
        self.restore_renamed_serializable_attributes()

    def restore_missing_serializable_defaults(self):
        """Hook for the future when extra serializable attributes are added to
        subclasses so new versions of the code can restore old saved files by
        providing defaults to any missing attributes.
        """
        pass

    def restore_renamed_serializable_attributes(self):
        """Hook for the future if attributes have been renamed. The old
        attribute names will have been restored in the __dict__.update in
        __setstate__, so this routine should move attribute values to their new
        names.
        """
        if hasattr(self, 'start_addr'):
            self.origin = self.start_addr
            print(f"moving start_addr to origin: {self.start_addr}")
            delattr(self, 'start_addr')

    def reconstruct_raw(self, rawdata):
        """Reconstruct the pointers to the parent data arrays

        Each segment is a view into the primary segment's data, so those
        pointers and the order must be restored in the child segments.
        """
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

    def serialize_extra_to_dict(self, mdict):
        """Save extra metadata to a dict so that it can be serialized

        This is not saved by __getstate__ because child segments will point to
        the same data and this allows it to only be saved for the base segment.
        As well as allowing it to be pulled out of the main json so that it can
        be more easily edited by hand if desired.
        """
        mdict["comment ranges"] = [list(a) for a in self.get_style_ranges(comment=True)]
        mdict["data ranges"] = [list(a) for a in self.get_style_ranges(data=True)]
        for i in range(1, user_bit_mask):
            r = [list(a) for a in self.get_style_ranges(user=i)]
            if r:
                slot = "user style %d" % i
                mdict[slot] = r

        # json serialization doesn't allow int keys, so convert to list of
        # pairs
        mdict["comments"] = self.get_sorted_comments()

    def restore_extra_from_dict(self, e):
        if 'comments' in e:
            for k, v in e['comments']:
                self.rawdata.extra.comments[k] = v
        if 'comment ranges' in e:
            self.set_style_ranges(e['comment ranges'], comment=True)
        if 'data ranges' in e:
            self.set_style_ranges(e['data ranges'], user=data_style)
        if 'display list ranges' in e:
            # DEPRECATED, but supported on read. Converts display list to
            # disassembly type 0 for user index 1
            self.set_style_ranges(e['display list ranges'], data=True, user=1)
            self.set_user_data(e['display list ranges'], 1, 0)
        if 'user ranges 1' in e:
            # DEPRECATED, but supported on read. Converts user extra data 0
            # (antic dl), 1 (jumpman level), and 2 (jumpman harvest) to user
            # styles 2, 3, and 4. Data is now user style 1.
            for r, val in e['user ranges 1']:
                self.set_style_ranges([r], user=val + 2)
        for i in range(1, user_bit_mask):
            slot = "user style %d" % i
            if slot in e:
                self.set_style_ranges(e[slot], user=i)

    def __str__(self):
        if self.origin > 0:
            origin = " @ %04x" % (self.origin)
        else:
            origin = ""
        s = "%s ($%x bytes%s)" % (self.name, len(self), origin)
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
        return self.rawdata.data_length

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

    def get_raw_index_from_address(self, addr):
        """Get index into base array's raw data, given the address of a byte
        into this segment
        """
        return self.get_raw_index(addr - self.origin)

    def get_index_from_base_index(self, base_index):
        """Get index into this array's data given the index into the base array
        """
        r = self.rawdata
        try:
            index = r.get_reverse_index(base_index)
        except IndexError:
            raise IndexError("index %d not in this segment" % base_index)
        if index < 0:
            raise IndexError("index %d not in this segment" % base_index)
        return int(index)

    def tobytes(self):
        return self.data.tobytes()

    def get_style_bits(self, **kwargs):
        return get_style_bits(**kwargs)

    def get_style_mask(self, **kwargs):
        return get_style_mask(**kwargs)

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
        """Return a list of start, end pairs that match the specified style
        """
        style_bits = self.get_style_bits(**kwargs)
        matches = (self.style & style_bits) == style_bits
        return self.bool_to_ranges(matches)

    def fixup_comments(self):
        """Remove any style bytes that are marked as commented but have no
        comment, and add any style bytes where there's a comment but it isn't
        marked in the style data.

        This happens on the base data, so only need to do this on one segment
        that uses this base data.
        """
        style_base = self.rawdata.style_base
        comment_text_indexes = np.asarray(list(self.rawdata.extra.comments.keys()), dtype=np.uint32)
        comment_mask = self.get_style_mask(comment=True)
        has_comments = np.where(style_base & comment_bit_mask > 0)[0]
        both = np.intersect1d(comment_text_indexes, has_comments)
        log.info("fixup comments: %d correctly marked, %d without style, %d empty text" % (np.alen(both), np.alen(comment_text_indexes) - np.alen(both), np.alen(has_comments) - np.alen(both)))
        style_base &= comment_mask
        comment_style = self.get_style_bits(comment=True)
        style_base[comment_text_indexes] |= comment_style

    def get_comment_locations(self, **kwargs):
        style_bits = self.get_style_bits(**kwargs)
        r = self.rawdata.copy()
        #print len(r.style)
        #print len(r.style_base)
        r.style_base[:] &= style_bits
        comment_indexes = np.asarray(list(self.rawdata.extra.comments.keys()), dtype=np.uint32)
        #print comment_indexes
        r.style_base[comment_indexes] |= comment_bit_mask
        return r.unindexed_style[:]

    def get_entire_style_ranges(self, split_comments=None, **kwargs):
        """Find sections of the segment that have the same style value.

        The arguments to this function are used as a mask for the style to
        determine where to split the styles. Style bits that aren't included in
        the list will be ignored when splitting. The returned list covers the
        entire length of the segment.

        Returns a list of tuples, each tuple containing two items: a start, end
        tuple; and an integer with the style value.
        """
        style_bits = self.get_style_bits(**kwargs)
        matches = self.get_comment_locations(**kwargs)
        groups = np.split(matches, np.where(np.diff(matches) != 0)[0] + 1)
        if split_comments is None:
            split_comments = []
        # print groups
        # split into groups with the same numbers
        ranges = []
        last_end = 0
        if len(groups) == 1 and len(groups[0]) == 0:
            # check for degenerate case
            return
        last_style = -1
        for group in groups:
            # each group is guaranteed to have the same style
            size = len(group)
            next_end = last_end + size
            style = matches[last_end]
            masked_style = style & style_bits
            # print last_end, next_end, style, masked_style, size, group
            if style & comment_bit_mask:
                if masked_style in split_comments:
                    # print "interesting comment", last_end, next_end
                    ranges.append(((last_end, next_end), masked_style))
                else:
                    # print "non-interesting comment", last_end, next_end
                    if last_style == masked_style:
                        ((prev_end, _), _) = ranges.pop()
                        ranges.append(((prev_end, next_end), masked_style))
                    else:
                        ranges.append(((last_end, next_end), masked_style))
            else:
                if last_style == masked_style:
                    ((prev_end, _), _) = ranges.pop()
                    ranges.append(((prev_end, next_end), masked_style))
                else:
                    ranges.append(((last_end, next_end), masked_style))
            last_style = masked_style
            last_end = next_end
        return ranges

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

    def get_rect_indexes(self, anchor_start, anchor_end, bytes_per_row):
        # determine row,col of upper left and lower right of selected
        # rectangle.  The values are inclusive, so ul=(0,0) and lr=(1,2)
        # is 2 rows and 3 columns.  Columns need to be adjusted slightly
        # depending on quadrant of selection because anchor indexes are
        # measured as cursor positions, that is: positions between the
        # bytes where as rect select needs to think of the selections as
        # on the byte positions themselves, not in between.
        r1, c1 = divmod(anchor_start, bytes_per_row)
        r2, c2 = divmod(anchor_end, bytes_per_row)
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
                c2 = bytes_per_row
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
        anchor_start = r1 * bytes_per_row + c1
        anchor_end = r2 * bytes_per_row + c2
        r2 += 1
        return anchor_start, anchor_end, (r1, c1), (r2, c2)

    def set_style_ranges_rect(self, ranges, bytes_per_row, **kwargs):
        style_bits = self.get_style_bits(**kwargs)
        s = self.style
        for start, end in ranges:
            start, end, (r1, c1), (r2, c2) = self.get_rect_indexes(start, end, bytes_per_row)
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
            indexes = np.tile(np.arange(c), r) + np.repeat(np.arange(r) * bytes_per_row, c) + start

            # Limit the indexes actually used to the size of the array, because
            # if the region has an incomplete last line, the style setting
            # would fail because it isn't be a perfect rectangle
            clamped = indexes[np.where(np.less(indexes, len(self)))[0]]
            s[clamped] |= style_bits

    def rects_to_ranges(self, rects, bytes_per_row):
        ranges = []
        for (r1, c1), (r2, c2) in rects:
            start = r1 * bytes_per_row + c1
            end = (r2 - 1) * bytes_per_row + c2
            ranges.append((start, end))
        return ranges

    def clear_style_bits(self, **kwargs):
        style_mask = self.get_style_mask(**kwargs)
        self.style &= style_mask

    def set_user_data(self, ranges, user_index, user_data):
        for start, end in ranges:
            # FIXME: this is slow
            for i in range(start, end):
                rawindex = self.get_raw_index(i)
                self.rawdata.extra.user_data[user_index][rawindex] = user_data

    def get_user_data(self, index, user_index):
        rawindex = self.get_raw_index(index)
        try:
            return self.rawdata.extra.user_data[user_index][rawindex]
        except KeyError:
            return 0

    def get_sorted_user_data(self, user_index):
        d = self.rawdata.extra.user_data[user_index]
        indexes = sorted(d.keys())
        ranges = []
        start, end, current = None, None, None
        for i in indexes:
            if start is None:
                start = i
                current = d[i]
            else:
                if d[i] != current or i != end:
                    ranges.append([[start, end], current])
                    start = i
                    current = d[i]
            end = i + 1
        if start is not None:
            ranges.append([[start, end], current])
        return ranges

    def get_style_at_indexes(self, indexes):
        return self.style[indexes]

    def set_style_at_indexes(self, indexes, **kwargs):
        style_bits = self.get_style_bits(**kwargs)
        self.style[indexes] |= style_bits

    def remove_comments_at_indexes(self, indexes):
        for where_index in indexes:
            self.remove_comment(where_index)

    def set_comments_at_indexes(self, ranges, indexes, comments):
        for where_index, comment in zip(indexes, comments):
            rawindex = self.get_raw_index(where_index)
            if comment:
                log.debug("  restoring comment: rawindex=%d, '%s'" % (rawindex, comment))
                self.rawdata.extra.comments[rawindex] = comment
            else:
                try:
                    del self.rawdata.extra.comments[rawindex]
                    log.debug("  no comment in original data, removed comment in current data at rawindex=%d" % rawindex)
                except KeyError:
                    log.debug("  no comment in original data or current data at rawindex=%d" % rawindex)
                    pass

    def get_comments_at_indexes(self, indexes):
        """Get a list of comments at specified indexes"""
        s = self.style[indexes]
        has_comments = np.where(s & comment_bit_mask > 0)[0]
        comments = []
        for where_index in has_comments:
            raw = self.get_raw_index(indexes[where_index])
            try:
                comment = self.rawdata.extra.comments[raw]
            except KeyError:
                comment = None
            comments.append(comment)
        return has_comments, comments

    def get_comment_restore_data(self, ranges):
        """Get a chunk of data (designed to be opaque) containing comments,
        styles & locations that can be used to recreate the comments on an undo
        """
        restore_data = []
        for start, end in ranges:
            log.debug("range: %d-%d" % (start, end))
            styles = self.style[start:end].copy()
            items = {}
            for i in range(start, end):
                rawindex = self.get_raw_index(i)
                try:
                    comment = self.rawdata.extra.comments[rawindex]
                    log.debug("  index: %d rawindex=%d '%s'" % (i, rawindex, comment))
                    items[i] = (rawindex, comment)
                except KeyError:
                    log.debug("  index: %d rawindex=%d NO COMMENT TO SAVE" % (i, rawindex))
                    items[i] = (rawindex, None)

            restore_data.append((start, end, styles, items))
        return restore_data

    def restore_comments(self, restore_data):
        """Restore comment styles and data
        """
        for start, end, styles, items in restore_data:
            log.debug("range: %d-%d" % (start, end))
            self.style[start:end] = styles
            for i in range(start, end):
                rawindex, comment = items[i]
                if comment:
                    log.debug("  restoring comment: rawindex=%d, '%s'" % (rawindex, comment))
                    self.rawdata.extra.comments[rawindex] = comment
                else:
                    # no comment in original data, remove any if exists
                    try:
                        del self.rawdata.extra.comments[rawindex]
                        log.debug("  no comment in original data, removed comment in current data at rawindex=%d" % rawindex)
                    except KeyError:
                        log.debug("  no comment in original data or current data at rawindex=%d" % rawindex)
                        pass

    def get_comments_in_range(self, start, end):
        """Get a list of comments at specified indexes"""
        comments = {}

        # Naive way, but maybe it's fast enough: loop over all comments
        # gathering those within the bounds
        for rawindex, comment in self.rawdata.extra.comments.items():
            try:
                index = self.get_index_from_base_index(rawindex)
            except IndexError:
                continue
            if index >= start and index < end:
                comments[index] = comment
        return comments

    def set_comment_at(self, index, text):
        rawindex = self.get_raw_index(index)
        self.rawdata.extra.comments[rawindex] = text

    def set_comment(self, ranges, text):
        self.set_style_ranges(ranges, comment=True)
        for start, end in ranges:
            self.set_comment_at(start, text)

    def get_comment(self, index):
        rawindex = self.get_raw_index(index)
        return self.rawdata.extra.comments.get(rawindex, "")

    def remove_comment(self, index):
        rawindex = self.get_raw_index(index)
        try:
            del self.rawdata.extra.comments[rawindex]
        except KeyError:
            pass

    def get_first_comment(self, ranges):
        start = reduce(min, [r[0] for r in ranges])
        rawindex = self.get_raw_index(start)
        return self.rawdata.extra.comments.get(rawindex, "")

    def clear_comment(self, ranges):
        self.clear_style_ranges(ranges, comment=True)
        for start, end in ranges:
            for i in range(start, end):
                rawindex = self.get_raw_index(i)
                if rawindex in self.rawdata.extra.comments:
                    del self.rawdata.extra.comments[rawindex]

    def get_sorted_comments(self):
        return sorted([[k, v] for k, v in self.rawdata.extra.comments.items()])

    def iter_comments_in_segment(self):
        start = self.origin
        start_index = self.get_raw_index(0)
        end_index = self.get_raw_index(len(self.rawdata))
        for k, v in self.rawdata.extra.comments.items():
            if k >= start_index and k < end_index:
                yield self.rawdata.get_reverse_index(k), v

    def copy_user_data(self, source, index_offset=0):
        """Copy comments and other user data from the source segment to this
        segment.

        The index offset is the offset into self based on the index of source.
        """
        for index, comment in source.iter_comments_in_segment():
            self.set_comment_at(index + index_offset, comment)

    def label(self, index, lower_case=True):
        if lower_case:
            return "%04x" % (index + self.origin)
        else:
            return "%04X" % (index + self.origin)

    @property
    def search_copy(self):
        if self._search_copy is None:
            self._search_copy = self.data.tobytes()
        return self._search_copy

    def compare_segment(self, other_segment):
        self.clear_style_bits(diff=True)
        diff = self.rawdata.data != other_segment.rawdata.data
        d = diff * np.uint8(diff_bit_mask)
        self.style |= (diff * np.uint8(diff_bit_mask))
        log.debug("compare_segment: # entries %d, # diffs: %d" % (len(diff), len(np.where(diff == True)[0])))


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
    extra_serializable_attributes = ['metadata_start', 'data_start']

    def __init__(self, rawdata, metadata_start, data_start, origin, end_addr=0,  name="", **kwargs):
        DefaultSegment.__init__(self, rawdata, origin, name, **kwargs)
        self.metadata_start = int(metadata_start)
        self.data_start = int(data_start)

    def __str__(self):
        count = len(self)
        s = "%s $%04x-$%04x ($%04x @ $%04x)" % (self.name, self.origin, self.origin + count, count, self.data_start)
        if self.error:
            s += " " + self.error
        return s

    @property
    def verbose_info(self):
        count = len(self)
        name = self.verbose_name or self.name
        s = "%s  address range: $%04x-$%04x ($%04x bytes), file index of first byte: $%04x" % (name, self.origin, self.origin + count, count, self.data_start)
        if self.error:
            s += "  error='%s'" % self.error
        return s


class SegmentedFileSegment(ObjSegment):
    can_resize_default = True


class RawSectorsSegment(DefaultSegment):
    extra_serializable_attributes = ['boot_sector_size', 'num_boot_sectors', 'page_size', 'first_sector', 'num_sectors']

    def __init__(self, rawdata, first_sector, num_sectors, count, boot_sector_size, num_boot_sectors, sector_size, **kwargs):
        DefaultSegment.__init__(self, rawdata, 0, **kwargs)
        self.boot_sector_size = int(boot_sector_size)
        self.num_boot_sectors = int(num_boot_sectors)
        self.page_size = int(sector_size)
        self.first_sector = int(first_sector)
        self.num_sectors = int(num_sectors)

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


class RawTrackSectorSegment(RawSectorsSegment):
    def label(self, index, lower_case=True):
        boot_size = self.num_boot_sectors * self.boot_sector_size
        if index >= boot_size:
            sector, byte = divmod(index - boot_size, self.page_size)
            sector += self.num_boot_sectors
        else:
            sector, byte = divmod(index, self.boot_sector_size)
        sector += self.first_sector
        t, s = divmod(sector, 16)
        if lower_case:
            return "t%02ds%02d:%02x" % (t, s, byte)
        return "t%02ds%02d:%02X" % (t, s, byte)


def interleave_indexes(segments, num_bytes):
    num_segments = len(segments)

    # interleave size will be the smallest segment
    size = len(segments[0])
    for s in segments[1:]:
        if len(s) < size:
            size = len(s)

    # adjust if byte spacing is not an even divisor
    _, rem = divmod(size, num_bytes)
    size -= rem

    interleave = np.empty(size * num_segments, dtype=np.uint32)
    if size > 0:
        factor = num_bytes * num_segments
        start = 0
        for s in segments:
            order = s.rawdata.get_indexes_from_base()
            for i in range(num_bytes):
                interleave[start::factor] = order[i:size:num_bytes]
                start += 1
    return interleave


def interleave_segments(segments, num_bytes):
    new_index = interleave_indexes(segments, num_bytes)
    data_base, style_base = segments[0].rawdata.get_bases()
    for s in segments[1:]:
        d, s = s.rawdata.get_bases()
        if id(d) != id(data_base) or id(s) != id(style_base):
            raise ValueError("Can't interleave segments with different base arrays")
    raw = SegmentData(data_base, style_base, segments[0].rawdata.extra, order=new_index)
    segment = DefaultSegment(raw, 0)
    return segment


class SegmentList(list):
    def add_segment(self, data, origin=0, name=None):
        last = origin + len(data)
        if name is None:
            name = "%04x - %04x, size=%04x" % (origin, last, len(data))
        rawdata = SegmentData(data)
        s = DefaultSegment(rawdata, origin, name)
        self.append(s)
        return s
