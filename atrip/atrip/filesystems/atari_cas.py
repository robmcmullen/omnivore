import numpy as np

from .. import errors
from ..segment import Segment
from ..filesystem import VTOC, Dirent, Directory, Filesystem
from ..file_type import guess_file_type

try:  # Expensive debugging
    _xd = _expensive_debugging
except NameError:
    _xd = False

import logging
log = logging.getLogger(__name__)


class AtariCasDirent(Dirent):
    extra_serializable_attributes = ['start_index:int', 'bytes_on_tape:int', 'num_chunks:int', 'baud:int', '_filename']

    def __init__(self, directory, file_num, start_index):
        self.parse_chunks(directory, start_index)
        Dirent.__init__(self, directory, file_num, start_index, self.bytes_on_tape, parent=directory.filesystem.media)
        self.parse_chunks(directory, start_index)

    def init_empty(self):
        super().init_empty()
        self.start_index = 0
        self.bytes_on_tape = 0
        self.num_chunks = 0
        self.baud = 600
        self._filename = b''

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self.start_index == other.start_index and self.bytes_on_tape == other.bytes_on_tape and self.num_chunks == other.num_chunks

    @property
    def filename(self):
        return self._filename

    @property
    def catalog_entry(self):
        return "%d %s  %03d" % (self.start_index, self.filename, self.num_chunks)

    @property
    def status(self):
        return f"{self.baud} baud"

    @property
    def verbose_info(self):
        return self.status

    def parse_chunks(self, parent, index):
        self.start_index = index
        media = parent.filesystem.media
        chunk = media.get_chunk(index)
        log.debug(f"Reading chunk {chunk}")
        if chunk.chunk_type != "FUJI":
            raise errors.FileStructureError(f"Expecting FUJI chunk to begin file")
        self._filename = chunk.chunk_data.copy()
        index += chunk.record_length
        offsets = np.empty(parent.filesystem.max_file_size, dtype=np.uint32)
        offset_index = 0
        keep_reading = True
        while keep_reading:
            try:
                chunk = media.get_chunk(index)
            except errors.InvalidSectorNumber:
                # EOF; maybe it's a tape without the 0xfe record?
                break
            log.debug(f"Reading chunk {chunk}")
            if chunk.chunk_type == "FUJI":
                # somehow encountered another start chunk; previous was missing
                # an EOF record
                log.warning("Missing EOF record; assuming end of file")
                break
            elif chunk.chunk_type == "baud":
                self.baud = chunk.chunk_aux
            elif chunk.chunk_type == "data":
                d = chunk.chunk_data
                flag = d[2]
                data_size = chunk.chunk_length - 8 - 3 - 1
                if not (flag == 0xfa or flag == 0xfc or flag == 0xfe):
                    raise errors.FileStructureError(f"Unknown data record flag {flag}")
                if flag == 0xfe:
                    # end of file record
                    keep_reading = False
                offsets[offset_index:offset_index + data_size] = np.arange(index, index + data_size)
                offset_index += data_size
            index += chunk.record_length
        self.temporary_offset_storage = np.copy(offsets[0:offset_index])
        self.bytes_on_tape = index - self.start_index

    def parse_raw_dirent(self):
        pass

    def get_file(self):
        media = self.filesystem.media
        offsets = self.temporary_offset_storage
        del self.temporary_offset_storage
        if len(offsets) > 0:
            file_segment = guess_file_type(media, self.filename, offsets)
            self.segments = [file_segment]
            return file_segment


class AtariCasDirectory(Directory):
    def find_segment_location(self):
        return 0, 0

    def calc_dirents(self):
        segments = []
        start_index = 0
        filenum = 0
        try:
            while True:
                dirent = AtariCasDirent(self, filenum, start_index)
                segments.append(dirent)
                start_index = dirent.start_index + dirent.bytes_on_tape
                filenum += 1
        except (errors.MediaError, errors.FileError):
            pass
        return segments


class AtariCassetteFilesystem(Filesystem):
    ui_name = "Atari Cassette (.cas)"
    default_executable_extension = "XEX"

    def check_media(self, media):
        try:
            media.get_chunk
        except AttributeError:
            raise errors.IncompatibleMediaError(f"{self.ui_name} only valid on cassette media")

    def calc_directory_segment(self):
        return AtariCasDirectory(self)
