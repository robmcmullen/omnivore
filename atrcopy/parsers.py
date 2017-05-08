from __future__ import absolute_import
from builtins import str
from builtins import object
import numpy as np

from .segments import SegmentData, DefaultSegment
from .kboot import KBootImage
from .ataridos import AtariDosDiskImage, BootDiskImage, AtariDosFile, XexContainerSegment
from .spartados import SpartaDosDiskImage
from .cartridge import AtariCartImage, get_known_carts
from .mame import MameZipImage
from .dos33 import Dos33DiskImage, ProdosDiskImage, Dos33BinFile
from .errors import *

import logging
log = logging.getLogger(__name__)


class SegmentParser(object):
    menu_name = ""
    image_type = None
    container_segment = DefaultSegment

    def __init__(self, segment_data, strict=False):
        self.image = None
        self.segments = []
        self.strict = strict
        self.segment_data = segment_data
        self.parse()

    def __getstate__(self):
        """Custom jsonpickle state save routine

        This routine culls down the list of attributes that should be
        serialized, and in some cases changes their format slightly so they
        have a better mapping to json objects. For instance, json can't handle
        dicts with integer keys, so dicts are turned into lists of lists.
        Tuples are also turned into lists because tuples don't have a direct
        representation in json, while lists have a compact representation in
        json.
        """
        state = dict()
        for key in ['segments', 'strict']:
            state[key] = getattr(self, key)
        return state

    def __setstate__(self, state):
        """Custom jsonpickle state restore routine

        The use of jsonpickle to recreate objects doesn't go through __init__,
        so there will be missing attributes when restoring old versions of the
        json. Once a version gets out in the wild and additional attributes are
        added to a segment, a default value should be applied here.
        """
        self.__dict__.update(state)

    def parse(self):
        r = self.segment_data
        self.segments.append(self.container_segment(r, 0, name=self.menu_name))
        try:
            self.image = self.get_image(r)
            self.check_image()
            self.image.parse_segments()
        except UnsupportedDiskImage:
            raise
        except AtrError as e:
            raise InvalidSegmentParser(e)
        self.segments.extend(self.image.segments)

    def get_image(self, r):
        return self.image_type(r)

    def check_image(self):
        if self.strict:
            try:
                self.image.strict_check()
            except AtrError as e:
                raise InvalidSegmentParser(e)
        else:
            self.image.relaxed_check()


class DefaultSegmentParser(SegmentParser):
    menu_name = "Raw Data"

    def parse(self):
        self.segments = [DefaultSegment(self.segment_data, 0)]


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
    container_segment = XexContainerSegment


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


class Dos33SegmentParser(SegmentParser):
    menu_name = "DOS 3.3 Disk Image"
    image_type = Dos33DiskImage


class Dos33BinSegmentParser(SegmentParser):
    menu_name = "BIN (Apple ][ executable)"
    image_type = Dos33BinFile


class ProdosSegmentParser(SegmentParser):
    menu_name = "ProDOS Disk Image"
    image_type = ProdosDiskImage


def guess_parser_for_mime(mime, r, verbose=False):
    parsers = mime_parsers[mime]
    found = None
    for parser in parsers:
        try:
            found = parser(r, True)
            break
        except InvalidSegmentParser as e:
            if verbose:
                log.info("parser isn't %s: %s" % (parser.__name__, str(e)))
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
    "application/vnd.atari8bit.cart": [
        ],
    "application/vnd.atari8bit.5200_cart": [
        ],
    "application/vnd.mame_rom": [
        MameZipParser,
        ],
    "application/vnd.apple2.dsk": [
        Dos33SegmentParser,
        ProdosSegmentParser,
        ],
    "application/vnd.apple2.bin": [
        Dos33BinSegmentParser,
        ],
    }

mime_parse_order = [
    "application/vnd.atari8bit.atr",
    "application/vnd.atari8bit.xex",
    "application/vnd.atari8bit.cart",
    "application/vnd.atari8bit.5200_cart",
    "application/vnd.mame_rom",
    "application/vnd.apple2.dsk",
    "application/vnd.apple2.bin",
    ]

pretty_mime = {
    "application/vnd.atari8bit.atr": "Atari 8-bit Disk Image",
    "application/vnd.atari8bit.xex": "Atari 8-bit Executable",
    "application/vnd.atari8bit.cart": "Atari 8-bit Cartridge",
    "application/vnd.atari8bit.5200_cart":"Atari 5200 Cartridge",
    "application/vnd.mame_rom": "MAME",
    "application/vnd.apple2.dsk": "Apple ][ Disk Image",
    "application/vnd.apple2.bin": "Apple ][ Binary",
}

grouped_carts = get_known_carts()
sizes = sorted(grouped_carts.keys())
for k in sizes:
    for c in grouped_carts[k]:
        t = c[0]
        name = c[1]
        kclass = type("AtariCartSegmentParser%d" % t, (AtariCartSegmentParser,), {'cart_type': t, 'cart_info': c, 'menu_name': "%s Cartridge" % name})
        if "5200" in name:
            key = "application/vnd.atari8bit.5200_cart"
        else:
            key = "application/vnd.atari8bit.cart"
        mime_parsers[key].append(kclass)


known_segment_parsers = [DefaultSegmentParser]
for mime in mime_parse_order:
    known_segment_parsers.extend(mime_parsers[mime])


def iter_known_segment_parsers():
    yield "application/octet-stream", "", [DefaultSegmentParser]
    for mime in mime_parse_order:
        yield mime, pretty_mime[mime], mime_parsers[mime]
