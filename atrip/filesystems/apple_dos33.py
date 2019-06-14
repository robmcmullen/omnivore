import numpy as np

from .. import errors
from ..segment import Segment
from ..filesystem import VTOC, Dirent, Directory, Filesystem
from ..file_type import guess_file_type

import logging
log = logging.getLogger(__name__)
try:  # Expensive debugging
    _xd = _expensive_debugging
except NameError:
    _xd = False


class Dos33BootSegment(Segment):
    ui_name = "DOS 3.3 Boot"
    def __init__(self, filesystem):
        media = filesystem.media
        Segment.__init__(self, media, 0, 0, name="Boot Sectors", length=256*37)
        self.segments = self.calc_boot_segments()

    def calc_boot_segments(self):
        boot1 = Segment(self, 0, 0x800, "Boot 1", length=256)
        boot2 = Segment(self, 256, 0x3700, "Boot 2", length=9*256)
        relocator = Segment(self, 10*256, 0x1b00, "Relocator", length=2*256)
        boot3 = Segment(self, 12*256, 0x1d00, "Boot 3", length=25*256)
        return [boot1, boot2, relocator, boot3]


class Dos33VTOC(VTOC):
    ui_name = "DOS 3.3 VTOC"
    max_tracks = (256 - 0x38) // 4  # 50, but kept here in case sector size changed
    max_sector = max_tracks * 16
    vtoc_bit_reorder_index = np.tile(np.arange(15, -1, -1), max_tracks) + (np.repeat(np.arange(max_tracks), 16) * 16)

    vtoc_type = np.dtype([
        ('unused1', 'S1'),
        ('cat_track','u1'),
        ('cat_sector','u1'),
        ('dos_release', 'u1'),
        ('unused2', 'S2'),
        ('vol_num', 'u1'),
        ('unused3', 'S32'),
        ('max_pairs', 'u1'),
        ('unused4', 'S8'),
        ('last_track', 'u1'),
        ('track_dir', 'i1'),
        ('unused5', 'S2'),
        ('num_tracks', 'u1'),
        ('sectors_per_track', 'u1'),
        ('sector_size', 'u2'),
        ])

    def find_segment_location(self):
        media = self.media
        index = 17 * 16
        if not media.is_sector_valid(index):
            raise errors.FilesystemError(f"Media ends before track 17")
        return media.get_contiguous_sectors_offsets(index, 1)

    def calc_sector_map_size(self):
        values = self[0:self.vtoc_type.itemsize].view(dtype=self.vtoc_type)[0]
        print(self.container_offset)
        print(values)
        media = self.media
        media.first_directory_track = int(values['cat_track'])
        media.first_directory_sector = int(values['cat_sector'])
        media.sector_size = int(values['sector_size'])
        media.max_sectors = int(values['num_tracks']) * int(values['sectors_per_track'])
        media.ts_pairs = int(values['max_pairs'])
        media.dos_release = int(values['dos_release'])
        media.last_track_num = int(values['last_track'])
        media.track_alloc_dir = int(values['track_dir'])
        return self.max_sector

    def unpack_vtoc(self):
        # VTOC stored in groups of 4 bytes starting at 0x38
        # in bits, the sector used data is stored by track:
        #
        # FEDCBA98 76543210 xxxxxxxx xxxxxxxx
        #
        # where the x values are ignored (should be zeros). Track 0 info is
        # found starting at 0x38, track 1 is found at 0x3c, etc.
        #
        # Want to convert this to an array that is a list of bits by
        # track/sector number, i.e.:
        #
        # t0s0 t0s1 t0s2 t0s3 t0s4 t0s5 t0s6 t0s7 ... t1s0 t1s1 ... etc
        #
        # Problem: the bits are stored backwards, so a straight unpackbits will
        # produce:
        #
        # t0sf t0se t0sd ...
        #
        # i.e. each group of 16 bits needs to be reversed.

        # create a view starting at 0x38 where out of every 4 bytes, the first
        # two are used and the second 2 are skipped. Regular slicing doesn't
        # work like this, so thanks to stackoverflow.com/questions/33801170,
        # reshaping it to a 2d array with 4 elements in each row, doing a slice
        # *there* to skip the last 2 entries in each row, then flattening it
        # gives us what we need.
        usedbytes = self[0x38:].reshape((-1, 4))[:,:2].flatten()

        # The bits here are still ordered backwards for each track, e.g. F E D
        # C B A 9 8 7 6 5 4 3 2 1 0
        bits = np.unpackbits(usedbytes)

        # so we need to reorder them using numpy's indexing before stuffing
        # them into the sector map
        self.sector_map[0:self.max_sector] = bits[self.vtoc_bit_reorder_index]
        if _xd: log.debug("vtoc before:\n%s" % str(self))  # expensive debugging call

    def pack_vtoc(self):
        if _xd: log.debug("vtoc after:\n%s" % str(self))  # expensive debugging call

        # reverse the process from above, so swap the order of every 16 bits,
        # turn them into bytes, then stuff them back into the vtoc. The bit
        # reorder list is commutative, so we don't need another order here.
        packed = np.packbits(self.sector_map[self.vtoc_bit_reorder_index])
        vtoc = self[0x38:].reshape((-1, 4))
        packed = packed.reshape((-1, 2))
        vtoc[:,:2] = packed[:,:]

        # FIXME
        self[0x38:] = vtoc.flatten()


