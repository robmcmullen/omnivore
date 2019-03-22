import hashlib
import inspect
import pkg_resources

import numpy as np

from . import errors
from . import style_bits
from .utils import to_numpy, to_numpy_list, uuid

import logging
log = logging.getLogger(__name__)


class MediaType:
    """Media storage container

    Instances of this class hold a contiguous block data that represent the
    disk, cassette or cartridge image. Views of this data are in the form of
    `Segment`s which only refer to this data via a mapping of indexes into this
    container. Segments do not hold copies of the data. All operations on
    segments actually affect the container's data, and because all segments
    point to the container's data, a change to one segment can affect many
    other segments.
    """
    pretty_name = "Raw Data"
    can_resize_default = False

    base_serializable_attributes = ['origin', 'error', 'name', 'verbose_name', 'uuid', 'can_resize']
    extra_serializable_attributes = []

    def __init__(self, data, style=None, origin=0, name="All", error=None, verbose_name=None, memory_map=None):
        self._data = None
        self._style = None
        self.set_data(data, style)
        self.verify_header()
        self.verify_data()

        self.origin = int(origin)  # force python int to decouple from possibly being a numpy datatype
        self.error = error
        self.name = name
        self.verbose_name = verbose_name
        self.uuid = uuid()
        if memory_map is None:
            memory_map = {}
        self.memory_map = memory_map
        self.comments = dict()
        self.user_data = dict()
        for i in range(1, style_bits.user_bit_mask):
            self.user_data[i] = dict()

        # Some segments may be resized to contain additional segments not
        # present when the segment was created.
        self.can_resize = self.__class__.can_resize_default

    #### initialization

    def set_data(self, data, style):
        self.data = data
        self.style = style

    def verify_header(self):
        """Subclasses should override this method to verify the integrity of
        any header information, if any.
        """
        self.header_length = 0

    def verify_data(self):
        """Subclasses should override this method to verify that the passed-in
        data can be stored in this media.
        """
        pass

    #### properties

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, value):
        if self._data is not None:
            raise errors.ReadOnlyContainer("media_type already populated with data")
        self._data = to_numpy(value)

    @property
    def style(self):
        return self._style

    @style.setter
    def style(self, value):
        if value is None:
            value = np.zeros(len(self._data), dtype=np.uint8)
        self._style = to_numpy(value)

    @property
    def sha1(self):
        return hashlib.sha1(self.data).digest()

    #### dunder methods

    def __str__(self):
        return f"{self.pretty_name}, size={len(self)}"

    def __len__(self):
        return np.alen(self._data)

    def __and__(self, other):
        return self._data & other

    def __iand__(self, other):
        self._data &= other
        return self

    def __getitem__(self, index):
        return self._data[index]

    def __setitem__(self, index, value):
        self._data[index] = value

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
        state['memory_map'] = sorted([list(i) for i in self.memory_map.items()])
        state['comment ranges'] = [list(a) for a in self.get_style_ranges(comment=True)]
        state['data ranges'] = [list(a) for a in self.get_style_ranges(data=True)]
        for i in range(1, style_bits.user_bit_mask):
            r = [list(a) for a in self.get_style_ranges(user=i)]
            if r:
                slot = "user style %d" % i
                state[slot] = r

        # json serialization doesn't allow int keys, so convert to list of
        # pairs
        state['comments'] = self.get_sorted_comments()
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
        comments = state.pop('comments', {})
        for k, v in e['comments']:
            self.comments[k] = v
        ranges = state.pop('comment ranges')
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
        for i in range(1, style_bits.user_bit_mask):
            slot = "user style %d" % i
            if slot in e:
                self.set_style_ranges(e[slot], user=i)
        self.restore_missing_serializable_defaults()
        self.__dict__.update(state)
        self.restore_renamed_serializable_attributes()

    #### style

    def set_style_at_indexes(self, indexes, **kwargs):
        style_bits = get_style_bits(**kwargs)
        self._style[indexes] |= style_bits

    def clear_style_at_indexes(self, indexes, **kwargs):
        style_mask = get_style_mask(**kwargs)
        self.style[indexes] &= style_mask

    def get_style_at_indexes(self, **kwargs):
        """Return a list of start, end pairs that match the specified style
        """
        style_bits = self.get_style_bits(**kwargs)
        matches = (self._style & style_bits) == style_bits
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
        has_comments = np.where(style_base & style_bits.comment_bit_mask > 0)[0]
        both = np.intersect1d(comment_text_indexes, has_comments)
        log.info("fixup comments: %d correctly marked, %d without style, %d empty text" % (np.alen(both), np.alen(comment_text_indexes) - np.alen(both), np.alen(has_comments) - np.alen(both)))
        style_base &= comment_mask
        comment_style = self.get_style_bits(comment=True)
        style_base[comment_text_indexes] |= comment_style


class DiskImage(MediaType):
    pretty_name = "Disk Image"
    sector_size = 128
    expected_size = 0
    starting_sector_label = 1

    def __str__(self):
        return f"{self.pretty_name}, size={len(self)} ({self.num_sectors}x{self.sector_size}B)"

    def verify_data(self):
        size = len(self) - self.header_length
        self.check_media_size(size)
        self.check_sector_size(size)

    def check_media_size(self, size):
        if size != self.expected_size:
            raise errors.InvalidMediaSize(f"{self.pretty_name} expects size {self.expected_size}; found {size}")

    def check_sector_size(self, size):
        if size % self.sector_size != 0:
            raise errors.InvalidMediaSize("{self.pretty_name} requires integer number of sectors")
        self.num_sectors = size // self.sector_size

    def sector_is_valid(self, sector):
        return (self.num_sectors < 0) or (sector >= self.starting_sector_label and sector < (self.num_sectors + self.starting_sector_label))

    def get_index_of_sector(self, sector):
        if not self.sector_is_valid(sector):
            raise errors.ByteNotInFile166("Sector %d out of range" % sector)
        pos = (sector - self.starting_sector_label) * self.sector_size
        return pos + self.header_length, self.sector_size


class CartImage(MediaType):
    pretty_name = "Cart Image"
    expected_size = 0

    def __str__(self):
        return f"{len(self) // 1024}K {self.pretty_name}"

    def verify_data(self):
        size = len(self) - self.header_length
        self.check_media_size(size)

    def check_media_size(self, size):
        k, rem = divmod(size, 1024)
        if rem > 0:
            raise errors.InvalidMediaSize("Cart not multiple of 1K")
        if size != self.expected_size:
            raise errors.InvalidMediaSize(f"{self.pretty_name} expects size {self.expected_size}; found {size}")


ignore_base_class_media_types = set([DiskImage, CartImage])

def find_media_types():
    media_types = []
    for entry_point in pkg_resources.iter_entry_points('atrcopy.media_types'):
        mod = entry_point.load()
        log.debug(f"find_media_type: Found module {entry_point.name}={mod.__name__}")
        for name, obj in inspect.getmembers(mod):
            if inspect.isclass(obj) and MediaType in obj.__mro__[1:] and obj not in ignore_base_class_media_types:
                log.debug(f"find_media_types:   found media_type class {name}")
                media_types.append(obj)
    return media_types


def guess_media_type(data, verbose=False):
    for m in find_media_types():
        if verbose:
            log.info(f"trying media_type {m}")
        try:
            found = m(data)
        except errors.MediaError as e:
            log.debug(f"found error: {e}")
            continue
        else:
            if verbose:
                log.info(f"found media_type {m}")
            return found
    log.info(f"No recognized media type.")
    return MediaType(data)
