import numpy as np

from segments import SegmentData, DefaultSegment
from diskimages import BootDiskImage
from kboot import KBootImage
from ataridos import AtariDosDiskImage, AtariDosFile
from spartados import SpartaDosDiskImage
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
            self.image = self.image_type(r)
            self.image.parse_segments()
        except AtrError:
            raise InvalidSegmentParser
        self.segments.extend(self.image.segments)


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


def guess_parser_for(mime, r):
    parsers = mime_parsers[mime]
    found = None
    for parser in parsers:
        try:
            found = parser(r)
            break
        except InvalidSegmentParser:
            pass
    return found


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

known_segment_parsers = [DefaultSegmentParser]
for mime in mime_parse_order:
    known_segment_parsers.extend(mime_parsers[mime])
