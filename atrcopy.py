#!/usr/bin/env python

import struct
from cStringIO import StringIO

class AtrError(RuntimeError):
    pass

class InvalidAtrHeader(AtrError):
    pass

class LastDirent(AtrError):
    pass

class FileNumberMismatchError164(AtrError):
    pass

class AtrHeader(object):
    format = "<hhhBLLB"
    file_format = "ATR"
    
    def __init__(self, bytes=None):
        self.size_in_bytes = 0
        self.sector_size = 0
        self.crc = 0
        self.unused = 0
        self.flags = 0
        self.atr_header_offset = 0
        if bytes is None:
            return
        
        if len(bytes) == 16:
            values = struct.unpack(self.format, bytes)
            if values[0] != 0x296:
                raise InvalidAtrHeader
            self.size_in_bytes = (values[3] * 256 * 256 + values[1]) * 16
            self.sector_size = values[2]
            self.crc = values[4]
            self.unused = values[5]
            self.flags = values[6]
            self.atr_header_offset = 16
        else:
            raise InvalidAtrHeader
    
    def __str__(self):
        return "%s Disk Image (size=%d, sector size=%d, crc=%d flags=%d unused=%d)" % (self.file_format, self.size_in_bytes, self.sector_size, self.crc, self.flags, self.unused)

    def check_size(self, size):
        if self.size_in_bytes == 0:
            if size == 92160:
                self.size_in_bytes = size
                self.sector_size = 128
            elif size == 184320:
                self.size_in_bytes = size
                self.sector_size = 256

class XfdHeader(AtrHeader):
    file_format = "XFD"
    
    def __str__(self):
        return "%s Disk Image (size=%d, sector size=%d)" % (self.file_format, self.size_in_bytes, self.sector_size)

class AtrDirent(object):
    format = "<Bhh8s3s"

    def __init__(self, file_num=0, bytes=None):
        self.file_num = file_num
        self.flag = 0
        self.opened_output = False
        self.dos_2 = False
        self.mydos = False
        self.is_dir = False
        self.locked = False
        self.in_use = False
        self.deleted = False
        self.num_sectors = 0
        self.starting_sector = 0
        self.filename = ""
        self.ext = ""
        if bytes is None:
            return
        values = struct.unpack(self.format, bytes)
        flag = values[0]
        self.flag = flag
        self.opened_output = (flag&0x01) > 0
        self.dos_2 = (flag&0x02) > 0
        self.mydos = (flag&0x04) > 0
        self.is_dir = (flag&0x10) > 0
        self.locked = (flag&0x20) > 0
        self.in_use = (flag&0x40) > 0
        self.deleted = (flag&0x80) > 0
        self.num_sectors = values[1]
        self.starting_sector = values[2]
        self.filename = values[3].rstrip()
        self.ext = values[4].rstrip()
        self.current_sector = 0
    
    def __str__(self):
        locked = "*" if self.locked else ""
        dos = "(mydos)" if self.mydos else ""
        if self.in_use:
            return "File #%-2d: %1s%-8s%-3s  %03d %s" % (self.file_num, locked, self.filename, self.ext, self.num_sectors, dos)
        return
    
    def start_read(self):
        self.current_sector = self.starting_sector
        self.current_read = self.num_sectors
    
    def read_sector(self, disk):
        raw = disk.get_raw_bytes(self.current_sector)
        bytes = self.process_raw_sector(disk, raw)
        return (bytes, self.current_sector == 0)

    def process_raw_sector(self, disk, raw):
        file_num = ord(raw[-3]) >> 2
        if file_num != self.file_num:
            raise FileNumberMismatchError164()
        self.current_sector = ((ord(raw[-3]) & 0x3) << 8) + ord(raw[-2])
        num_bytes = ord(raw[-1])
        return raw[0:num_bytes]
    
    def get_filename(self):
        ext = ("." + self.ext) if self.ext else ""
        return self.filename + ext

class MydosDirent(AtrDirent):
    def process_raw_sector(self, disk, raw):
        self.current_read -= 1
        if self.current_read == 0:
            self.current_sector = 0
        else:
            self.current_sector += 1
            if self.current_sector == disk.first_vtoc:
                self.current_sector = disk.first_data_after_vtoc
        return raw

class AtrFile(object):
    pass

