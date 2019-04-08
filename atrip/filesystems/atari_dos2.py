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
    boot_record_type = np.dtype([
        ('BFLAG', 'u1'),
        ('BRCNT', 'u1'),
        ('BLDADR', '<u2'),
        ('BWTARR', '<u2'),
        ])

    def __init__(self, filesystem):
        media = filesystem.media
        size = self.find_segment_size(media)
        Segment.__init__(self, media, 0, self.bldadr, name="Boot Sectors", length=size)
        self.segments = self.calc_boot_segments()

    def find_segment_size(self, media):
        try:
            self.first_sector = media.get_contiguous_sectors(1)
            self.values = media[0:6].view(dtype=self.boot_record_type)[0]
            self.bflag = self.values['BFLAG']
            if self.bflag == 0:
                # possible boot sector
                self.brcnt = self.values['BRCNT']
                if self.brcnt == 0:
                    self.brcnt = 3
            else:
                self.brcnt = 3
            self.bldadr = self.values['BLDADR']
            index, _ = media.get_index_of_sector(1 + self.brcnt)
        except errors.MediaError as e:
            raise errors.IncompatibleMediaError(f"Invalid boot sector: {e}")
        return index

    def calc_boot_segments(self):
        header = Segment(self, 0, self.bldadr, "Boot Header", length=6)
        code = Segment(self, 6, self.bldadr + 6, name="Boot Code", length=len(self) - 6)
        return [header, code]


class AtariDos1SectorVTOC(VTOC):
    vtoc_type = np.dtype([
        ('code', 'u1'),
        ('total','<u2'),
        ('unused','<u2'),
        ])

    max_sector = 720

    def find_segment_location(self):
        media = self.media
        values = media[0:5].view(dtype=self.vtoc_type)[0]
        code = values[0]
        if code == 0 or code == 2:
            pass
        else:
            raise errors.FilesystemError(f"Invalid VTOC code {code}")
        if not media.is_sector_valid(360):
            raise errors.FilesystemError(f"Media ends before sector 360")
        self.total_sectors = values[1]
        if self.total_sectors > self.max_sector:
            raise errors.FilesystemError(f"Invalid number of sectors {self.total_sectors}")
        self.unused_sectors = values[2]
        return media.get_contiguous_sectors_offsets(360, 1)

    def unpack_vtoc(self):
        bits = np.unpackbits(self[0x0a:0x64])
        self.sector_map[0:720] = bits
        if _xd: log.debug("vtoc before:\n%s" % str(self))

    def pack_vtoc(self):
        if _xd: log.debug("vtoc after:\n%s" % str(self))
        packed = np.packbits(self.sector_map[0:720])
        self[0x0a:0x64] = packed


