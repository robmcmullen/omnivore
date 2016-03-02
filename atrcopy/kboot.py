import numpy as np

from errors import *
from ataridos import AtariDosDirent, XexSegment
from diskimages import DiskImageBase


class KBootDirent(AtariDosDirent):
    def __init__(self, image):
        AtariDosDirent.__init__(self, image)
        self.in_use = True
        self.starting_sector = 4
        self.filename = image.filename
        if not self.filename:
            self.filename = "KBOOT"
        if self.filename == self.filename.upper():
            self.ext = "XEX"
        else:
            self.ext = "xex"
        start, size = image.header.get_pos(4)
        i = image.header.atr_header_offset + 9
        count = image.bytes[i] + 256 * image.bytes[i+1] + 256 * 256 *image.bytes[i + 2]
        if start + count > image.size or start + count < image.size - 128:
            self.is_sane = False
        else:
            self.exe_size = count
            self.exe_start = start
        self.num_sectors = count / 128 + 1
    
    def parse_raw_dirent(self, image, bytes):
        pass

    def process_raw_sector(self, image, raw):
        num_bytes = np.alen(raw)
        return raw[0:num_bytes], num_bytes


class KBootImage(DiskImageBase):
    def __str__(self):
        return "%s KBoot Format: %d byte executable" % (self.header, self.files[0].exe_size)
    
    def check_sane(self):
        if not self.all_sane:
            raise InvalidDiskImage("Doesn't seem to be KBoot header")
    
    def get_directory(self):
        dirent = KBootDirent(self)
        if not dirent.is_sane:
            self.all_sane = False
        self.files = [dirent]

    def get_file_segment(self, dirent):
        start = dirent.exe_start
        end = dirent.exe_start + dirent.exe_size
        return XexSegment(self.bytes[start:end], self.style[start:end], 0, 0, 0, start, name="KBoot Executable")
