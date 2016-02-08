import numpy as np

from atrcopy import DefaultSegment, KBootImage, AtariDosDiskImage, AtariDosFile, InvalidBinaryFile


class InvalidSegmentParser(Exception):
    pass


class SegmentParser(object):
    name = ""
    
    def __init__(self, bytes):
        self.segments = []
        self.parse(bytes)
    
    def parse(self, bytes):
        raise NotImplementedError


class AnticFontSegment(DefaultSegment):
    def __init__(self, *args, **kwargs):
        DefaultSegment.__init__(self, *args, **kwargs)
        if np.alen(self.data) != 1024:
            raise RuntimeError("ANTIC Fonts must be 1024 bytes; have %d bytes" % (np.alen(self.data)))
    
    @property
    def antic_font(self):
        font = {
            'name': self.name,
            'char_w': 8,
            'char_h': 8,
            'np_data': self.data,
            }
        return font


class DefaultSegmentParser(SegmentParser):
    menu_name = "Raw Data"
    
    def parse(self, bytes):
        self.segments = [DefaultSegment(0, bytes)]


class KBootSegmentParser(SegmentParser):
    menu_name = "KBoot Disk Image"
    
    def parse(self, bytes):
        self.segments.append(DefaultSegment(0, bytes))
        try:
            self.atr = KBootImage(bytes)
        except:
            raise InvalidSegmentParser
        
        self.atr.parse_segments()
        self.segments.extend(self.atr.segments)


class AtariDosSegmentParser(SegmentParser):
    menu_name = "Atari DOS Disk Image"
    
    def parse(self, bytes):
        self.segments.append(DefaultSegment(0, bytes))
        try:
            self.atr = AtariDosDiskImage(bytes)
        except:
            raise InvalidSegmentParser
        
        self.atr.parse_segments()
        self.segments.extend(self.atr.segments)


class AtariBootDiskSegmentParser(SegmentParser):
    menu_name = "Atari Boot Disk Image"
    
    def parse(self, bytes):
        self.segments.append(DefaultSegment(0, bytes))
        try:
            self.atr = AtariDosDiskImage(bytes)
        except:
            raise InvalidSegmentParser
        
        self.atr.parse_segments()
        self.segments.extend(self.atr.segments)


class XexSegmentParser(SegmentParser):
    menu_name = "XEX (Atari 8-bit executable)"
    
    def parse(self, bytes):
        self.segments.append(DefaultSegment(0, bytes))
        try:
            xex = AtariDosFile(bytes)
        except InvalidBinaryFile:
            raise InvalidSegmentParser

        self.segments.extend(xex.segments)


def guess_parser_for(mime, bytes):
    parsers = mime_parsers[mime]
    found = None
    for parser in parsers:
        try:
            found = parser(bytes)
        except InvalidSegmentParser:
            pass
    return found


mime_parsers = {
    "application/vnd.atari8bit.atr": [
        KBootSegmentParser,
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
