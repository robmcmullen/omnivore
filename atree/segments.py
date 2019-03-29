import bisect
import io

import numpy as np

from . import errors
from .utils import to_numpy, to_numpy_list, uuid
from . import style_bits
from functools import reduce

import logging
log = logging.getLogger(__name__)


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
        log.debug("binary data: %x bytes at %x" % (header[1], header[0]))
        return header.tobytes() + segment.tobytes()


class ArrayWrapper:
    """Wrapper for numpy data so that manipulations can use normal numpy syntax
    and still affect the data according to the byte ordering.

    Numpy's fancy indexing can't be used for setting set values, so this
    intermediate layer is needed that defines the __setitem__ method that
    explicitly references the byte ordering in the data array.
    """

    def __init__(self, data, order):
        self.np_data = data
        self.order = order

    def __str__(self):
        return f"ArrayWrapper at {hex(id(self))} count={len(self)} order={self.order}"

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


class SegmentData:
    # Dummy to prevent import statement failures
    pass


class DefaultSegment:
    can_resize_default = False

    base_serializable_attributes = ['origin', 'error', 'name', 'verbose_name', 'uuid', 'can_resize']
    extra_serializable_attributes = []

    def __init__(self, container, offset_or_offset_list, origin=0, name="All", error=None, verbose_name=None, length=None):
        self.container = container
        try:
            start_offset = int(offset_or_offset_list)
        except TypeError:
            self.set_offset_from_list(offset_or_offset_list)
        else:
            self.set_offset_from_ints(offset_or_offset_list, length)
        self.verify_offsets()

        self.origin = int(origin)  # force python int to decouple from possibly being a numpy datatype
        self.error = error
        self.name = name
        self.verbose_name = verbose_name
        self.uuid = uuid()

        # Some segments may be resized to contain additional segments not
        # present when the segment was created.
        self.can_resize = self.__class__.can_resize_default

    #### properties

    @property
    def data(self):
        return ArrayWrapper(self.container._data, self.container_offset)

    @property
    def style(self):
        return ArrayWrapper(self.container._style, self.container_offset)

    def __len__(self):
        return np.alen(self.container_offset)

    #### dunder methods and convenience functions to operate on data (not style)

    def __str__(self):
        if self.origin > 0:
            origin = " @ %04x" % (self.origin)
        else:
            origin = ""
        s = "%s ($%x bytes%s)" % (self.name, len(self), origin)
        if self.error:
            s += " " + self.error
        return s

    def __and__(self, other):
        return self.container._data[self.container_offset] & other

    def __iand__(self, other):
        self.container._data[self.container_offset] &= other
        return self

    def __getitem__(self, index):
        return self.container._data[self.container_offset[index]]

    def __setitem__(self, index, value):
        self.container._data[self.container_offset[index]] = value

    #### offsets

    def set_offset_from_list(self, offsets):
        self.container_offset = to_numpy_list(offsets)

    def set_offset_from_ints(self, start, length):
        if length is None:
            raise errors.InvalidSegmentLength
        self.container_offset = np.arange(start, start + length, dtype=np.uint32)

    def verify_offsets(self):
        self.enforce_offset_bounds()
        self.reverse_offset = self.calc_reverse_offsets()

    def enforce_offset_bounds(self):
        self.container_offset = self.container_offset[self.container_offset < len(self.container)]

    def calc_reverse_offsets(self):
        # Initialize array to out of range
        r = np.zeros(len(self.container), dtype=np.int32) - 1
        r[self.container_offset] = np.arange(len(self), dtype=np.int32)
        valid = np.where(r >= 0)[0]
        if len(valid) != len(self):
            raise errors.InvalidSegmentOrder
        return r

    #### subset

    def create_subset(self, new_order, *args, **kwargs):
        new_order_of_source = self.container_offset[new_order]
        segment = DefaultSegment(self.container, new_order_of_source, *args, **kwargs)
        return segment

    #### serialization

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
        state['container_offset'] = self.calc_serialized_container_offset()
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
            log.debug(f"moving start_addr to origin: {self.start_addr}")
            delattr(self, 'start_addr')


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

    def is_valid_index(self, i):
        return i >= 0 and i < len(self)

    def tobytes(self):
        return self.container._data[self.container_offset].tobytes()

    def get_style_bits(self, **kwargs):
        return style_bits.get_style_bits(**kwargs)

    def get_style_mask(self, **kwargs):
        return style_bits.get_style_mask(**kwargs)

    def calc_source_indexes_from_ranges(self, ranges):
        source_indexes = np.zeros(len(self.container), dtype=np.uint8)
        offsets = self.container_offset
        for start, end in ranges:
            if end < start:
                start, end = end, start
            source_indexes[offsets[start:end]] = 1
        affected_source_indexes = np.where(source_indexes > 0)[0]
        return affected_source_indexes

    def set_style_ranges(self, ranges, **kwargs):
        indexes = self.calc_source_indexes_from_ranges(ranges)
        self.container.set_style_at_indexes(indexes, **kwargs)

    def clear_style_ranges(self, ranges, **kwargs):
        indexes = self.calc_source_indexes_from_ranges(ranges)
        self.container.clear_style_at_indexes(indexes, **kwargs)

    def clear_style_bits(self, **kwargs):
        self.container.clear_style_at_indexes(self.container_offset, **kwargs)

    def get_style_ranges(self, **kwargs):
        """Return a list of start, end pairs that match the specified style
        """
        style_bits = self.get_style_bits(**kwargs)
        matches = (self.style & style_bits) == style_bits
        return self.bool_to_ranges(matches)

    def get_comment_locations(self, **kwargs):
        style_bits = self.get_style_bits(**kwargs)
        r = self.rawdata.copy()
        #print len(r.style)
        #print len(r.style_base)
        r.style_base[:] &= style_bits
        comment_indexes = np.asarray(list(self.rawdata.extra.comments.keys()), dtype=np.uint32)
        #print comment_indexes
        r.style_base[comment_indexes] |= style_bits.comment_bit_mask
        return r.unindexed_style[:]

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
        has_comments = np.where(s & style_bits.comment_bit_mask > 0)[0]
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
        d = diff * np.uint8(style_bits.diff_bit_mask)
        self.style |= (diff * np.uint8(style_bits.diff_bit_mask))
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
