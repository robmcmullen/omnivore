import numpy as np

from .. import errors
from ..segment import Segment
from ..filesystem import VTOC, Dirent, Directory, Filesystem
from ..file_type import guess_file_type
from ..char_mapping import internal_to_atascii, atascii_to_internal
from .atari_dos2 import AtariDos2, AtariDosBootSegment
from ..machines.atari8bit.jumpman import playfield

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
    ui_name = "Jumpman Level"
    name_offset = 0x2bec - 0x2800
    dirent_size = 0x800
    extra_serializable_attributes = ['file_num', 'in_use', 'is_sane', 'id', 'level_name', 'assembly_source']

    def __init__(self, directory, file_num):
        start = file_num * self.dirent_size
        self.id = b''
        self.level_name = b''
        self.assembly_source = None
        Dirent.__init__(self, directory, file_num, start, self.dirent_size)
        self.name = str(self)
        self.origin = 0x2800
        self.restore_computed_defaults()

    def restore_computed_defaults(self):
        self.jumpman_playfield_model = playfield.JumpmanPlayfieldModel(self)

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self.id == other.id

    def __str__(self):
        return f"Level {self.id.decode('latin1')}: {self.level_name.decode('latin1')}"

    @property
    def filename(self):
        return self.level_name

    def parse_raw_dirent(self):
        data = self.data[:]
        self.id = bytes(data[0:2].view(dtype="S2"))
        name = internal_to_atascii[data[self.name_offset:self.name_offset + 20] & 0x3f]
        self.level_name = bytes(name).strip()

    def encode_dirent(self):
        data = np.zeros([self.dirent_size], dtype=np.uint8)
        values = data.view(dtype=self.format)[0]
        values[0] = self.id
        values[1] = self.level_name
        return data

    def get_file(self):
        return None

    def sanity_check(self):
        return len(self) == 0x800

    def set_assembly_source(self, src):
        """Assembly source file is required to be in the same directory as the
        jumpman disk image. It's also assumed to be on the local filesystem
        since pyatasm can't handle the virtual filesystem.
        """
        self.assembly_source = src
        self.jumpman_playfield_model.compile_assembly_source()


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
        return index, size

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

    def find_interesting_segment(self):
        levels = list(self.iter_dirents())
        if levels:
            return levels[0]
        return None


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
