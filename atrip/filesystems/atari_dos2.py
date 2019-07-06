import numpy as np

from .. import errors
from ..segment import Segment
from ..filesystem import VTOC, Dirent, Directory, Filesystem
from ..file_type import guess_file_type

try:  # Expensive debugging
    _xd = _expensive_debugging
except NameError:
    _xd = False


class AtariDosBootSegment(Segment):
    ui_name = "DOS2 Boot Segment"
    boot_record_type = np.dtype([
        ('BFLAG', 'u1'),
        ('BRCNT', 'u1'),
        ('BLDADR', '<u2'),
        ('BWTARR', '<u2'),
        ])

    extra_serializable_attributes = ['bflag:int', 'brcnt:int', 'bldadr:int']

    def __init__(self, filesystem):
        media = filesystem.media
        indexes, size = self.find_segment_location(media)
        Segment.__init__(self, media, indexes, self.bldadr, name="Boot Sectors", length=size)
        self.segments = self.calc_boot_segments()

    def init_empty(self):
        super().init_empty()
        self.bflag = 0
        self.brcnt = 0
        self.bldadr = 0

    def find_segment_location(self, media):
        try:
            values = media[0:6].view(dtype=self.boot_record_type)[0]
            self.bflag = values['BFLAG']
            if self.bflag == 0:
                # possible boot sector
                self.brcnt = values['BRCNT']
                if self.brcnt == 0:
                    self.brcnt = 3
            else:
                self.brcnt = 3
            self.bldadr = values['BLDADR']
            index, _ = media.get_index_of_sector(1 + self.brcnt)
        except errors.MediaError as e:
            raise errors.IncompatibleMediaError(f"Invalid boot sector: {e}")
        return 0, index

    def calc_boot_segments(self):
        header = Segment(self, 0, self.bldadr, "Boot Header", length=6)
        code = Segment(self, 6, self.bldadr + 6, name="Boot Code", length=len(self) - 6)
        return [header, code]


class AtariDos1SectorVTOC(VTOC):
    ui_name = "DOS2 SD VTOC"

    vtoc_type = np.dtype([
        ('code', 'u1'),
        ('total','<u2'),
        ('unused','<u2'),
        ])

    max_sector = 720

    extra_serializable_attributes = ['total_sectors:int', 'unused_sectors:int']

    def find_segment_location(self):
        media = self.media
        if not media.is_sector_valid(360):
            raise errors.FilesystemError(f"Media ends before sector 360")
        return media.get_contiguous_sectors_offsets(360, 1)

    def calc_sector_map_size(self):
        values = self[0:5].view(dtype=self.vtoc_type)[0]
        code = values[0]
        if code == 0 or code == 2:
            pass
        else:
            raise errors.FilesystemError(f"Invalid VTOC code {code}")
        self.total_sectors = values[1]
        if self.total_sectors > self.max_sector:
            raise errors.FilesystemError(f"Invalid number of sectors {self.total_sectors}")
        self.unused_sectors = values[2]
        return self.max_sector

    def unpack_vtoc(self):
        bits = np.unpackbits(self[0x0a:0x64])
        self.sector_map[0:720] = bits
        if _xd: log.debug("vtoc before:\n%s" % str(self))

    def pack_vtoc(self):
        if _xd: log.debug("vtoc after:\n%s" % str(self))
        packed = np.packbits(self.sector_map[0:720])
        self[0x0a:0x64] = packed


class AtariDos2SectorVTOC(AtariDos1SectorVTOC):
    ui_name = "DOS2 ED VTOC"

    max_sector = 1040

    def find_segment_location(self):
        if self.media.num_sectors != 1040:
            raise errors.FilesystemError(f"Not enhanced density disk")
        return self.media.get_sector_list_offsets([360, 1024]), 0

    def unpack_vtoc(self):
        bits = np.unpackbits(self[0x0a:0x64])
        self.sector_map[0:720] = bits
        bits = np.unpackbits(self[0xd4:0xfa])  # 0x44 - 0x7a in 2nd sector
        self.sector_map[720:1024] = bits
        if _xd: log.debug("vtoc before:\n%s" % str(self))

    def pack_vtoc(self):
        if _xd: log.debug("vtoc after:\n%s" % str(self))
        packed = np.packbits(self.sector_map[0:720])
        self[0x0a:0x64] = packed
        packed = np.packbits(self.sector_map[720:1024])
        self[0xd4:0xfa] = packed


