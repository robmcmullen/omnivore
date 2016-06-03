import numpy as np

from segments import SegmentData, DefaultSegment
from diskimages import BootDiskImage
from kboot import KBootImage
from ataridos import AtariDosDiskImage, AtariDosFile
from spartados import SpartaDosDiskImage
from cartridge import AtariCartImage, get_known_carts
from mame import MameZipImage
from errors import *


class SegmentParser(object):
    menu_name = ""
    image_type = None
    
    def __init__(self, segment_data, strict=False):
        self.image = None
        self.segments = []
        self.strict = strict
        self.parse(segment_data)

    def parse(self, r):
        self.segments.append(DefaultSegment(r, 0))
        try:
            self.image = self.get_image(r)
            self.check_image()
            self.image.parse_segments()
        except AtrError:
            raise InvalidSegmentParser
        self.segments.extend(self.image.segments)

    def get_image(self, r):
        return self.image_type(r)

    def check_image(self):
        if self.strict:
            try:
                self.image.strict_check()
            except AtrError:
                raise InvalidSegmentParser
        else:
            self.image.relaxed_check()


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
    cart_type = 0
    cart_info = None

    def get_image(self, r):
        return self.image_type(r, self.cart_type)


class MameZipParser(SegmentParser):
    menu_name = "MAME ROM Zipfile"
    image_type = MameZipImage


def guess_parser_for_mime(mime, r):
    parsers = mime_parsers[mime]
    found = None
    for parser in parsers:
        try:
            found = parser(r, True)
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

def iter_parsers(r):
    for mime in mime_parse_order:
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
    "application/vnd.mame_rom": [
        MameZipParser,
        ],
    }

mime_parse_order = [
    "application/vnd.atari8bit.atr",
    "application/vnd.atari8bit.xex",
    "CARTS", # Will get filled in below
    "application/vnd.mame_rom",
    ]

pretty_mime = {
    "application/vnd.atari8bit.atr": "Atari 8-bit Disk Image",
    "application/vnd.atari8bit.xex": "Atari 8-bit Executable",
    "application/vnd.mame_rom": "MAME"
}

grouped_carts = get_known_carts()
sizes = sorted(grouped_carts.keys())
cart_order = []
for k in sizes:
    if k > 128:
        key = "application/vnd.atari8bit.large_cart"
        pretty = "Atari 8-bit Large Cartridge"
    else:
        key = "application/vnd.atari8bit.%dkb_cart" % k
        pretty = "Atari 8-bit %dKB Cartridge" % k
    if key not in mime_parsers:
        cart_order.append(key)
        pretty_mime[key] = pretty
        mime_parsers[key] = []
    for c in grouped_carts[k]:
        t = c[0]
        kclass = type("AtariCartSegmentParser%d" % t, (AtariCartSegmentParser,), {'cart_type': t, 'cart_info': c, 'menu_name': "%s Cartridge" % c[1]})
        mime_parsers[key].append(kclass)
i = mime_parse_order.index("CARTS")
mime_parse_order[i:i+1] = cart_order


known_segment_parsers = [DefaultSegmentParser]
for mime in mime_parse_order:
    known_segment_parsers.extend(mime_parsers[mime])

def iter_known_segment_parsers():
    yield "application/octet-stream", "", [DefaultSegmentParser]
    for mime in mime_parse_order:
        yield mime, pretty_mime[mime], mime_parsers[mime]
