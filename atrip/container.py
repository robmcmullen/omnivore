import os
import hashlib
import inspect
import pkg_resources

import numpy as np

from . import errors
from . import style_bits
from . import utils
from .segment import Segment
from . import media_type
from . import filesystem
from .compressor import guess_compressor_list, compress_in_reverse_order, Uncompressed
from .filesystem import Dirent

import logging
log = logging.getLogger(__name__)



class ContainerHeader(Segment):
    format = np.dtype([])
    file_format = "No"

    def __init__(self, container):
        self.sector_size = 0
        self.image_size = 0
        Segment.__init__(self, container, 0, name=f"{self.file_format} Header", length=self.header_length)
        self.decode()

    @property
    def header_length(self):
        return self.format.itemsize

    def decode(self):
        size = self.header_length
        header = self.container[0:size]
        if len(header) == size:
            self.decode_from_bytes(header)
        else:
            raise errors.InvalidHeader(f"incorrect header size {len(header)} for {self.container_format}; should be {size}")

    def decode_from_bytes(self, raw):
        """Parse raw bytes and populate object attributes
        """
        raise NotImplementedError(f"decode_from_bytes not implemented for {self.file_format}")

    def encode_to_bytes(self, raw):
        """Convert values stored in header object into raw bytes in the
        container
        """
        raise NotImplementedError(f"encode_to_bytes not implemented for {self.file_format}")

    def check_media(self, media):
        if self.sector_size > 0 and self.sector_size != media.sector_size:
            raise errors.InvalidHeader("ExpectedMismatch between sector sizes: header claims {self.sector_size}, expected {media.sector_size} for {media.ui_name}")
        media_size = len(media) - self.header_length
        if self.image_size > 0 and self.image_size != media_size:
            raise errors.InvalidHeader("Invalid media size: header claims {self.image_size}, expected {media_size} for {media.ui_name}")


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
    be compressed by any number of techniques. Subclasses of `Compressor`
    are used to transform compressed data into uncompressed bytes.

    Compressors may be chained, so the output of one compressor may become the
    input to the next. The order will be reversed upon saving, for example: a
    `dcm.gz` image will first be decompressed with the `gzip` algorithm, and
    that output will be in turn decompressed with the `DCM` algorithm. When
    writing the disk image back out to a file, it will be compressed with `DCM`
    before being `gzip`ped.
    """
    ui_name = "Raw Data"

    def __init__(self, data, decompression_order=None, style=None, origin=0, name="D1", error=None, verbose_name=None, memory_map=None, disasm_type=None, default_disasm_type=None, force_numpy_data=False):

        self.init_empty()
        if default_disasm_type is not None:
            self.default_disasm_type = default_disasm_type
        if force_numpy_data:
            # don't copy the data; use the data passed in as the raw data for
            # this container
            self._data = data
        else:
            self.data = data
        self.style = style
        self.disasm_type = disasm_type
        if decompression_order is None:
            decompression_order = [Uncompressed()]
        self.decompression_order = decompression_order

        self.origin = int(origin)  # force python int to decouple from possibly being a numpy datatype
        self.error = error
        self.name = name
        self.verbose_name = verbose_name
        if memory_map is not None:
            self.memory_map = memory_map

    def init_empty(self):
        self.segments = []
        self.header = None
        self._filesystem = None
        self._media = None
        self.mime = "application/octet-stream"
        self.pathname = ""
        self.default_disasm_type = 128  # libudis flag to use default CPU
        self.origin = 0
        self.error = ""
        self.name = ""
        self.verbose_name = ""
        self.memory_map = {}
        self.comments = {}
        self.uuid = utils.uuid()

        self._data = None
        self._style = None
        self._disasm_type = None

    #### properties

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, unpacked):
        if self._data is not None:
            raise errors.ReadOnlyContainer("container already populated with data")
        self._data = utils.to_numpy(unpacked)

    @property
    def style(self):
        return self._style

    @style.setter
    def style(self, value):
        if value is None:
            value = np.zeros(len(self._data), dtype=np.uint8)
        self._style = utils.to_numpy(value)

    @property
    def disasm_type(self):
        return self._disasm_type

    @disasm_type.setter
    def disasm_type(self, value):
        if value is None:
            value = np.zeros(len(self._data), dtype=np.uint8) + self.default_disasm_type
        self._disasm_type = utils.to_numpy(value)

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
        self._filesystem = None

    @property
    def filesystem(self):
        return self._filesystem

    @filesystem.setter
    def filesystem(self, value):
        self._filesystem = value
        self.segments = []
        if self.header:
            self.segments.append(self.header)
        if self.media:
            self.segments.append(self.media)

    @property
    def verbose_info(self):
        return self.container_info()

    def container_info(self, indent=""):
        lines = []
        name = self.verbose_name or self.name
        desc = f"{indent}{name}: {self.basename}, {len(self)} bytes, compression={','.join([c.compression_algorithm for c in self.decompression_order])}"
        lines.append(desc)
        for s in self.segments:
            v = s.segment_info(indent + "    ")
            lines.extend(v)
        return "\n".join(lines)

    @property
    def basename(self):
        return os.path.basename(self.pathname)

    #### dunder methods

    def __str__(self):
        return f"{self.basename}, size={len(self)}"

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

    #### iterators

    def iter_segments(self):
        for segment in self.segments:
            yield segment
            yield from segment.iter_segments()

    def iter_menu(self, level):
        for segment in self.segments:
            yield (segment, level)
            yield from segment.iter_menu(level + 1)

    def iter_dirents(self):
        for segment in self.media.segments:
            if isinstance(segment, Dirent):
                yield segment
            yield from segment.iter_segments(Dirent)

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

    def calc_packed_bytes(self, skip_missing_compressors=False):
        """Pack this container into a compressed data array using this packing
        algorithm.

        Can raise `InvalidAlgorithm` if one of the compressors is read-only
        (i.e. can only decompress data). However, if `skip_missing_compressors`
        is True, no error will be raised and compression will take place
        ignoring any compressors that can't compress data.
        """
        byte_data = self.data.tobytes()
        return compress_in_reverse_order(byte_data, self.decompression_order, self.media, skip_missing_compressors)

    #### media

    def guess_media_type(self):
        media = media_type.guess_media_type(self)
        self.media = media

    def guess_filesystem(self):
        fs = filesystem.guess_filesystem(self.media)
        self.filesystem = fs

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
        state['origin'] = int(self.origin)
        state['name'] = self.name
        state['verbose_name'] = self.verbose_name
        state['uuid'] = self.uuid
        state['error'] = self.error
        state['decompression_order'] = self.decompression_order
        state['default_disasm_type'] = int(self.default_disasm_type)
        state['memory_map'] = sorted([list(i) for i in self.memory_map.items()])

        # json serialization doesn't allow int keys, so convert to list of
        # pairs
        state['comments'] = self.get_sorted_comments()

        state['disasm_type'] = utils.collapse_values(self._disasm_type)

        state['header'] = self.header
        state['media'] = self.media
        state['filesystem'] = self.filesystem
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
        raw = np.zeros(size, dtype=np.uint8)
        self._data = raw
        self.style = None
        self.default_disasm_type = state.pop('default_disasm_type')
        self.disasm_type = None
        self.origin = state.pop('origin', 0)
        self.name = state.pop('name', "")
        self.verbose_name = state.pop('verbose_name', "")
        self.uuid = state.pop('uuid', utils.uuid())
        self.error = state.pop('error', "")
        self.decompression_order = state.pop('decompression_order', [])
        self.memory_map = dict(state.pop('memory_map', []))
        self.restore_comments(state.pop('comments', []))
        utils.restore_values(self._disasm_type, state.pop('disasm_type', []))

        self.header = state.pop('header')
        if self.header is not None:
            self.header.container = self
        self.restore_media(state)
        self.restore_filesystem(state)
        self.restore_containers()

        self.restore_backward_compatible_state(state)
        self.restore_missing_state()
        self.__dict__.update(state)
        self.restore_renamed_attributes()
        self.update_data_style_from_disasm_type()

    def restore_media(self, state):
        self.media = state.pop('media')

    def restore_filesystem(self, state):
        self.filesystem = state.pop('filesystem')

    def restore_containers(self):
        if self.media:
            self.media.container = self
        for segment in self.iter_segments():
            segment.container = self
            segment.restore_computed_defaults()

    def restore_backward_compatible_state(self, state):
        # convert old atrcopy stuff
        d = state.get('data ranges', None)
        if d is not None:
            utils.restore_value_to_ranges(self._disasm_type, d, 0)
        d = state.get('display list ranges', None)
        if d is not None:
            utils.restore_value_to_ranges(self._disasm_type, d, 30)

        d2 = state.get('user style 2', None)  # display list
        if d2 is not None:
            utils.restore_value_to_ranges(self._disasm_type, d2, 30)
        d3 = state.get('user style 3', None)  # jumpman level
        if d3 is not None:
            utils.restore_value_to_ranges(self._disasm_type, d3, 31)

        if d2 is not None and d2 == d3:
            # it seems that user styles 2 and 3 can point to the same ranges,
            # although 2 was supposed to be the display list and 3 the jumpman
            # level data. Try to disambiguate them because display lists
            # usually start out with 0x70, 0x70.
            for start, end in d2:
                if self._data[start] == 0x70 and self._data[start + 1] == 0x70:
                    self._disasm_type[start:end] = 30
                elif self._data[start] in [0xfc, 0xfd, 0xfe]:
                    self._disasm_type[start:end] = 32
                else:
                    self._disasm_type[start:end] = 30

        d = state.get('user style 4', None)  # jumpman harvest
        if d is not None:
            utils.restore_value_to_ranges(self._disasm_type, d, 31)

        d = state.get('comments', None)  # jumpman harvest
        if d is not None:
            self.restore_comments(d, overwrite=False)

        self.update_data_style_from_disasm_type()

    def restore_missing_state(self):
        """Hook for the future when extra serializable attributes are added to
        subclasses so new versions of the code can restore old saved files by
        providing defaults to any missing attributes.
        """
        pass

    def restore_renamed_attributes(self):
        """Hook for the future if attributes have been renamed. The old
        attribute names will have been restored in the __dict__.update in
        __setstate__, so this routine should move attribute values to their new
        names.
        """
        if hasattr(self, 'start_addr'):
            self.origin = self.start_addr
            log.debug(f"moving start_addr to origin: {self.start_addr}")
            delattr(self, 'start_addr')

    #### style

    def set_style_at_indexes(self, indexes, **kwargs):
        bits = style_bits.get_style_bits(**kwargs)
        self._style[indexes] |= bits

    def clear_style_at_indexes(self, indexes, **kwargs):
        style_mask = style_bits.get_style_mask(**kwargs)
        self.style[indexes] &= style_mask

    def get_style_ranges(self, **kwargs):
        """Return a list of start, end pairs that match the specified style
        """
        bits = style_bits.get_style_bits(**kwargs)
        matches = (self.style & bits) == bits
        return utils.bool_to_ranges(matches)

    def update_data_style_from_disasm_type(self):
        mask = style_bits.get_style_mask(data=True)
        self._style &= mask
        bits = style_bits.get_style_bits(data=True)
        indexes = np.where((self._disasm_type == 0) | ((self._disasm_type >= 30) & (self._disasm_type < 128)))[0]
        self._style[indexes] |= bits


    #### comments

    def clear_comments(self, indexes):
        mask = style_bits.get_style_mask(comment=True)
        style = self.style
        subset = style[indexes]
        comment_subset_indexes = np.where(subset & style_bits.comment_bit_mask)[0]
        print(f"clear_comments: deleting comments at {indexes}")
        style[indexes] &= mask
        for subset_index in comment_subset_indexes:
            del self.comments[indexes[subset_index]]

    def get_sorted_comments(self):
        return sorted([[int(k), str(v)] for k, v in self.comments.items()])

    def restore_comments(self, comments_list, overwrite=True):
        if overwrite:
            self.comments = {}
        bits = style_bits.get_style_bits(comment=True)
        style = self.style
        for k, v in comments_list:
            self.comments[k] = v
            style[k] |= bits

    def fixup_comments(self):
        """Remove any style bytes that are marked as commented but have no
        comment, and add any style bytes where there's a comment but it isn't
        marked in the style data.

        This happens on the base data, so only need to do this on one segment
        that uses this base data.
        """
        style_base = self._style
        comment_text_indexes = np.asarray(list(self.comments.keys()), dtype=np.uint32)
        comment_mask = style_bits.get_style_mask(comment=True)
        has_comments = np.where(style_base & style_bits.comment_bit_mask > 0)[0]
        both = np.intersect1d(comment_text_indexes, has_comments)
        log.info("fixup comments: %d correctly marked, %d without style, %d empty text" % (np.alen(both), np.alen(comment_text_indexes) - np.alen(both), np.alen(has_comments) - np.alen(both)))
        style_base &= comment_mask
        comment_style = style_bits.get_style_bits(comment=True)
        style_base[comment_text_indexes] |= comment_style

    #### search utilities

    def find_dirent(self, filename, match_case=False):
        for dirent in self.iter_dirents():
            dirent_name = dirent.filename
            if not match_case:
                dirent_name = dirent_name.lower()
                filename = filename.lower()
            print(f"checking {dirent_name} for {filename}")
            if dirent_name == filename:
                return dirent
        return None

    def find_uuid(self, uuid):
        for segment in self.iter_segments():
            if uuid == segment.uuid:
                return segment
        else:
            raise errors.InvalidSegment(f"No segment with uuid={uuid}")

def guess_container(data):
    data, compressors = guess_compressor_list(data)
    container = Container(data, compressors)
    return container


def load(pathname):
    sample_data = np.fromfile(pathname, dtype=np.uint8)
    container = guess_container(sample_data)
    container.pathname = pathname
    container.guess_media_type()
    return container
