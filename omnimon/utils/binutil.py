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


class AtrFileSegment(DefaultSegment):
    def __init__(self, dirent, data, error=None):
        DefaultSegment.__init__(self, 0, data, error)
        self.dirent = dirent
    
    def __str__(self):
        s = str(self.dirent)
        if self.error:
            s += " " + self.error
        return s


class ATRSegmentParser(SegmentParser):
    menu_name = "ATR Disk Image"
    
    def parse(self, bytes):
        self.segments.append(DefaultSegment(0, bytes))
        try:
            self.atr = atrcopy.AtrDiskImage(bytes)
        except:
            raise InvalidSegmentParser
        
        for dirent in atr.files:
            try:
                bytes = atr.get_file(dirent)
                error = None
            except atrcopy.FileNumberMismatchError164:
                bytes = None
                error = "Error 164"
            except atrcopy.ByteNotInFile166:
                bytes = None
                error = "Invalid sector"
            a = AtrFileSegment(dirent, bytes, error)
            self.segments.append(AtrSegment(dirent))

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
