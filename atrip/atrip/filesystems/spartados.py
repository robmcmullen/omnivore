import numpy as np

from . import errors
from .ataridos import AtariDosDirent, AtariDosDiskImage, XexSegment
from .segments import DefaultSegment, EmptySegment, ObjSegment, RawSectorsSegment, SegmentSaver

import logging
log = logging.getLogger(__name__)


class SpartaDosDirent(AtariDosDirent):
    format = np.dtype([
        ('status', 'u1'),
        ('sector', '<u2'),
        ('len_l', '<u2'),
        ('len_h', 'i1'),
        ('filename','S8'),
        ('ext','S3'),
        ('date','S3'),
        ('time','S3'),
        ])

    def __init__(self, image, file_num=0, bytes=None, starting_sector=None):
        self.length = 0
        self.sector_map = None
        self.sector_map_index = 0
        AtariDosDirent.__init__(self, image, file_num, bytes=bytes)
        if starting_sector is not None:
            # Root directory doesn't have the starting sector in the dirent,
            # rather the boot sector so it must be specified here.
            self.starting_sector = starting_sector
            self.is_sane = self.sanity_check(image)

    def __str__(self):
        output = "o" if self.opened_output else "."
        subdir = "D" if self.is_dir else "."
        in_use = "u" if self.in_use else "."
        deleted = "d" if self.deleted else "."
        locked = "*" if self.locked else " "
        flags = "%s%s%s%s%s %03d" % (output, subdir, in_use, deleted, locked, self.starting_sector)
        return "File #%-2d (%s) %-8s%-3s  %8d  %s" % (self.file_num, flags, self.basename.decode('latin1'), self.ext.decode('latin1'), self.length, self.str_timestamp)

    @property
    def verbose_info(self):
        flags = []
        if self.opened_output: flags.append("OUT")
        if self.is_dir: flags.append("DIR")
        if self.in_use: flags.append("IN_USE")
        if self.deleted: flags.append("DEL")
        if self.locked: flags.append("LOCK")
        return "flags=[%s]" % ", ".join(flags)

    def parse_raw_dirent(self, image, data):
        if data is None:
            return
        values = data.view(dtype=self.format)[0]
        flag = values[0]
        self.flag = flag
        self.locked = (flag&0x1) > 0
        self.hidden = (flag&0x10) > 0
        self.archived = (flag&0x100) > 0
        self.in_use = (flag&0b1000) > 0
        self.deleted = (flag&0b10000) > 0
        self.is_dir = (flag&0b100000) > 0
        self.opened_output = (flag&0b10000000) > 0
        self.starting_sector = int(values[1])
        self.basename = bytes(values[4]).rstrip()
        if self.is_dir:
            self.ext = b""
        else:
            self.ext = bytes(values[5]).rstrip()
        self.length = 256*256*values[3] + values[2]
        self.date_array = tuple(data[17:20])
        self.time_array = tuple(data[20:23])
        self.is_sane = self.sanity_check(image)

    def sanity_check(self, image):
        if not self.in_use:
            return True
        if not image.header.sector_is_valid(self.starting_sector):
            return False
        return True

    @property
    def str_timestamp(self):
        str_date = "%d/%d/%d" % self.date_array
        str_time = "%d:%d:%d" % self.time_array
        return "%s %s" % (str_date, str_time)

    def start_read(self, image):
        if not self.is_sane:
            log.debug("Invalid directory entry '%s', starting_sector=%s" % (str(self), self.starting_sector))
            raise errors.InvalidDirent("Invalid directory entry '%s'" % str(self))
        self.sector_map = image.get_sector_map(self.starting_sector)
        self.sector_map_index = 0
        self.length_remaining = self.length

    def read_sector(self, image):
        sector = self.sector_map[self.sector_map_index]
        if sector == 0:
            return None, True, 0, self.length_remaining
        raw, pos, size = image.get_raw_bytes(sector)
        num_data_bytes = min(self.length_remaining, size)
        self.length_remaining -= num_data_bytes
        self.sector_map_index += 1
        return raw[0:num_data_bytes], sector == 0, pos, num_data_bytes


