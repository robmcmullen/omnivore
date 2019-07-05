import bisect
import io
import json

import numpy as np

from . import errors
from . import utils
from . import style_bits
from functools import reduce

import logging
log = logging.getLogger(__name__)


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

    def tobytes(self):
        return self.np_data[self.order].tobytes()


class Segment:
    ui_name = "Data Segment"
    base_serializable_attributes = ['origin', 'error', 'name', 'verbose_name', 'uuid']
    extra_serializable_attributes = []

    def __init__(self, container_or_segment, offset_or_offset_list=None, origin=0, name="All", error=None, verbose_name=None, length=None):
        self.init_empty()
        # the container may be specified as the actual container or a segment
        # of the container. If a segment is specified, the offset list is
        # calculated relative to the segment to get the real offset into the
        # container.
        offset_list = self.calc_offset_list(container_or_segment, offset_or_offset_list, length)
        if hasattr(container_or_segment, 'container_offset'):
            log.debug(f"creating {name},  {len(offset_list)} bytes from {container_or_segment}")
            # log.debug(f"  offset_list = {offset_list}")
            offset_list = container_or_segment.container_offset[offset_list]
            container_or_segment = container_or_segment.container

        self.container = container_or_segment
        self.container_offset = self.enforce_offset_bounds(offset_list)

        self.origin = int(origin)  # force python int to decouple from possibly being a numpy datatype
        self.error = error
        self.name = name
        self.verbose_name = verbose_name

        # Child segments
        self.segments = self.calc_segments()

    def init_empty(self):
        self.origin = 0
        self.error = ""
        self.name = ""
        self.verbose_name = ""
        self.uuid = utils.uuid()
        self._reverse_offset = None
        self.segments = []

    #### properties

    @property
    def data(self):
        return ArrayWrapper(self.container._data, self.container_offset)

    @property
    def style(self):
        return ArrayWrapper(self.container._style, self.container_offset)

    @property
    def disasm_type(self):
        return ArrayWrapper(self.container._disasm_type, self.container_offset)

    @property
    def reverse_offset(self):
        if self._reverse_offset is None:
            self._reverse_offset = self.calc_reverse_offsets()
        return self._reverse_offset

    def __len__(self):
        return np.alen(self.container_offset)

    #### dunder methods and convenience functions to operate on data (not style)

    def __str__(self):
        if self.origin > 0:
            origin = " @ %04x" % (self.origin)
        else:
            origin = ""
        s = "%s (%d bytes%s)" % (self.name, len(self), origin)
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

    #### iterator utilities

    def iter_segments(self, segment_type=None):
        for segment in self.segments:
            if segment_type is None or isinstance(segment, segment_type):
                yield segment
            yield from segment.iter_segments(segment_type)

    def iter_menu(self, level):
        for segment in self.segments:
            yield (segment, level)
            yield from segment.iter_menu(level + 1)

    #### offsets

    def calc_offset_list(self, container_or_segment, offset_or_offset_list=None, length=None):
        if offset_or_offset_list is None:
            offset_or_offset_list = 0
        try:
            start_offset = int(offset_or_offset_list)
        except TypeError:
            offset_list = utils.to_numpy_list(offset_or_offset_list)
        else:
            if length is None:
                length = len(container_or_segment)
            offset_list = np.arange(offset_or_offset_list, offset_or_offset_list + length, dtype=np.uint32)
        return offset_list

    def enforce_offset_bounds(self, offset_list):
        return offset_list[offset_list < len(self.container)]

    def calc_reverse_offsets(self):
        # Initialize array to out of range
        r = np.zeros(len(self.container), dtype=np.int32) - 1
        r[self.container_offset] = np.arange(len(self), dtype=np.int32)
        valid = np.where(r >= 0)[0]
        if len(valid) != len(self):
            raise errors.InvalidSegmentOrder
        return r

    def calc_offsets_of_range(self, start, end):
        in_here = np.arange(start, end, dtype=np.int32)
        in_container = self.container_offset[in_here]
        return in_container

    def calc_index_from_other_segment(self, other_segment_index, other_segment):
        """Convert an index from another segment by mapping it to the container
        and then looking up the index that corresponds to that container index
        in this segment.
        """
        container_index = other_segment.container_offset[other_segment_index]
        index = self.reverse_offset[container_index]
        return index

    def calc_indexes_from_other_segment(self, other_segment_indexes, other_segment):
        """Convert a list of indexes from another segment by mapping it to the
        container and then looking up each index that corresponds to that
        container index in this segment.
        """
        container_indexes = other_segment.container_offset[other_segment_indexes]
        indexes = self.reverse_offset[container_indexes]
        return indexes

    #### creation

    def calc_segments(self):
        """Convenience method used by subclasses to create any sub-segments
        within this segment.

        """
        return []

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
        state['__size__'] = len(self)

        def get_value(key):
            if ":" in key:
                key, converter = key.split(":", 1)
                value = getattr(self, key)
                if converter == "int":
                    value = int(value)
                elif converter == "str":
                    value = str(value)
            else:
                value = getattr(self, key)
            return key, value

        for key in self.base_serializable_attributes:
            key, value = get_value(key)
            state[key] = value
        for key in self.extra_serializable_attributes:
            key, value = get_value(key)
            state[key] = value
        state['container_offset'] = utils.collapse_to_ranges(self.container_offset, compact=True)
        state['segments'] = self.segments
        return state

    def __setstate__(self, state):
        """Custom jsonpickle state restore routine

        The use of jsonpickle to recreate objects doesn't go through __init__,
        so there will be missing attributes when restoring old versions of the
        json. Once a version gets out in the wild and additional attributes are
        added to a segment, a default value should be applied here.
        """
        self.init_empty()
        size = state.pop('__size__')
        raw = np.arange(size, dtype=np.uint32)
        self.container_offset = raw
        utils.restore_from_ranges(self.container_offset, state.pop('container_offset', []))
        self.segments = state.pop('segments')

        # Can't restore here because it would result in many unrelated copies
        # of the container object. After all the segments are loaded, will have
        # to loop through and set container attributes for each one.
        self.container = None

        for key in self.base_serializable_attributes:
            if key in state:
                setattr(self, key, state.pop(key))
        for key in self.extra_serializable_attributes:
            if key in state:
                setattr(self, key, state.pop(key))
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

    def restore_computed_defaults(self):
        """Hook to recreate any computed defaults after the container has
        been restored
        """
        pass


    @property
    def verbose_info(self):
        lines = []
        name = self.verbose_name or self.name
        lines.append(f"{name}: {len(self)} bytes")
        for s in self.segments:
            v = s.segment_info("    ")
            lines.extend(v)
        return "\n".join(lines)

    def segment_info(self, indent=""):
        lines = []
        lines.append(indent + str(self))
        for s in self.segments:
            lines.extend(s.segment_info(indent + "    "))
        return lines

    def is_valid_index(self, i):
        return i >= 0 and i < len(self)

    def tobytes(self):
        return self.container._data[self.container_offset].tobytes()

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
        bits = style_bits.get_style_bits(**kwargs)
        matches = (self.style & bits) == bits
        return utils.bool_to_ranges(matches)

    def get_style_indexes(self, **kwargs):
        """Return a list of start, end pairs that match the specified style
        """
        bits = style_bits.get_style_bits(**kwargs)
        matches = (self.style & bits) == bits
        w = np.where(matches == True)[0]
        return w

    def convert_style(self, from_style, to_style):
        indexes = self.get_style_indexes(**from_style)
        indexes = self.container_offset[indexes]
        c = self.container
        c.clear_style_at_indexes(indexes, **from_style)

        # it's possible the mask includes more bits than the style, as in the
        # user styles
        c.clear_style_at_indexes(indexes, **to_style)
        c.set_style_at_indexes(indexes, **to_style)

    #### disassembly type

    def update_data_style_from_disasm_type(self):
        self.container.update_data_style_from_disasm_type()

    def set_disasm_ranges(self, ranges, value):
        indexes = self.calc_source_indexes_from_ranges(ranges)
        self.container.disasm_type[indexes] = value

    #### comment convenience functions

    def get_comment_locations(self, **kwargs):
        bits = style_bits.get_style_bits(**kwargs)
        r = self.rawdata.copy()
        #print len(r.style)
        #print len(r.style_base)
        r.style_base[:] &= bits
        comment_indexes = np.asarray(list(self.container.comments.keys()), dtype=np.uint32)
        #print comment_indexes
        r.style_base[comment_indexes] |= style_bits.comment_bit_mask
        return r.unindexed_style[:]

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

    def remove_comments_at_indexes(self, indexes):
        for where_index in indexes:
            self.remove_comment(where_index)

    def set_comments_at_indexes(self, ranges, indexes, comments):
        c = self.container
        for where_index, comment in zip(indexes, comments):
            rawindex = self.container_offset[where_index]
            if comment:
                log.debug("  restoring comment: rawindex=%d, '%s'" % (rawindex, comment))
                c.comments[rawindex] = comment
            else:
                try:
                    del self.container.comments[rawindex]
                    log.debug("  no comment in original data, removed comment in current data at rawindex=%d" % rawindex)
                except KeyError:
                    log.debug("  no comment in original data or current data at rawindex=%d" % rawindex)
                    pass
        c.fixup_comments()

    def get_comments_at_indexes(self, indexes):
        """Get a list of comments at specified indexes"""
        s = self.style[indexes]
        has_comments = np.where(s & style_bits.comment_bit_mask > 0)[0]
        comments = []
        for where_index in has_comments:
            raw = self.container_offset[indexes[where_index]]
            try:
                comment = self.container.comments[raw]
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
                rawindex = self.container_offset[i]
                try:
                    comment = self.container.comments[rawindex]
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
                    self.container.comments[rawindex] = comment
                else:
                    # no comment in original data, remove any if exists
                    try:
                        del self.container.comments[rawindex]
                        log.debug("  no comment in original data, removed comment in current data at rawindex=%d" % rawindex)
                    except KeyError:
                        log.debug("  no comment in original data or current data at rawindex=%d" % rawindex)
                        pass

    def get_comments_in_range(self, start, end):
        """Get a list of comments at specified indexes"""
        comments = {}

        # Naive way, but maybe it's fast enough: loop over all comments
        # gathering those within the bounds
        for rawindex, comment in self.container.comments.items():
            try:
                index = self.get_index_from_base_index(rawindex)
            except IndexError:
                continue
            if index >= start and index < end:
                comments[index] = comment
        return comments

    def set_comment_at(self, index, text):
        rawindex = self.container_offset[index]
        c = self.container
        c.comments[rawindex] = text
        c.style[rawindex] |= style_bits.comment_bit_mask

    def set_comment_ranges(self, ranges, text):
        for start, end in ranges:
            self.set_comment_at(start, text)

    def get_comment_at(self, index):
        rawindex = self.container_offset[index]
        return self.container.comments.get(rawindex, "")

    def remove_comment_at(self, index):
        rawindex = self.container_offset[index]
        self.container.clear_comments([rawindex])

    def get_first_comment(self, ranges):
        start = reduce(min, [r[0] for r in ranges])
        rawindex = self.container_offset[start]
        return self.container.comments.get(rawindex, "")

    def clear_comment_ranges(self, ranges):
        c = self.container
        for start, end in ranges:
            offsets = self.calc_offsets_of_range(start, end)
            c.clear_comments(offsets)

    def iter_comments_in_segment(self):
        s = self.style[:]
        has_comments = np.where(s & style_bits.comment_bit_mask > 0)[0]
        for index in has_comments:
            rawindex = self.container_offset[index]
            yield index, self.container.comments.get(rawindex, "")

    def address(self, index, lower_case=True):
        if lower_case:
            return "%04x" % (index + self.origin)
        else:
            return "%04X" % (index + self.origin)

    def compare_segment(self, other_segment):
        self.clear_style_bits(diff=True)
        diff = self.rawdata.data != other_segment.rawdata.data
        d = diff * np.uint8(style_bits.diff_bit_mask)
        self.style |= (diff * np.uint8(style_bits.diff_bit_mask))
        log.debug("compare_segment: # entries %d, # diffs: %d" % (len(diff), len(np.where(diff == True)[0])))

    def calc_selected_index_metadata(self, indexes):
        """Return serializable string containing style information"""
        style = self.style[indexes]
        where_comments, comments = self.get_comments_at_indexes(indexes)
        log.debug(f"after get_comments_at_indexes: {where_comments}, {comments}")
        return style, where_comments, comments

    @classmethod
    def encode_selected_index_metadata(cls, style, where_comments, comments):
        metadata = [style.tolist(), where_comments.tolist(), comments]
        j = json.dumps(metadata).encode('utf-8')
        return j

    def serialize_selected_index_metadata(self, indexes):
        a = self.calc_selected_index_metadata(indexes)
        return self.encode_selected_index_metadata(*a)

    @classmethod
    def restore_selected_index_metadata(self, encoded_meta):
        metadata = json.loads(encoded_meta.decode('utf-8'))
        style = np.asarray(metadata[0], dtype=np.uint8)
        where_comments = np.asarray(metadata[1], dtype=np.int32)
        return style, where_comments, metadata[2]


class RawSectorsSegment(Segment):
    extra_serializable_attributes = ['sector_size', 'first_sector', 'num_sectors']

    def __init__(self, container, header_size, first_sector, num_sectors, sector_size, name="Sectors", **kwargs):
        DefaultSegment.__init__(self, container, header_size, name=name, length=num_sectors*sector_size, **kwargs)
        self.sector_size = int(sector_size)
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
        sector, byte = divmod(index, self.sector_size)
        if lower_case:
            return "s%03d:%02x" % (sector + self.first_sector, byte)
        return "s%03d:%02X" % (sector + self.first_sector, byte)