class AtariDosDirent(Dirent):
    ui_name = "DOS2 Dirent"
    extra_serializable_attributes = ['file_num', 'in_use', 'is_sane', 'flag:int', 'num_sectors', 'starting_sector', 'basename', 'ext']

    # ATR Dirent structure described at http://atari.kensclassics.org/dos.htm
    format = np.dtype([
        ('FLAG', 'u1'),
        ('COUNT', '<u2'),
        ('START', '<u2'),
        ('NAME','S8'),
        ('EXT','S3'),
        ])

    FLAG_OPENED_OUTPUT = 0x01
    FLAG_DOS_2 = 0x02
    FLAG_MYDOS = 0x04
    FLAG_IS_DIR = 0x10
    FLAG_LOCKED = 0x20
    FLAG_IN_USE = 0x40
    FLAG_DELETED = 0x80

    def __init__(self, directory, file_num):
        start = file_num * self.format.itemsize
        self.flag = 0  # self.flag needs to have a value, but don't want to got through init_empty twice
        Dirent.__init__(self, directory, file_num, start, self.format.itemsize)

    def init_empty(self):
        super().init_empty()
        self.flag = 0
        self.num_sectors = 0
        self.starting_sector = 0
        self.basename = b''
        self.ext = b''

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self.filename == other.filename and self.starting_sector == other.starting_sector and self.num_sectors == other.num_sectors

    @property
    def opened_output(self):
        return bool(self.flag & self.FLAG_OPENED_OUTPUT)

    @property
    def dos_2(self):
        return bool(self.flag & self.FLAG_DOS_2)

    @property
    def mydos(self):
        return bool(self.flag & self.FLAG_MYDOS)

    @property
    def is_dir(self):
        return bool(self.flag & self.FLAG_IS_DIR)

    @property
    def locked(self):
        return bool(self.flag & self.FLAG_LOCKED)

    @property
    def in_use(self):
        return bool(self.flag & self.FLAG_IN_USE)

    @in_use.setter
    def in_use(self, value):
        if value:
            self.flag |= self.FLAG_IN_USE
        else:
            self.flag &= 0xff ^ self.FLAG_IN_USE

    @property
    def deleted(self):
        return bool(self.flag & self.FLAG_DELETED)

    @property
    def filename(self):
        ext = (b'.' + self.ext) if self.ext else b''
        return (self.basename + ext).decode('latin1')

    @property
    def catalog_entry(self):
        return "%03d %-8s%-3s  %03d" % (self.starting_sector, self.basename.decode("latin1"), self.ext.decode("latin1"), self.num_sectors)

    @property
    def status(self):
        output = "o" if self.opened_output else "."
        dos2 = "2" if self.dos_2 else "."
        mydos = "m" if self.mydos else "."
        in_use = "u" if self.in_use else "."
        deleted = "d" if self.deleted else "."
        locked = "*" if self.locked else " "
        flags = "%s%s%s%s%s%s" % (output, dos2, mydos, in_use, deleted, locked)
        return flags

    @property
    def verbose_info(self):
        flags = []
        if self.opened_output: flags.append("OUT")
        if self.dos_2: flags.append("DOS2")
        if self.mydos: flags.append("MYDOS")
        if self.in_use: flags.append("IN_USE")
        if self.deleted: flags.append("DEL")
        if self.locked: flags.append("LOCK")
        return "flags=[%s]" % ", ".join(flags)

    def parse_raw_dirent(self):
        data = self.data[0:16]
        values = data.view(dtype=self.format)[0]
        self.flag = values[0]
        self.num_sectors = int(values[1])
        self.starting_sector = int(values[2])
        self.basename = bytes(values[3]).rstrip()
        self.ext = bytes(values[4]).rstrip()

    def encode_dirent(self):
        data = np.zeros([self.format.itemsize], dtype=np.uint8)
        values = data.view(dtype=self.format)[0]
        values[0] = self.flag
        values[1] = self.num_sectors
        values[2] = self.starting_sector
        values[3] = self.basename
        values[4] = self.ext
        return data

    def get_file(self):
        media = self.filesystem.media
        offsets = np.empty(self.filesystem.max_file_size, dtype=np.uint32)
        length = 0
        next_sector = self.starting_sector
        sectors_remaining = self.num_sectors
        sectors_seen = set()

        while next_sector > 0 and sectors_remaining > 0:
            try:
                index, size = media.get_index_of_sector(next_sector)
            except errors.MediaError:
                length = 0
                self.is_sane = False
                break
            num_bytes = media[index + size - 1]
            file_num = media[index + size - 3] >> 2
            if file_num != self.file_num:
                raise errors.FileNumberMismatchError164(f"Expecting file {self.file_num}, found {file_num}")
            sectors_seen.add(next_sector)

            offsets[length:length + num_bytes] = np.arange(index, index+num_bytes)
            length += num_bytes

            next_sector = ((media[index + size - 3] & 0x3) << 8) + media[index + size - 2]
            if next_sector in sectors_seen:
                raise errors.FileStructureError(f"Bad sector pointer data: attempting to reread sector {next_sector}")
            sectors_remaining -= 1

        if length > 0:
            offsets = np.copy(offsets[0:length])
            file_segment = guess_file_type(media, self.filename, offsets)
            self.segments = [file_segment]
            return file_segment

    def update_sector_info(self, sector_list):
        self.num_sectors = sector_list.num_sectors
        self.starting_sector = sector_list.first_sector

    def add_metadata_sectors(self, vtoc, sector_list, header):
        # no extra sectors are needed for an Atari DOS file; the links to the
        # next sector is contained in the sector.
        pass

    def sanity_check(self):
        media = self.filesystem.media
        if not self.in_use:
            return True
        if not media.is_sector_valid(self.starting_sector):
            return False
        if self.num_sectors < 0 or self.num_sectors > media.num_sectors:
            return False
        return True

    def set_values(self, filename, filetype, index):
        if type(filename) is not bytes:
            filename = filename.encode("latin1")
        if b'.' in filename:
            filename, ext = filename.split(b'.', 1)
        else:
            ext = b'   '
        self.basename = b'%-8s' % filename[0:8]
        self.ext = ext
        self.file_num = index
        self.flag |= self.FLAG_DOS_2 | self.FLAG_IN_USE
        if _xd: log.debug("set_values: %s" % self)


