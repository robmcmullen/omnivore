import numpy as np

from .. import errors
from ..media_type import DiskImage
from ..segment import Segment
from ..container import ContainerHeader

import logging
log = logging.getLogger(__name__)


class CassetteChunk:
    def __init__(self, media, index):
        header = media[index:index + 8]
        if len(header) < 8:
            raise errors.InvalidSectorNumber(f"tape position {index} beyond end of tape")
        self.tape_index = index
        flag = header[0:4].view(dtype='>u4')
        self.chunk_length = int(header[4] + header[5] * 256)
        self.chunk_aux = int(header[6] + header[7] * 256)
        self.record_length = self.chunk_length + 8
        if flag == 0x46554a49:  # FUJI in big-endian hex
            self.chunk_type = "FUJI"
        elif flag == 0x62617564:  # baud in big-endian hex
            self.chunk_type = "baud"
        elif flag == 0x64617461:  # daha in big-endian hex
            self.chunk_type = "data"
        else:
            try:
                name = flag.decode("latin1")
            except:
                name = hex(flag)
            raise errors.UnsupportedSectorType(f"Can't handle {name} chunk types")
        self.chunk_data = media[index + 8:index + 8 + self.chunk_length]
        if len(self.chunk_data) < self.chunk_length:
            raise errors.InvalidSectorNumber(f"chunk {self.chunk_type} at tape index {index} specifies {self.chunk_length} bytes but ran out of tape")

    def __str__(self):
        return f"{self.chunk_type}: {self.chunk_length} bytes at tape index {self.tape_index}"


class AtariCassetteImage(DiskImage):
    ui_name = "Atari Cassette Image (.cas)"

    def check_media_size(self):
        size = len(self)
        if size < 8:
            raise errors.InvalidMediaSize(f"{self.ui_name} too small to be valid image")

    def check_magic(self):
        flag = self[0:4].view(dtype='>u4')
        if flag != 0x46554a49:  # FUJI in big-endian hex
            raise errors.InvalidHeader("Not a .cas image; FUJI chunk not found")

    def get_chunk(self, index):
        return CassetteChunk(self, index)
