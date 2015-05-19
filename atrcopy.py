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
        return "size=%d, sector size=%d, crc=%d flags=%d unused=%d" % (self.size_in_bytes, self.sector_size, self.crc, self.flags, self.unused)

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
    
    def __str__(self):
        locked = "*" if self.locked else ""
        dos = "(mydos)" if self.mydos else ""
        if self.in_use:
            return "File #%-2d: %1s%-8s%-3s  %03d %s" % (self.file_num, locked, self.filename, self.ext, self.num_sectors, dos)
        return
    
    def process_raw_sector(self, bytes):
        file_num = ord(bytes[-3]) >> 2
        if file_num != self.file_num:
            raise FileNumberMismatchError164()
        sector = ((ord(bytes[-3]) & 0x3) << 8) + ord(bytes[-2])
        num_bytes = ord(bytes[-1])
        return sector, bytes[0:num_bytes]
    
    def get_filename(self):
        ext = ("." + self.ext) if self.ext else ""
        return self.filename + ext

class AtrFile(object):
    pass

class AtrDiskImage(object):
    def __init__(self, fh):
        self.fh = fh
        self.header = None
        self.files = []
        self.setup()
    
    def __str__(self):
        lines = []
        lines.append("ATR Disk Image (%s) %d files" % (self.header, len(self.files)))
        for dirent in self.files:
            if dirent.in_use:
                lines.append(str(dirent))
        return "\n".join(lines)
    
    def setup(self):
        self.fh.seek(0, 2)
        self.size = self.fh.tell()
        
        self.read_atr_header()
        self.check_size()
        self.get_directory()
    
    def read_atr_header(self):
        self.fh.seek(0)
        bytes = self.fh.read(16)
        try:
            self.header = AtrHeader(bytes)
        except InvalidAtrHeader:
            self.header = AtrHeader()
    
    def check_size(self):
        if self.header.size_in_bytes == 0:
            if self.size == 92160:
                self.header.size_in_bytes = self.size
                self.header.sector_size = 128
            elif self.size == 184320:
                self.header.size_in_bytes = self.size
                self.header.sector_size = 256
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
    
    def get_sectors(self, start, end):
        """ Get contiguous sectors
        
        :param start: first sector number to read (note: numbering starts from 1)
        :param end: last sector number to read
        :returns: bytes
        """
        output = StringIO()
        pos, size = self.get_pos(start)
        self.fh.seek(pos)
        while start <= end:
            bytes = self.fh.read(size)
            output.write(bytes)
            start += 1
            pos, size = self.get_pos(start)
        return output.getvalue()
    
    def get_directory(self):
        dir_bytes = self.get_sectors(361, 368)
        i = 0
        num = 0
        files = []
        while i < len(dir_bytes):
            dirent = AtrDirent(num, dir_bytes[i:i+16])
            if dirent.in_use:
                files.append(dirent)
            elif dirent.flag == 0:
                break
            i += 16
            num += 1
        self.files = files
    
    def get_file(self, dirent):
        output = StringIO()
        sector = dirent.starting_sector
        while sector > 0:
            pos, size = self.get_pos(sector)
            self.fh.seek(pos)
            raw = self.fh.read(size)
            sector, bytes = dirent.process_raw_sector(raw)
            output.write(bytes)
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
    parser.add_argument("-l", "--lower", action="store_true", default=False, help="Convert filenames to lower case")
    parser.add_argument("--dry-run", action="store_true", default=False, help="Don't extract, just show what would have been extracted")
    parser.add_argument("-n", "--no-sys", action="store_true", default=False, help="Only extract things that look like games (no DOS or .SYS files)")
    parser.add_argument("-x", "--extract", action="store_true", default=False, help="Extract files")
    parser.add_argument("--xex", action="store_true", default=False, help="Add .xex extension")
    options, extra_args = parser.parse_known_args()

    for args in extra_args:
        print args
        with open(args, "rb") as fh:
            atr = AtrDiskImage(fh)
            for dirent in atr.files:
                try:
                    process(dirent, options)
                except FileNumberMismatchError164:
                    print "Error 164: %s" % str(dirent)