class AtariDos2Directory(Directory):
    ui_name = "DOS2 Directory"

    def find_segment_location(self):
        media = self.media
        if media.is_sector_valid(361):
            if media.sector_size == 256:
                # uses only first 128 bytes
                offsets = media.get_sector_list_offsets(range(361,369), 128)
                return offsets, 0
            else:
                return media.get_contiguous_sectors_offsets(361, 8)
        else:
            raise errors.FilesystemError("Disk image too small to contain a directory")

    def calc_dirents(self):
        segments = []
        for filenum in range(64):
            dirent = AtariDosDirent(self, filenum)
            if dirent.in_use:
                dirent.set_comment_at(0x00, "FILE #%d: Flag" % filenum)
                dirent.set_comment_at(0x01, "FILE #%d: Number of sectors in file" % filenum)
                dirent.set_comment_at(0x03, "FILE #%d: Starting sector number" % filenum)
                dirent.set_comment_at(0x05, "FILE #%d: Filename" % filenum)
                dirent.set_comment_at(0x0d, "FILE #%d: Extension" % filenum)
                segments.append(dirent)
        return segments


class AtariDos2(Filesystem):
    ui_name = "Atari DOS 2"
    default_executable_extension = "XEX"

    def check_media(self, media):
        try:
            media.get_contiguous_sectors
        except AttributeError:
            raise errors.IncompatibleMediaError(f"{self.ui_name} needs sector access")

    def calc_boot_segment(self):
        return AtariDosBootSegment(self)

    def calc_vtoc_segment(self):
        try:
            return AtariDos2SectorVTOC(self)
        except errors.FilesystemError:
            pass
        return AtariDos1SectorVTOC(self)

    def calc_directory_segment(self):
        return AtariDos2Directory(self)
