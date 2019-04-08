import os
import hashlib
import inspect
import pkg_resources

import numpy as np

from . import errors
from . import style_bits
from .utils import to_numpy, to_numpy_list, uuid
from . import media_type
from . import filesystem

import logging
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

class Container:
    """Media storage container and packer/unpacker for disk image compression.

    Instances of this class hold a contiguous block data that represent the
    disk, cassette or cartridge image. Views of this data are in the form of
    `Segment`s which only refer to this data via a mapping of indexes into this
    container. Segments do not hold copies of the data. All operations on
    segments actually affect the container's data, and because all segments
    point to the container's data, a change to one segment can affect many
    other segments.

    In their native data format, disk images may be stored as raw data or can
    be compressed by any number of techniques. Subclasses of Container
    implement the `unpack_bytes` method which examines the byte_data argument
    for the supported compression type, and if valid returns the unpacked bytes
    to be used in the disk image parsing.

    """
    pretty_name = "Uncompressed"
    compression_algorithm = "uncompressed"
    can_resize_default = False

    base_serializable_attributes = ['origin', 'error', 'name', 'verbose_name', 'uuid', 'can_resize']
    extra_serializable_attributes = []

    def __init__(self, data, style=None, origin=0, name="All", error=None, verbose_name=None, memory_map=None):

        self.segments = []
        self.header = None
        self.filesystem = None
        self._media = None
        self.mime = "application/octet-stream"

        self._data = None
        self._style = None
        self.data = data
        self.style = style

        self.pathname = ""
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

    #### properties

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, value):
        if self._data is not None:
            raise errors.ReadOnlyContainer("container already populated with data")
        raw = value.tobytes()
        try:
            unpacked = self.calc_unpacked_bytes(raw)
        except EOFError as e:
            raise errors.InvalidContainer(e)
        self._data = to_numpy(unpacked)

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

    @property
    def header_length(self):
        return len(self.header) if self.header is not None else 0

    @property
    def media(self):
        return self._media

    @media.setter
    def media(self, value):
        self._media = value
        self.segments = []
        if value.header:
            self.header = value.header
            self.segments.append(self.header)
        self.segments.append(value)

    @property
    def verbose_info(self):
        return self.container_info()

    def container_info(self, indent=""):
        lines = []
        name = self.verbose_name or self.name
        lines.append(f"{indent}{name}: {len(self)} bytes")
        for s in self.segments:
            v = s.segment_info(indent + "    ")
            lines.extend(v)
        return "\n".join(lines)

    @property
    def basename(self):
        return os.path.basename(self.pathname)

    #### dunder methods

    def __str__(self):
        if self.media:
            desc = str(self.media)
        else:
            desc = f"{self.pretty_name}, size={len(self)}"
        return desc

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

    #### compression

    def calc_unpacked_bytes(self, byte_data):
        """Attempt to unpack `byte_data` using this unpacking algorithm.

        `byte_data` is a byte string, and should return a byte string if
        successfully unpacked. Conversion to a numpy array will take place
        automatically, outside of this method.

        If the data is not recognized by this subclass, raise an
        InvalidContainer exception. This signals to the caller that a different
        container type should be tried.

        If the data is recognized by this subclass but the unpacking algorithm
        is not implemented, raise an UnsupportedContainer exception. This is
        different than the InvalidContainer exception because it indicates that
        the data was indeed recognized by this subclass (despite not being
        unpacked) and checking further containers is not necessary.
        """
        return byte_data

    def calc_packed_bytes(self):
        """Pack this container into a compressed data array using this packing
        algorithm.
        """
        return np_data

    #### media

    def guess_media_type(self):
        media = media_type.guess_media_type(self)
        self.media = media

    def guess_filesystem(self):
        self.media.guess_filesystem()
        self.filesystem = self.media.filesystem

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


_containers = None

def _find_containers():
    containers = []
    for entry_point in pkg_resources.iter_entry_points('atrip.containers'):
        mod = entry_point.load()
        log.debug(f"find_container: Found module {entry_point.name}={mod.__name__}")
        for name, obj in inspect.getmembers(mod):
            if inspect.isclass(obj) and Container in obj.__mro__[1:]:
                log.debug(f"find_containers:   found container class {name}")
                containers.append(obj)
    return containers

def find_containers():
    global _containers

    if _containers is None:
        _containers = _find_containers()
    return _containers

def guess_container(raw_data, verbose=False):
    container = None
    for c in find_containers():
        if verbose:
            log.info(f"trying container {c.compression_algorithm}")
        try:
            container = c(raw_data)
        except errors.InvalidContainer as e:
            continue
        else:
            if verbose:
                log.info(f"found container {c.compression_algorithm}")
            break
    else:
        if verbose:
            log.info(f"image does not appear to be compressed.")
        container = Container(raw_data)
    return container


def load(pathname):
    sample_data = np.fromfile(pathname, dtype=np.uint8)
    container = guess_container(sample_data)
    container.pathname = pathname
    container.guess_media_type()
    return container
