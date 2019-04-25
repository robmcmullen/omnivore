import numpy as np

from .. import errors
from ..media_type import CartImage

import logging
log = logging.getLogger(__name__)


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
    (0,  "", 0,),
    (57, "Standard 2 KB", 2, 2, 0, 0xb800),
    (58, "Standard 4 KB", 4, 4, 0, 0xb000),
    (59, "Right slot 4 KB", 4, 4, 0, 0, 0x9000),
    (1,  "Standard 8 KB", 8, 8, 0, 0xa000),
    (21, "Right slot 8 KB", 8,),
    (2,  "Standard 16 KB", 16, 16, 0, 0x8000),
    (44, "OSS 8 KB", 8,),
    (15, "OSS one chip 16 KB", 16,),
    (3,  "OSS two chip (034M) 16 KB", 16, 4, 12, 0xb000, 4, 0, 0xa000),
    (45, "OSS two chip (043M) 16 KB", 16, 4, 12, 0xb000, 4, 0, 0xa000),
    (12, "XEGS 32 KB", 32,  8, 24, 0xa000, 8, 0, 0x8000),
    (13, "XEGS (banks 0-7) 64 KB", 64, 8, 56, 0xa000, 8, 0, 0x8000),
    (67, "XEGS (banks 8-15) 64 KB", 64, 8, 56, 0xa000, 8, 0, 0x8000),
    (14, "XEGS 128 KB", 128, 8, 120, 0xa000, 8, 0, 0x8000),
    (23, "XEGS 256 KB", 256, 8, 248, 0xa000, 8, 0, 0x8000),
    (24, "XEGS 512 KB", 512, 8, 504, 0xa000, 8, 0, 0x8000),
    (25, "XEGS 1 MB", 1024, 8, 1016, 0xa000, 8, 0, 0x8000 ),
    (33, "Switchable XEGS 32 KB", 32,  8, 24, 0xa000, 8, 0, 0x8000),
    (34, "Switchable XEGS 64 KB", 64,  8, 56, 0xa000, 8, 0, 0x8000),
    (35, "Switchable XEGS 128 KB", 128, 8, 120, 0xa000, 8, 0, 0x8000),
    (36, "Switchable XEGS 256 KB", 256, 8, 248, 0xa000, 8, 0, 0x8000),
    (37, "Switchable XEGS 512 KB", 512, 8, 504, 0xa000, 8, 0, 0x8000),
    (38, "Switchable XEGS 1 MB", 1024, 8, 1016, 0xa000, 8, 0, 0x8000 ),
    (22, "Williams 32 KB", 32,),
    (8,  "Williams 64 KB", 64,),
    (9,  "Express 64 KB", 64,),
    (10, "Diamond 64 KB", 64,),
    (11, "SpartaDOS X 64 KB", 64,),
    (43, "SpartaDOS X 128 KB", 128,),
    (17, "Atrax 128 KB", 128,),
    (18, "Bounty Bob 40 KB", 40,),
    (26, "MegaCart 16 KB", 16,),
    (27, "MegaCart 32 KB", 32,),
    (28, "MegaCart 64 KB", 64,),
    (29, "MegaCart 128 KB", 128,),
    (30, "MegaCart 256 KB", 256,),
    (31, "MegaCart 512 KB", 512,),
    (32, "MegaCart 1 MB", 1024,),
    (39, "Phoenix 8 KB", 8,),
    (46, "Blizzard 4 KB", 4,),
    (40, "Blizzard 16 KB", 16, 16, 0, 0x8000),
    (60, "Blizzard 32 KB", 32,),
    (41, "Atarimax 128 KB Flash", 128,),
    (42, "Atarimax 1 MB Flash", 1024,),
    (47, "AST 32 KB", 32,),
    (48, "Atrax SDX 64 KB", 64,),
    (49, "Atrax SDX 128 KB", 128,),
    (50, "Turbosoft 64 KB", 64,),
    (51, "Turbosoft 128 KB", 128,),
    (52, "Ultracart 32 KB", 32,),
    (53, "Low bank 8 KB", 8, 8, 0, 0x8000),
    (5,  "DB 32 KB", 32,),
    (54, "SIC! 128 KB", 128,),
    (55, "SIC! 256 KB", 256,),
    (56, "SIC! 512 KB", 512,),
    (61, "MegaMax 2 MB", 2048,),
    (62, "The!Cart 128 MB", 128*1024,),
    (63, "Flash MegaCart 4 MB", 4096,),
    (64, "MegaCart 2 MB", 2048,),
    (65, "The!Cart 32 MB", 32*1024,),
    (66, "The!Cart 64 MB", 64*1024,),
    (20, "Standard 4 KB 5200", 4, 4, 0, 0x8000),
    (19, "Standard 8 KB 5200", 8, 8, 0, 0x8000),
    (4,  "Standard 32 KB 5200", 32, 32, 0, 0x4000),
    (16, "One chip 16 KB 5200", 16,),
    (6,  "Two chip 16 KB 5200", 16,),
    (7,  "Bounty Bob 40 KB 5200", 40,),
]

known_cart_type_map = {c[0]:i for i, c in enumerate(known_cart_types)}


def get_known_carts():
    grouped = defaultdict(list)
    for c in known_cart_types[1:]:
        size = c[2]
        grouped[size].append(c)
    return grouped


def get_cart(cart_type):
    try:
        return known_cart_types[known_cart_type_map[cart_type]]
    except KeyError:
        raise errors.InvalidHeader("Unsupported cart type %d" % cart_type)


class A8CartHeader:
    # Atari Cart format described by https://sourceforge.net/p/atari800/source/ci/master/tree/DOC/cart.txt  NOTE: Big endian!
    format = np.dtype([
        ('magic', '|S4'),
        ('format', '>u4'),
        ('checksum', '>u4'),
        ('unused','>u4')
        ])

    def __init__(self, data):
        if len(data) == 16:
            header = data.view(dtype=self.format)[0]
            if header[0] != b'CART':
                raise errors.InvalidHeader("No Atari 8-bit cart header")
            self.cart_type = int(header[1])
            self.crc = int(header[2])
            self.set_type(self.cart_type)
        else:
            raise errors.InvalidHeader(f"Short cart header: should be 16 bytes; found {len(data)}")

    def __str__(self):
        return "%s Cartridge (atari800 type=%d size=%d, %d banks, crc=%d)" % (self.cart_name, self.cart_type, self.cart_size, self.bank_size, self.crc)

    def set_type(self, cart_type):
        self.cart_type = cart_type
        c = get_cart(cart_type)
        self.cart_name = c[1]
        self.cart_size = c[2]
        self.main_size = self.cart_size
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

    def check_media(self, media):
        media_size = len(media) - 16
        if self.cart_size != media_size:
            raise errors.InvalidHeader("Invalid cart size: {media_size}, expected {self.cart_size} for {self.cart_name}")


class Atari8bitCart(CartImage):
    ui_name = "Atari 8bit Cart"

    def calc_header(self, container):
        header_data = container[0:16]
        try:
            if len(header_data) == 16:
                header = A8CartHeader(header_data)
                header_length = 16
                header.check_media(container)
            else:
                header = None
        except errors.InvalidHeader:
            header = None
        return header
