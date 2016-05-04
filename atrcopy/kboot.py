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
        raw = self.rawdata[start:end]
        return XexSegment(raw, 0, 0, start, end, name="KBoot Executable")

kboot_header = '\x96\x020\x13\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x03\x00\x07\x14\x07L\x14\x07\xff\x97\x00\x00\xa9F\x8d\xc6\x02\xd0\xfe\xa0\x00\xa9k\x91X \xd9\x07\xb0\xee \xc4\x07\xadz\x08\rv\x08\xd0\xe3\xa5\x80\x8d\xe0\x02\xa5\x81\x8d\xe1\x02\xa9\x00\x8d\xe2\x02\x8d\xe3\x02 \xeb\x07\xb0\xcc\xa0\x00\x91\x80\xa5\x80\xc5\x82\xd0\x06\xa5\x81\xc5\x83\xf0\x08\xe6\x80\xd0\x02\xe6\x81\xd0\xe3\xadv\x08\xd0\xaf\xad\xe2\x02\x8dp\x07\r\xe3\x02\xf0\x0e\xad\xe3\x02\x8dq\x07 \xff\xff\xadz\x08\xd0\x13\xa9\x00\x8d\xe2\x02\x8d\xe3\x02 \xae\x07\xadz\x08\xd0\x03L<\x07\xa9\x00\x85\x80\x85\x81\x85\x82\x85\x83\xad\xe0\x02\x85\n\x85\x0c\xad\xe1\x02\x85\x0b\x85\r\xa9\x01\x85\t\xa9\x00\x8dD\x02l\xe0\x02 \xeb\x07\x85\x80 \xeb\x07\x85\x81\xa5\x80\xc9\xff\xd0\x10\xa5\x81\xc9\xff\xd0\n \xeb\x07\x85\x80 \xeb\x07\x85\x81 \xeb\x07\x85\x82 \xeb\x07\x85\x83` \xeb\x07\xc9\xff\xd0\t \xeb\x07\xc9\xff\xd0\x02\x18`8`\xad\t\x07\r\n\x07\r\x0b\x07\xf0y\xacy\x08\x10P\xeew\x08\xd0\x03\xeex\x08\xa91\x8d\x00\x03\xa9\x01\x8d\x01\x03\xa9R\x8d\x02\x03\xa9@\x8d\x03\x03\xa9\x80\x8d\x04\x03\xa9\x08\x8d\x05\x03\xa9\x1f\x8d\x06\x03\xa9\x80\x8d\x08\x03\xa9\x00\x8d\t\x03\xadw\x08\x8d\n\x03\xadx\x08\x8d\x0b\x03 Y\xe4\xad\x03\x03\xc9\x02\xb0"\xa0\x00\x8cy\x08\xb9\x80\x08\xaa\xad\t\x07\xd0\x0b\xad\n\x07\xd0\x03\xce\x0b\x07\xce\n\x07\xce\t\x07\xeey\x08\x8a\x18`\xa0\x01\x8cv\x088`\xa0\x01\x8cz\x088`\x00\x03\x00\x80\x00\x00\x00\x00\x00\x00'

def add_kboot_header(bytes):
    sec_size = 128
    size = len(bytes)
    num_sectors = (size + sec_size - 1) / sec_size
    padded_size = num_sectors * sec_size
    if size < padded_size:
        bytes = np.append(bytes, np.zeros([padded_size - size], dtype=np.uint8))
    paragraphs = padded_size / 16
    print size, num_sectors, paragraphs
    header = np.fromstring(kboot_header, dtype=np.uint8)
    image = np.append(header, bytes)
    print image
    words = image.view(dtype='<u2')
    print words
    words[1] = paragraphs
    print words
    words = image[16 + 9:16 + 9 + 2].view('<u2')
    words[0] = size
    return image
