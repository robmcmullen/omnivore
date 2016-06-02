from collections import defaultdict

import numpy as np

from errors import *
from segments import SegmentData, EmptySegment, ObjSegment
from diskimages import DiskImageBase
from utils import to_numpy

# From atari800 source
known_cart_types = [
# (note: all size units in KB)
# atari800 index number
# name
# total size
# static size
# static offset
# static address
# banked size
# banked offset (for bank zero)
# banked address
    (0, "", 0,),
    (1, "Standard 8K", 8, 8, 0, 0xa000),
    (2, "Standard 16K", 16, 16, 0, 0x8000),
    (3, "OSS 16K", 16, 4, 12, 0xb000, 4, 0, 0xa000),
    (4, "5200 32K", 32, 32, 0, 0x4000),
    (5, "DB 32K", 32,),
    (6, "5200 EE 16K", 16,),
    (7, "5200 BBSB 40K", 40,),
    (8, "WILL 64K", 64,),
    (9, "EXP_64K", 64,),
    (10, "DIAMOND_64K", 64,),
    (11, "SDX_64K", 64,),
    (12, "XEGS_32K", 32,  8, 24, 0xa000, 8, 0, 0x8000),
    (13, "XEGS_64_07K", 64,  8, 56, 0xa000, 8, 0, 0x8000),
    (14, "XEGS_128K", 128, 8, 120, 0xa000, 8, 0, 0x8000),
    (15, "OSS_M091_16K", 16,),
    (16, "5200_NS_16K", 16,),
    (17, "ATRAX_128K", 128,),
    (18, "BBSB_40K", 40,),
    (19, "5200_8K", 8, 8, 0, 0x8000),
    (20, "5200_4K", 4, 4, 0, 0x8000),
    (21, "RIGHT_8K", 8,),
    (22, "WILL_32K", 32,),
    (23, "XEGS_256K", 256, 8, 248, 0xa000, 8, 0, 0x8000),
    (24, "XEGS_512K", 512, 8, 504, 0xa000, 8, 0, 0x8000),
    (25, "XEGS_1024K", 1024, 8, 1016, 0xa000, 8, 0, 0x8000 ),
    (26, "MEGA_16K", 16,),
    (27, "MEGA_32K", 32,),
    (28, "MEGA_64K", 64,),
    (29, "MEGA_128K", 128,),
    (30, "MEGA_256K", 256,),
    (31, "MEGA_512K", 512,),
    (32, "MEGA_1024K", 1024,),
    (33, "SWXEGS_32K", 32,  8, 24, 0xa000, 8, 0, 0x8000),
    (34, "SWXEGS_64K", 64,  8, 56, 0xa000, 8, 0, 0x8000),
    (35, "SWXEGS_128K", 128, 8, 120, 0xa000, 8, 0, 0x8000),
    (36, "SWXEGS_256K", 256, 8, 248, 0xa000, 8, 0, 0x8000),
    (37, "SWXEGS_512K", 512, 8, 504, 0xa000, 8, 0, 0x8000),
    (38, "SWXEGS_1024K", 1024, 8, 1016, 0xa000, 8, 0, 0x8000 ),
    (39, "PHOENIX_8K", 8,),
    (40, "BLIZZARD_16K", 16, 16, 0, 0x8000),
    (41, "ATMAX_128K", 128,),
    (42, "ATMAX_1024K", 1024,),
    (43, "SDX_128K", 128,),
    (44, "OSS_8K", 8,),
    (45, "OSS_043M_16K", 16, 4, 12, 0xb000, 4, 0, 0xa000),
    (46, "BLIZZARD_4K", 4,),
    (47, "AST_32K", 32,),
    (48, "ATRAX_SDX_64K", 64,),
    (49, "ATRAX_SDX_128K", 128,),
    (50, "TURBOSOFT_64K", 64,),
    (51, "TURBOSOFT_128K", 128,),
    (52, "ULTRACART_32K", 32,),
    (53, "LOW_BANK_8K", 8, 8, 0, 0x8000),
    (54, "SIC_128K", 128,),
    (55, "SIC_256K", 256,),
    (56, "SIC_512K", 512,),
    (57, "Standard 2K", 2, 2, 0, 0xb800),
    (58, "Standard 4K", 4, 4, 0, 0xb000),
    (59, "Right 4K", 4, 4, 4, 0, 0x9000),
    (60, "TURBO_HIT_32K", 32,),
    (61, "MEGA_2048K", 2048,),
    (62, "THECART_128MK", 128*1024,),
    (63, "MEGA_4096K", 4096,),
    (64, "MEGA_2048K", 2048,),
    (65, "THECART_32MK", 32*1024,),
    (66, "THECART_64MK", 64*1024,),
    (67, "XEGS_64_8FK", 64),
]

def get_known_carts():
    grouped = defaultdict(list)
    for i, c in enumerate(known_cart_types[1:], 1):
        size = c[2]
        grouped[size].append((i, c))
    return grouped


