import numpy as np

from .. import errors
from ..segment import Segment
from ..filesystem import VTOC, Dirent, Directory, Filesystem
from ..file_type import guess_file_type
from ..char_mapping import internal_to_atascii, atascii_to_internal
from .atari_dos2 import AtariDos2, AtariDosBootSegment

try:  # Expensive debugging
    _xd = _expensive_debugging
except NameError:
    _xd = False


class AtariJumpmanBootSegment(AtariDosBootSegment):
    def find_segment_location(self, media):
        self.bldadr = 0x700
        try:
            sectors = list(range(1, 8))  # sectors 1 - 7
            sectors.extend(range(560, 720))  # sectors 560 - 719
            indexes = media.get_sector_list_offsets(sectors)
        except errors.MediaError as e:
            raise errors.IncompatibleMediaError(f"Invalid boot sector: {e}")
        return indexes, 0

    def calc_boot_segments(self):
        header = Segment(self, 0, 0x700, "Boot Header", length=6)
        code = Segment(self, 6, 0x706, name="Boot Code", length=0x380 - 6)
        game = Segment(self, 0x380, 0x2000, name="Game Code", length=0x5000)
        game.segments = [
            Segment(game, 0, 0x2000, name="Game Code, Part 1", length=0x800),
            Segment(game, 0x800, 0x2800, name="Level Definition", length=0x800),
            Segment(game, 0x1000, 0x4000, name="Game Code, Part 2", length=0x4000),
        ]
        return [header, code, game]


class AtariJumpmanDirent(Dirent):
    format = np.dtype([
        ('ID', 'S2'),
        ('NAME','S20'),
        ])
    dirent_size = format.itemsize

    def __init__(self, directory, file_num):
        start = file_num * self.dirent_size
        self.id = b''
        self.level_name = b''
        Dirent.__init__(self, directory, file_num, start, self.dirent_size)

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self.id == other.id

    def __str__(self):
        return f"Level {self.id.decode('latin1')}: {self.level_name.decode('latin1')}"

    @property
    def filename(self):
        return self.level_name

    def parse_raw_dirent(self):
        data = self.data[:]
        data[2:] = internal_to_atascii[data[2:] & 0x3f]
        values = data.view(dtype=self.format)[0]
        self.id = values[0]
        self.level_name = values[1].strip()
        # print(self.file_num, data, values[1], self.level_name)

    def encode_dirent(self):
        data = np.zeros([self.dirent_size], dtype=np.uint8)
        values = data.view(dtype=self.format)[0]
        values[0] = self.id
        values[1] = self.level_name
        return data

    def get_file(self):
        media = self.filesystem.media
        index, size = media.get_contiguous_sectors_offsets(17 + (16 * self.file_num), 16)
        file_segment = guess_file_type(media, self.filename, index, size)
        self.segments = [file_segment]
        return file_segment

    def sanity_check(self):
        return len(self) == 0x800


class AtariJumpmanDirectory(Directory):
    ui_name = "Jumpman Levels"

    def __str__(self):
        num_entries = len(self) // AtariJumpmanDirent.dirent_size
        s = f"{self.name} ({num_entries} level"
        if num_entries != 1:
            s += "s"
        s += ")"
        if self.error:
            s += " " + self.error
        return s

    def find_first_level(self, media):
        index, size = media.get_contiguous_sectors_offsets(17, 16 * 32)
        return index, size

    def find_segment_location(self):
        media = self.media
        index, size = self.find_first_level(media)
        level_count = size // 0x800
        indexes = np.empty(AtariJumpmanDirent.dirent_size * level_count, dtype=np.int32)
        data_index = index
        dirent_index = 0
        for filenum in range(level_count):
            if media[data_index + 0x48] == 0x20 and media[data_index + 0x4b] == 0x60 and media[data_index + 0x4c] == 0xff: 
                name = data_index + 0x2bec - 0x2800
                level = np.arange(name - 2, name + 20, dtype=np.uint32)
                level[0] = data_index
                level[1] = data_index + 1
                indexes[dirent_index:dirent_index + AtariJumpmanDirent.dirent_size] = level
                data_index += 0x800
                dirent_index += AtariJumpmanDirent.dirent_size
            else:
                raise errors.FilesystemError(f"Jumpman level signature not present")
        return indexes, 0

    def calc_dirents(self):
        segments = []
        filenum = 0
        pointer = 0
        while pointer < len(self):
            filenum = pointer // AtariJumpmanDirent.dirent_size
            dirent = AtariJumpmanDirent(self, filenum)
            pointer += AtariJumpmanDirent.dirent_size
            segments.append(dirent)
        return segments


class AtariJumpman(AtariDos2):
    ui_name = "Atari Jumpman"

    def check_media(self, media):
        AtariDos2.check_media(self, media)
        if media.sector_size != 128:
            raise errors.IncompatibleMediaError(f"{self.ui_name} requires SD")

    def calc_boot_segment(self):
        return AtariJumpmanBootSegment(self)

    def calc_vtoc_segment(self):
        return None

    def calc_directory_segment(self):
        return AtariJumpmanDirectory(self)



class AtariJumpmanLevelTesterBootSegment(AtariDosBootSegment):
    def find_segment_location(self, media):
        self.bldadr = 0x700
        start, size = media.get_index_of_sector(4)
        i = 9
        count = media[i] + 256 * media[i+1] + 256 * 256 *media[i + 2]
        if start + count > len(media) or start + count < len(media) - 128:
            raise errors.NotEnoughSpaceOnDisk(f"KBoot header reports size {count}; media only {len(media)}")
        else:
            self.exe_size = count
            self.exe_start = start
        return 0, len(media)

    def calc_boot_segments(self):
        header = Segment(self, 0, 0x700, "Boot Header", length=6)
        code = Segment(self, 6, 0x706, name="Boot Code", length=0x180 - 6)

        file_segment = guess_file_type(self, "Jumpman Level", self.exe_start, self.exe_size)
        return [header, code, file_segment]


class AtariJumpmanLevelTesterDirectory(AtariJumpmanDirectory):
    def find_first_level(self, media):
        start, size = media.get_index_of_sector(4)
        i = 9
        count = media[i] + 256 * media[i+1] + 256 * 256 *media[i + 2]
        if start + count > len(media) or start + count < len(media) - 128:
            raise errors.NotEnoughSpaceOnDisk(f"Jumpman Level Tester header reports size {count}; media only {len(media)}")
        else:
            exe_size = count
            exe_start = start
        file_segment = guess_file_type(media, "Jumpman Level Tester", exe_start, exe_size)
        index = None
        if len(file_segment.segments) > 0:
            s = file_segment.segments[0].segments[0]
            if s.origin == 0x8800:
                # Jumpman level tester loads initial level at $8800, then the
                # code moves it down
                #
                # Need index relative to media; container_offset is absolute
                # position in source file and media is at some offset from the
                # beginning of the container.
                index = s.container_offset[0] - media.container_offset[0]
        if index is None:
            raise errors.FilesystemError("Not recognized as a Jumpman Level Tester image")
        return index, 0x800


class AtariJumpmanLevelTester(AtariJumpman):
    ui_name = "Atari Jumpman Level Tester"

    def calc_boot_segment(self):
        return AtariJumpmanLevelTesterBootSegment(self)

    def calc_directory_segment(self):
        return AtariJumpmanLevelTesterDirectory(self)
