import numpy as np

from segments import SegmentData, DefaultSegment
from diskimages import BootDiskImage
from kboot import KBootImage
from ataridos import AtariDosDiskImage, AtariDosFile
from spartados import SpartaDosDiskImage
from cartridge import AtariCartImage, get_known_carts
from errors import *


class SegmentParser(object):
    menu_name = ""
    image_type = None
    
    def __init__(self, segment_data):
        self.image = None
        self.segments = []
        self.parse(segment_data)
    
    def parse(self, r):
        self.segments.append(DefaultSegment(r, 0))
        try:
            self.image = self.get_image(r)
            self.image.parse_segments()
        except AtrError:
            raise InvalidSegmentParser
        self.segments.extend(self.image.segments)

    def get_image(self, r):
        return self.image_type(r)


class DefaultSegmentParser(SegmentParser):
    menu_name = "Raw Data"
    
    def parse(self, r):
        self.segments = [DefaultSegment(r, 0)]


class KBootSegmentParser(SegmentParser):
    menu_name = "KBoot Disk Image"
    image_type = KBootImage


class AtariDosSegmentParser(SegmentParser):
    menu_name = "Atari DOS Disk Image"
    image_type = AtariDosDiskImage


class SpartaDosSegmentParser(SegmentParser):
    menu_name = "Sparta DOS Disk Image"
    image_type = SpartaDosDiskImage


class AtariBootDiskSegmentParser(SegmentParser):
    menu_name = "Atari Boot Disk Image"
    image_type = BootDiskImage


class XexSegmentParser(SegmentParser):
    menu_name = "XEX (Atari 8-bit executable)"
    image_type = AtariDosFile


class AtariCartSegmentParser(SegmentParser):
    menu_name = "temp"
    image_type = AtariCartImage
    cart_index = 0
    cart_info = None

    def get_image(self, r):
        return self.image_type(r, self.cart_index)


def guess_parser_for_mime(mime, r):
    parsers = mime_parsers[mime]
    found = None
    for parser in parsers:
        try:
            found = parser(r)
            break
        except InvalidSegmentParser:
            pass
    return found

def guess_parser_for_system(mime_base, r):
    for mime in mime_parse_order:
        if mime.startswith(mime_base):
            p = guess_parser_for_mime(mime, r)
            if p is not None:
                return mime, p
    return None, None


mime_parsers = {
    "application/vnd.atari8bit.atr": [
        KBootSegmentParser,
        SpartaDosSegmentParser,
        AtariDosSegmentParser,
        AtariBootDiskSegmentParser,
        ],
    "application/vnd.atari8bit.xex": [
        XexSegmentParser,
        ],
    }

mime_parse_order = [
    "application/vnd.atari8bit.atr",
    "application/vnd.atari8bit.xex",
    ]

grouped_carts = get_known_carts()
sizes = sorted(grouped_carts.keys())
print sizes
for k in sizes:
    if k >= 1024:
        key = "application/vnd.atari8bit.%dmb_cart" % (k / 1024)
    else:
        key = "application/vnd.atari8bit.%dkb_cart" % k
    mime_parse_order.append(key)
    mime_parsers[key] = []
    for i, c in grouped_carts[k]:
        kclass = type("AtariCartSegmentParser%d" % i, (AtariCartSegmentParser,), {'cart_index': i, 'cart_info': c, 'menu_name': "%s Cartridge" % c[1]})
        mime_parsers[key].append(kclass)


known_segment_parsers = [DefaultSegmentParser]
for mime in mime_parse_order:
    known_segment_parsers.extend(mime_parsers[mime])