class SpartaDosDiskImage(AtariDosDiskImage):
    def __init__(self, *args, **kwargs):
        self.first_bitmap = 0
        self.num_bitmap = 0
        self.root_dir = 0
        self.root_dir_dirent = None
        self.fs_version = 0
        AtariDosDiskImage.__init__(self, *args, **kwargs)

    def __str__(self):
        return "%s Sparta DOS Format: %d usable sectors (%d free), %d files" % (self.header, self.total_sectors, self.unused_sectors, len(self.files))

    boot_record_type = np.dtype([
        ('unused', 'u1'),
        ('num_boot', 'u1'),
        ('boot_addr', '<u2'),
        ('init_addr', '<u2'),
        ('jmp', 'u1'),
        ('cont_addr', '<u2'),
        ('root_dir','<u2'),
        ('num_sectors','<u2'),
        ('num_free','<u2'),
        ('num_bitmap', 'u1'),
        ('bitmap','<u2'),
        ('first_free', '<u2'),
        ('first_free_dir','<u2'),
        ('vol_name','S8'),
        ('num_tracks','u1'),
        ('sector_size','u1'),
        ('fs_version','u1'),
        ])

    sector_size_map = {0: 256,
                       1: 512,
                       0x80: 128,
                       }

    def get_boot_sector_info(self):
        data, style = self.get_sectors(1)
        values = data[0:33].view(dtype=self.boot_record_type)[0]
        self.num_boot = values['num_boot']
        self.boot_addr = values['boot_addr']
        self.first_bitmap = values['bitmap']
        self.num_bitmap = values['num_bitmap']
        self.root_dir = values['root_dir']
        self.fs_version = values['fs_version']
        s = values['sector_size']
        self.sector_size = self.sector_size_map.get(values['sector_size'], -1)
        self.total_sectors = values['num_sectors']
        self.unused_sectors = values['num_free']
        num = self.header.max_sectors
        self.is_sane = self.total_sectors == num and values['first_free'] <= num and self.first_bitmap <= num and self.root_dir <= num and self.fs_version in [0x11, 0x20, 0x21] and self.sector_size != -1
        if not self.is_sane:
            raise errors.InvalidDiskImage("Invalid SpartaDos parameters in boot header")

    def get_vtoc(self):
        pass

    def get_directory(self):
        self.files = []
        dir_map = self.get_sector_map(self.root_dir)
        sector = dir_map[0]
        if sector == 0:
            return
        bytes, pos, size = self.get_raw_bytes(sector)
        d = SpartaDosDirent(self, 0, bytes[0:23], starting_sector=self.root_dir)
        s = self.get_file_segment(d)
        for filenum, i in enumerate(range(23, d.length, 23)):
            dirent = SpartaDosDirent(self, filenum + 1, s[i:i + 23])
            self.files.append(dirent)
        self.root_dir_dirent = d

    def get_boot_segments(self):
        segments = []
        num = min(self.num_boot, 1)
        s = self.get_sector_slice(1, num)
        r = self.rawdata[s]
        addr = self.boot_addr
        header = ObjSegment(r[0:43], 0, 0, addr, addr + 43, name="Boot Header")
        segments.append(header)
        if self.num_boot > 0:
            sectors = ObjSegment(r, 0, 0, addr, addr + len(r), name="Boot Sectors")
            code = ObjSegment(r[43:], 0, 0, addr + 43, addr + len(r), name="Boot Code")
            segments.extend([header, code])
        return segments

    def get_vtoc_segments(self):
        r = self.rawdata
        segments = []
        addr = 0
        start, count = self.get_contiguous_sectors(self.first_bitmap, self.num_bitmap)
        if self.sector_size == 512:
            num_boot = 1
            boot_size = 512
        else:
            num_boot = 3
            boot_size = 128
        segment = RawSectorsSegment(r[start:start+count], self.first_bitmap, self.num_bitmap, count, 0, 0, self.sector_size, name="Bitmap")
        segments.append(segment)
        return segments

    def get_sector_map(self, sector):
        m = None
        while sector > 0:
            b, _ = self.get_sectors(sector)
            sector, prev = b[0:4].view(dtype='<u2')
            if m is None:
                m = np.copy(b[4:].view(dtype='<u2'))
            else:
                m = np.hstack((m, b[4:].view(dtype='<u2')))
        return m

    def get_directory_segments(self):
        dirent = self.root_dir_dirent
        segment = self.get_file_segment(dirent)
        segment.name = dirent.filename
        segment.map_width = 23
        segments = [segment]
        return segments

    def get_file_segment(self, dirent):
        byte_order = []
        dirent.start_read(self)
        while True:
            bytes, last, pos, size = dirent.read_sector(self)
            if not last:
                byte_order.extend(list(range(pos, pos + size)))
            else:
                break
        if len(byte_order) > 0:
            name = "%s %d@%d %s" % (dirent.filename, dirent.length, dirent.starting_sector, dirent.str_timestamp)
            verbose_name = "%s (%d bytes, sector map@%d) %s %s" % (dirent.filename, dirent.length, dirent.starting_sector, dirent.verbose_info, dirent.str_timestamp)
            raw = self.rawdata.get_indexed(byte_order)
            segment = DefaultSegment(raw, name=name, verbose_name=verbose_name)
        else:
            segment = EmptySegment(self.rawdata, name=dirent.filename, error=dirent.str_timestamp)
        return segment