class AtariDos2SectorVTOC(AtariDos1SectorVTOC):
    vtoc_type = np.dtype([
        ('code', 'u1'),
        ('total','<u2'),
        ('unused','<u2'),
        ])

    max_sector = 1024

    def find_segment_location(self):
        if self.media.num_sectors < 1024:
            raise errors.FilesystemError(f"Not enhanced density disk")
        AtariDos1SectorVTOC.find_segment_location(self)  # throw away its return value
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
    # ATR Dirent structure described at http://atari.kensclassics.org/dos.htm
    format = np.dtype([
        ('FLAG', 'u1'),
        ('COUNT', '<u2'),
        ('START', '<u2'),
        ('NAME','S8'),
        ('EXT','S3'),
        ])

    def __init__(self, filesystem, parent, file_num, start):
        self.file_num = file_num
        Dirent.__init__(self, filesystem, parent, file_num, start, 16)
        self.flag = 0
        self.opened_output = False
        self.dos_2 = False
        self.mydos = False
        self.is_dir = False
        self.locked = False
        self._in_use = False
        self.deleted = False
        self.num_sectors = 0
        self.starting_sector = 0
        self.basename = b''
        self.ext = b''
        self.is_sane = True
        self.parse_raw_dirent()
        if self.in_use:
            try:
                self.get_file()
            except errors.FileError as e:
                self.is_sane = False
                self.error = e

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self.filename == other.filename and self.starting_sector == other.starting_sector and self.num_sectors == other.num_sectors

    @property
    def in_use(self):
        return self._in_use

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
        in_use = "u" if self._in_use else "."
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
        if self._in_use: flags.append("IN_USE")
        if self.deleted: flags.append("DEL")
        if self.locked: flags.append("LOCK")
        return "flags=[%s]" % ", ".join(flags)

    def extra_metadata(self, image):
        return self.verbose_info

    def parse_raw_dirent(self):
        data = self.data[0:16]
        values = data.view(dtype=self.format)[0]
        flag = values[0]
        self.flag = flag
        self.opened_output = (flag&0x01) > 0
        self.dos_2 = (flag&0x02) > 0
        self.mydos = (flag&0x04) > 0
        self.is_dir = (flag&0x10) > 0
        self.locked = (flag&0x20) > 0
        self._in_use = (flag&0x40) > 0
        self.deleted = (flag&0x80) > 0
        self.num_sectors = int(values[1])
        self.starting_sector = int(values[2])
        self.basename = bytes(values[3]).rstrip()
        self.ext = bytes(values[4]).rstrip()
        self.is_sane = self.sanity_check()

    def encode_dirent(self):
        data = np.zeros([self.format.itemsize], dtype=np.uint8)
        values = data.view(dtype=self.format)[0]
        flag = (1 * int(self.opened_output)) | (2 * int(self.dos_2)) | (4 * int(self.mydos)) | (0x10 * int(self.is_dir)) | (0x20 * int(self.locked)) | (0x40 * int(self._in_use)) | (0x80 * int(self.deleted))
        values[0] = flag
        values[1] = self.num_sectors
        values[2] = self.starting_sector
        values[3] = self.basename
        values[4] = self.ext
        return data

    def mark_deleted(self):
        self.deleted = True
        self._in_use = False

    def get_file(self):
        media = self.filesystem.media
        offsets = np.empty(self.filesystem.max_file_size, dtype=np.uint32)
        length = 0
        next_sector = self.starting_sector
        sectors_remaining = self.num_sectors
        sectors_seen = set()

        while next_sector > 0 and sectors_remaining > 0:
            index, size = media.get_index_of_sector(next_sector)
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
        if not self._in_use:
            return True
        if not media.is_sector_valid(self.starting_sector):
            return False
        if self.num_sectors < 0 or self.num_sectors > media.num_sectors:
            return False
        return True

    def get_sectors_in_vtoc(self, image):
        sector_list = BaseSectorList(image.header)
        self.start_read(image)
        while True:
            sector = WriteableSector(image.header.sector_size, None, self.current_sector)
            sector_list.append(sector)
            _, last, _, _ = self.read_sector(image)
            if last:
                break
        return sector_list

    def start_read(self, image):
        if not self.is_sane:
            raise errors.InvalidDirent("Invalid directory entry '%s'" % str(self))
        self.current_sector = self.starting_sector
        self.current_read = self.num_sectors
        self.sectors_seen = set()

    def read_sector(self, image):
        raw, pos, size = image.get_raw_bytes(self.current_sector)
        bytes, num_data_bytes = self.process_raw_sector(image, raw)
        return bytes, self.current_sector == 0, pos, num_data_bytes

    def process_raw_sector(self, image, raw):
        file_num = raw[-3] >> 2
        if file_num != self.file_num:
            raise errors.FileNumberMismatchError164("Expecting file %d, found %d" % (self.file_num, file_num))
        self.sectors_seen.add(self.current_sector)
        next_sector = ((raw[-3] & 0x3) << 8) + raw[-2]
        if next_sector in self.sectors_seen:
            raise errors.FileStructureError("Bad sector pointer data: attempting to reread sector %d" % next_sector)
        self.current_sector = next_sector
        num_bytes = raw[-1]
        return raw[0:num_bytes], num_bytes

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
        self.dos_2 = True
        self._in_use = True
        if _xd: log.debug("set_values: %s" % self)


class AtariDos2Directory(Directory):
    def __init__(self, filesystem):
        self.filesystem = filesystem
        offset, length = self.find_segment_location()
        Segment.__init__(self, filesystem.media, offset, name="Directory", length=length)

        # Each segment is a dirent
        self.segments = self.calc_dirents()

    def find_segment_location(self):
        media = self.media
        if media.is_sector_valid(361):
            return media.get_contiguous_sectors_offsets(361, 8)
        else:
            raise errors.FilesystemError("Disk image too small to contain a directory")

    def calc_dirents(self):
        segments = []
        index = 0
        for filenum in range(64):
            dirent = AtariDosDirent(self.filesystem, self, filenum, index)
            if dirent.in_use:
                dirent.set_comment_at(0x00, "FILE #%d: Flag" % filenum)
                dirent.set_comment_at(0x01, "FILE #%d: Number of sectors in file" % filenum)
                dirent.set_comment_at(0x03, "FILE #%d: Starting sector number" % filenum)
                dirent.set_comment_at(0x05, "FILE #%d: Filename" % filenum)
                dirent.set_comment_at(0x0d, "FILE #%d: Extension" % filenum)
                segments.append(dirent)
            index += 16
        return segments


class AtariDos2(Filesystem):
    default_executable_extension = "XEX"

    def check_media(self, media):
        try:
            media.get_contiguous_sectors
        except AttributeError:
            raise errors.IncompatibleMediaError("Atari DOS needs sector access")

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