class Dos33Dirent(Dirent):
    ui_name = "DOS 3.3 Dirent"
    format = np.dtype([
        ('track', 'u1'),
        ('sector', 'u1'),
        ('flag', 'u1'),
        ('name','S30'),
        ('num_sectors','<u2'),
        ])

    def __init__(self, directory, filenum):
        start = self.format.itemsize * filenum
        Dirent.__init__(self, directory, filenum, start, self.format.itemsize)
        self._file_type = 0
        self.locked = False
        self.deleted = False
        self.track = 0
        self.sector = 0
        self.filename = ""
        self.num_sectors = 0
        self.current_sector_index = 0
        self.current_read = 0
        self.sectors_seen = None
        self.sector_map = None

    def __str__(self):
        return "File #%-2d (%s) %03d %-30s %03d %03d" % (self.file_num, self.verbose_info, self.num_sectors, self.filename, self.track, self.sector)

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self.filename == other.filename and self.track == other.track and self.sector == other.sector and self.num_sectors == other.num_sectors

    type_to_text = {
        0x0: "T",  # text
        0x1: "I",  # integer basic
        0x2: "A",  # applesoft basic
        0x4: "B",  # binary
        0x8: "S",  # ?
        0x10: "R",  # relocatable object module
        0x20: "a",  # ?
        0x40: "b",  # ?
    }
    text_to_type = {v: k for k, v in type_to_text.items()}

    @property
    def file_type(self):
        """User friendly version of file type, not the binary number"""
        return self.type_to_text.get(self._file_type, "?")

    @property
    def verbose_info(self):
        if self.deleted:
            locked = "D"
            file_type = " "
        else:
            locked = "*" if self.locked else " "
            file_type = self.file_type
        flag = "%s%s" % (locked, file_type)
        return flag

    @property
    def flag(self):
        return 0xff if self.deleted else self._file_type | (0x80 * int(self.locked))

    def parse_raw_dirent(self):
        data = self.data[0:self.format.itemsize]
        values = data.view(dtype=self.format)[0]
        self.track = values[0]
        if self.track == 0xff:
            self.deleted = True
            self.track = data[0x20]
        else:
            self.deleted = False
        self.sector = values[1]
        self._file_type = values[2] & 0x7f
        self.locked = values[2] & 0x80
        self.filename = (data[3:0x20] - 0x80).tobytes().rstrip().decode("ascii", errors='ignore')
        self.num_sectors = int(values[4])
        self.is_sane = self.sanity_check()

    def encode_dirent(self):
        data = np.zeros([self.format.itemsize], dtype=np.uint8)
        values = data.view(dtype=self.format)[0]
        values[0] = 0xff if self.deleted else self.track
        values[1] = self.sector
        values[2] = self.flag
        n = min(len(self.filename), 30)
        data[3:3+n] = np.frombuffer(self.filename.encode("ascii"), dtype=np.uint8) | 0x80
        data[3+n:] = ord(' ') | 0x80
        if self.deleted:
            data[0x20] = self.track
        values[4] = self.num_sectors
        return data

    def sanity_check(self):
        media = self.filesystem.media
        if self.deleted:
            return True
        if self.track == 0:
            return False
        s = media.sector_from_track(self.track, self.sector)
        if not media.is_sector_valid(s):
            return False
        if self.num_sectors < 0 or self.num_sectors > media.max_sectors:
            return False
        return True

    def get_file(self):
        media = self.filesystem.media
        tslist = self.get_track_sector_list()
        offsets = media.follow_track_sector_list(tslist)
        if len(offsets) > 0:
            file_segment = guess_file_type(media, self.filename, offsets)
            self.segments = [tslist, file_segment]
            return file_segment

    def get_track_sector_list(self):
        media = self.filesystem.media
        offsets = media.follow_track_sector_pointers(self.track, self.sector, 0xc, 2 * 122)
        return Segment(media, offsets, 0, "Track/Sector List")

    def get_sectors_in_vtoc(self, image):
        self.get_track_sector_list(image)
        sectors = BaseSectorList(media)
        sectors.extend(self.track_sector_list)
        for sector_num in self.sector_map:
            sector = WriteableSector(media.sector_size, None, sector_num)
            sectors.append(sector)
        return sectors

    def get_filename(self):
        return self.filename

    def set_values(self, filename, filetype, index):
        self.filename = '%-30s' % filename[0:30]
        self._file_type = self.text_to_type.get(filetype, 0x04)
        self.locked = False
        self.deleted = False

    def get_binary_start_address(self, image):
        self.start_read(image)
        data, _, _, _ = self.read_sector(image)
        addr = int(data[0]) + 256 * int(data[1])
        return addr