class AtrDiskImage(object):
    def __init__(self, fh):
        self.fh = fh
        self.header = None
        self.first_vtoc = 360
        self.first_data_after_vtoc = 369
        self.total_sectors = 0
        self.unused_sectors = 0
        self.files = []
        self.setup()
    
    def __str__(self):
        return "%s %d total sectors (%d free), %d files" % (self.header, self.total_sectors, self.unused_sectors, len(self.files))
    
    def dir(self):
        lines = []
        lines.append(str(self))
        for dirent in self.files:
            if dirent.in_use:
                lines.append(str(dirent))
        return "\n".join(lines)
    
    def setup(self):
        self.fh.seek(0, 2)
        self.size = self.fh.tell()
        
        self.read_atr_header()
        self.check_size()
        self.get_vtoc()
        self.get_directory()
    
    def read_atr_header(self):
        self.fh.seek(0)
        bytes = self.fh.read(16)
        try:
            self.header = AtrHeader(bytes)
        except InvalidAtrHeader:
            self.header = XfdHeader()
    
    def check_size(self):
        self.header.check_size(self.size)
        self.initial_sector_size = self.header.sector_size
        self.num_initial_sectors = 0
    
    def get_pos(self, sector):
        if sector <= self.num_initial_sectors:
            pos = self.num_initial_sectors * (sector - 1)
            size = self.initial_sector_size
        else:
            pos = self.num_initial_sectors * self.initial_sector_size + (sector - 1 - self.num_initial_sectors) * self.header.sector_size
            size = self.header.sector_size
        pos += self.header.atr_header_offset
        return pos, size
    
    def get_raw_bytes(self, sector):
        pos, size = self.get_pos(sector)
        self.fh.seek(pos)
        raw = self.fh.read(size)
        return raw
    
    def get_sectors(self, start, end=None):
        """ Get contiguous sectors
        
        :param start: first sector number to read (note: numbering starts from 1)
        :param end: last sector number to read
        :returns: bytes
        """
        output = StringIO()
        pos, size = self.get_pos(start)
        self.fh.seek(pos)
        if end is None:
            end = start
        while start <= end:
            bytes = self.fh.read(size)
            output.write(bytes)
            start += 1
            pos, size = self.get_pos(start)
        return output.getvalue()
    
    def get_vtoc(self):
        bytes = self.get_sectors(360)
        values = struct.unpack("<BHH", bytes[0:5])
        code = values[0]
        if code == 0 or code == 2:
            num = 1
        else:
            num = (code * 2) - 3
        self.first_vtoc = 360 - num + 1
        self.total_sectors = values[1]
        self.unused_sectors = values[2]
    
    def get_directory(self):
        dir_bytes = self.get_sectors(361, 368)
        i = 0
        num = 0
        files = []
        while i < len(dir_bytes):
            dirent = AtrDirent(num, dir_bytes[i:i+16])
            if dirent.mydos:
                dirent = MydosDirent(num, dir_bytes[i:i+16])
            
            if dirent.in_use:
                files.append(dirent)
            elif dirent.flag == 0:
                break
            i += 16
            num += 1
        self.files = files
    
    def get_file(self, dirent):
        output = StringIO()
        dirent.start_read()
        while True:
            bytes, last = dirent.read_sector(self)
            output.write(bytes)
            if last:
                break
        return output.getvalue()
    
    def find_file(self, filename):
        for dirent in self.files:
            if filename == dirent.get_filename():
                bytes = self.get_file(dirent)
                return bytes
        return ""

def process(dirent, options):
    skip = False
    action = "copying to"
    filename = dirent.get_filename()
    outfilename = filename
    if options.no_sys:
        if dirent.ext == "SYS":
            skip = True
            action = "skipping system file"
    if not skip:
        if options.xex:
            outfilename = "%s%s.XEX" % (dirent.filename, dirent.ext)
    if options.lower:
        outfilename = outfilename.lower()
    
    if options.dry_run:
        action = "DRY_RUN: %s" % action
        skip = True
    if not skip:
        bytes = atr.get_file(dirent)
        with open(outfilename, "wb") as fh:
            fh.write(bytes)
    if options.extract:
        print "%s: %s %s" % (dirent, action, outfilename)
    else:
        print dirent

if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="Extract images off ATR format disks")
    parser.add_argument("-v", "--verbose", default=0, action="count")
    parser.add_argument("-l", "--lower", action="store_true", default=False, help="convert filenames to lower case")
    parser.add_argument("--dry-run", action="store_true", default=False, help="don't extract, just show what would have been extracted")
    parser.add_argument("-n", "--no-sys", action="store_true", default=False, help="only extract things that look like games (no DOS or .SYS files)")
    parser.add_argument("-x", "--extract", action="store_true", default=False, help="extract files")
    parser.add_argument("--xex", action="store_true", default=False, help="add .xex extension")
    parser.add_argument("files", metavar="ATR", nargs="+", help="an ATR image file [or a list of them]")
    options, extra_args = parser.parse_known_args()

    for filename in options.files:
        with open(filename, "rb") as fh:
            atr = AtrDiskImage(fh)
            print "%s: %s" % (filename, atr)
            for dirent in atr.files:
                try:
                    process(dirent, options)
                except FileNumberMismatchError164:
                    print "Error 164: %s" % str(dirent)

