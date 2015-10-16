import numpy as np

import atrcopy


class InvalidSegmentParser(Exception):
    pass


class SegmentParser(object):
    name = ""
    
    def __init__(self, bytes):
        self.segments = []
        self.parse(bytes)
    
    def parse(self, bytes):
        raise NotImplementedError


class DefaultSegment(object):
    def __init__(self, start_addr=0, data=None, error=None):
        self.start_addr = start_addr
        if data is None:
            data = np.fromstring("", dtype=np.uint8)
        self.data = data
        self.error = error
    
    def __str__(self):
        return "All (%d bytes)" % len(self.data)
    
    def __len__(self):
        return np.alen(self.data)
    
    def __getitem__(self, val):
        return self.data[val]


class DefaultSegmentParser(SegmentParser):
    menu_name = "Raw Data"
    
    def parse(self, bytes):
        self.segments = [DefaultSegment(0, bytes)]


class ATRSegmentParser(SegmentParser):
    menu_name = "ATR Disk Image"
    
    def parse(self, bytes):
        self.segments.append(DefaultSegment(0, bytes))
        try:
            self.atr = atrcopy.AtrDiskImage(bytes)
        except:
            raise InvalidSegmentParser
        
        self.atr.parse_segments()
        self.segments.extend(self.atr.segments)


class XexSegmentParser(SegmentParser):
    menu_name = "XEX (Atari 8-bit executable)"
    
    def parse(self, bytes):
        self.segments.append(DefaultSegment(0, bytes))
        try:
            xex = atrcopy.AtariDosFile(bytes)
            print xex
        except atrcopy.InvalidBinaryFile:
            raise InvalidSegmentParser

        self.segments.extend(xex.segments)




known_segment_parsers = [
    DefaultSegmentParser,
    ATRSegmentParser,
    XexSegmentParser,
    ]