class Dos33Directory(Directory):
    ui_name = "DOS 3.3 Directory"

    def find_segment_location(self):
        media = self.media
        offsets = media.follow_track_sector_pointers(media.first_directory_track, media.first_directory_sector, 0x0b, 7 * 0x23)
        return offsets, 0

    def calc_dirents(self):
        segments = []
        index = 0
        filenum = 0
        while index < len(self):
            dirent = Dos33Dirent(self, filenum)
            if dirent.in_use:
                dirent.set_comment_at(0x00, "FILE #%d: Track number of next catalog sector" % filenum)
                dirent.set_comment_at(0x01, "FILE #%d: Sector number of next catalog sector" % filenum)
                dirent.set_comment_at(0x02, "FILE #%d: File type" % filenum)
                dirent.set_comment_at(0x03, "FILE #%d: Filename" % filenum)
                dirent.set_comment_at(0x21, "FILE #%d: Number of sectors in file" % filenum)
                segments.append(dirent)
            index += len(dirent)
            filenum += 1
        return segments


class AppleDos33(Filesystem):
    ui_name = "Apple DOS 3.3"
    default_executable_extension = "BIN"

    def check_media(self, media):
        try:
            media.sector_from_track
        except AttributeError:
            raise errors.IncompatibleMediaError("Apple DOS needs track/sector access")

    def calc_boot_segment(self):
        return Dos33BootSegment(self)

    def calc_vtoc_segment(self):
        return Dos33VTOC(self)

    def calc_directory_segment(self):
        return Dos33Directory(self)
