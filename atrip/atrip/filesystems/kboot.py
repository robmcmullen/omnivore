import numpy as np

from .. import errors
from ..segment import Segment
from ..filesystem import VTOC, Dirent, Directory, Filesystem
from .atari_dos2 import AtariDos2, AtariDos2Directory
from ..file_type import guess_file_type

class KBootDirent(Dirent):
    def __init__(self, directory):
        Dirent.__init__(self, directory, 0, 0, 0)

    def parse_raw_dirent(self):
        self.starting_sector = 4
        self.basename = self.container.basename
        if not self.basename:
            self.basename = b"KBOOT"
        if self.basename == self.basename.upper():
            self.ext = b"XEX"
        else:
            self.ext = b"xex"
        media = self.filesystem.media
        start, size = media.get_index_of_sector(4)
        i = 9
        count = media[i] + 256 * media[i+1] + 256 * 256 *media[i + 2]
        if start + count > len(media) or start + count < len(media) - 128:
            raise errors.NotEnoughSpaceOnDisk(f"KBoot header reports size {count}; media only {len(media)}")
        else:
            self.exe_size = count
            self.exe_start = start
        self.num_sectors = count // 128 + 1

    @property
    def filename(self):
        ext = (b'.' + self.ext) if self.ext else b''
        return (self.basename + ext).decode('latin1')

    @property
    def catalog_entry(self):
        return "%03d %-8s%-3s  %03d" % (4, self.basename.decode("latin1"), self.ext.decode("latin1"), self.num_sectors)

    def get_file(self):
        media = self.filesystem.media
        file_segment = guess_file_type(media, self.filename, self.exe_start, length=self.exe_size)
        self.segments = [file_segment]
        return file_segment


class KBootDirectory(AtariDos2Directory):
    def find_segment_location(self):
        media = self.media
        return 0, 0

    def calc_dirents(self):
        segments = [KBootDirent(self)]
        return segments


class KBoot(AtariDos2):
    ui_name = "Atari KBoot"
    default_executable_extension = "XEX"

    def calc_vtoc_segment(self):
        pass

    def calc_directory_segment(self):
        return KBootDirectory(self)

    @classmethod
    def create_boot_image(cls, segments, run_addr=None):
        data_segment, _ = get_xex(segments)
        payload_bytes = add_xexboot_header(data_segment.data)
        data_bytes = np.zeros(len(payload_bytes) + 16, np.uint8)
        data_bytes[16:] = payload_bytes[:]
        header_bytes = data_bytes[0:16]
        atr_header = AtrHeader(create=True)
        atr_header.check_size(len(payload_bytes))
        atr_header.encode(header_bytes)
        raw = SegmentData(data_bytes)
        atr = cls(raw, create=True)
        return atr


xexboot_header = b'\x00\x03\x00\x07\r\x07L\r\x07\x1c[\x00\x00\xa0\x00\x8c\t\x03\x8c\x04\x03\x8cD\x02\x8c\xe2\x02\x8c\xe3\x02\xc8\x84\t\x8c\x01\x03\xce\x06\x03\xa91\x8d\x00\x03\xa9R\x8d\x02\x03\xa9\x80\x8d\x08\x03\xa9\x01\x8d\x05\x03\xa9\xe3\x8d0\x02\x8d\x02\xd4\xa9\x07\x8d1\x02\x8d\x03\xd4\xa9\x00\xaa\x8d\x0b\x03\xa9\x04\x8d\n\x03 \xbc\x07\xca \xa5\x07\x85C \xa5\x07\x85D%C\xc9\xff\xf0\xf0 \xa5\x07\x85E \xa5\x07\x85F \xa5\x07\x91C\xe6C\xd0\x02\xe6D\xa5E\xc5C\xa5F\xe5D\xb0\xeb\xad\xe2\x02\r\xe3\x02\xf0\xc9\x86\x19 \xa2\x07\xa6\x19\xa0\x00\x8c\xe2\x02\x8c\xe3\x02\xf0\xb8l\xe2\x02\xad\t\x07\xd0\x0b\xad\n\x07\xd0\x03l\xe0\x02\xce\n\x07\xce\t\x07\xe0\x80\x90"\xa9@\x8d\x03\x03 Y\xe4\x10\x06\xce\x01\x07\xd0\xf1\x00\xee\n\x03\xd0\x03\xee\x0b\x03\xad\n\x03\x8d\x19\xd0\xa0\x00\xa2\x00\xbd\x00\x01\xe8`pppppF\xf8\x07p\x07ppp\x06p\x06p\x06A\xe3\x07\x00\x00\x00\x00\x00,/!$).\'\x0e\x0e\x0e\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00&2/-'


def insert_bytes(data, offset, string, color):
    s = np.frombuffer(string.upper(), dtype=np.uint8) - 32  # convert to internal
    s = s | color
    count = len(s)
    tx = offset + (20 - count) // 2
    data[tx:tx+count] = s


def add_xexboot_header(bytes, bootcode=None, title=b"DEMO", author=b"an atari user"):
    sec_size = 128
    xex_size = len(bytes)
    num_sectors = (xex_size + sec_size - 1) // sec_size
    padded_size = num_sectors * sec_size
    if xex_size < padded_size:
        bytes = np.append(bytes, np.zeros([padded_size - xex_size], dtype=np.uint8))
    paragraphs = padded_size // 16

    if bootcode is None:
        bootcode = np.copy(np.frombuffer(xexboot_header, dtype=np.uint8))
    else:
        # don't insert title or author in user supplied bootcode; would have to
        # assume that the user supplied everything desired in their own code!
        title = ""
        author = ""
    bootsize = np.alen(bootcode)
    v = bootcode[9:11].view(dtype="<u2")
    v[0] = xex_size

    bootsectors = np.zeros([384], dtype=np.uint8)
    bootsectors[0:bootsize] = bootcode

    insert_bytes(bootsectors, 268, title, 0b11000000)
    insert_bytes(bootsectors, 308, author, 0b01000000)

    image = np.append(bootsectors, bytes)
    return image