class A8CartHeader(object):
    # Atari Cart format described by https://sourceforge.net/p/atari800/source/ci/master/tree/DOC/cart.txt  NOTE: Big endian!
    format = np.dtype([
        ('magic', '|S4'),
        ('format', '>u4'),
        ('checksum', '>u4'),
        ('unused','>u4')
        ])
    file_format = "Cart"
    
    def __init__(self, bytes=None, create=False):
        self.image_size = 0
        self.cart_type = -1
        self.cart_name = ""
        self.cart_size = 0
        self.crc = 0
        self.unused = 0
        self.header_offset = 0
        self.num_banks = 0
        self.banks = []
        self.bank_size = 0
        self.bank_origin = 0
        self.main_size = 0
        self.main_offset = 0
        self.main_origin = 0
        self.possible_types = set()
        if create:
            self.header_offset = 16
            self.check_size(0)
        if bytes is None:
            return
        
        if len(bytes) == 16:
            values = bytes.view(dtype=self.format)[0]
            if values[0] != 'CART':
                raise InvalidCartHeader
            self.cart_type = int(values[1])
            self.crc = int(values[2])
            self.header_offset = 16
            self.set_type(self.cart_type)
        else:
            raise InvalidCartHeader
    
    def __str__(self):
        return "%s Cartridge (atari800 type=%d size=%d, %d banks, crc=%d)" % (self.cart_name, self.cart_type, self.cart_size, self.bank_size, self.crc)
    
    def __len__(self):
        return self.header_offset
    
    def to_array(self):
        raw = np.zeros([16], dtype=np.uint8)
        values = raw.view(dtype=self.format)[0]
        values[0] = 'CART'
        values[1] = self.cart_type
        values[2] = self.crc
        values[3] = 0
        return raw

    def set_type(self, cart_type):
        print "TYPE", cart_type
        self.cart_type = cart_type
        c = known_cart_types[cart_type]
        self.cart_name = c[1]
        self.cart_size = c[2]
        if len(c) >= 6:
            self.main_size, self.main_offset, self.main_origin = c[3:6]
        if len(c) >= 9:
            self.banks = []
            self.bank_size, offset, self.bank_origin = c[6:9]
            s = self.cart_size - self.main_size
            while s > 0:
                self.banks.append(offset)
                offset += self.bank_size
                s -= self.bank_size

    def check_size(self, size):
        self.possible_types = set()
        k, r = divmod(size, 1024)
        if r == 0 or r == 16:
            for i, t in enumerate(known_cart_types):
                valid_size = t[0]
                if k == valid_size:
                    self.possible_types.add(i)


class AtariCartImage(DiskImageBase):
    def __init__(self, rawdata, cart_type, filename=""):
        self.cart_type = cart_type
        DiskImageBase.__init__(self, rawdata, filename)

    def __str__(self):
        return str(self.header)
    
    def read_header(self):
        bytes = self.bytes[0:16]
        try:
            self.header = A8CartHeader(bytes)
        except InvalidCartHeader:
            self.header = A8CartHeader()
            self.header.set_type(self.cart_type)
        if self.header.cart_type != self.cart_type:
            raise InvalidDiskImage("Cart type doesn't match type defined in header")
    
    def check_size(self):
        if self.header is None:
            return
        k, rem = divmod((len(self) - len(self.header)), 1024)
        c = known_cart_types[self.cart_type]
        print "checking %s:" % c[1], k, rem, c[2]
        if rem > 0:
            raise InvalidDiskImage("Cart not multiple of 1K")
        if k != c[2]:
            raise InvalidDiskImage("Image size %d doesn't match cart type %d size %d" % (k, self.cart_type, c[2]))
    
    def parse_segments(self):
        r = self.rawdata
        i = self.header.header_offset
        if i > 0:
            self.segments.append(ObjSegment(r[0:i], 0, 0, 0, i, name="Cart Header"))
        self.segments.extend(self.get_main_segment())
        self.segments.extend(self.get_banked_segments())

    def get_main_segment(self):
        r = self.rawdata
        start = self.header.header_offset + self.header.main_offset * 1024
        end = start + (self.header.main_size * 1024)
        s = ObjSegment(r[start:end], 0, 0, self.header.main_origin, name="Main Bank")
        return [s]

    def get_banked_segments(self):
        print "HI", self.header.banks
        segments = []
        r = self.rawdata
        for i, offset in enumerate(self.header.banks):
            start = self.header.header_offset + offset * 1024
            end = start + (self.header.bank_size * 1024)
            s = ObjSegment(r[start:end], 0, 0, self.header.bank_origin, name="Bank #%d" % (i + 1))
            segments.append(s)
        return segments


def add_cart_header(bytes):
    header = A8CartHeader(create=True)
    header.check_size(len(bytes))
    hlen = len(header)
    data = np.empty([hlen + len(bytes)], dtype=np.uint8)
    data[0:hlen] = header.to_array()
    data[hlen:] = bytes
    return data
