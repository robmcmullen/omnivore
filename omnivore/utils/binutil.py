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
    debug = False
    
    def __init__(self, start_addr=0, data=None, name="All", error=None):
        self.start_addr = start_addr
        if data is None:
            data = np.fromstring("", dtype=np.uint8)
        self.data = data
        self.style = np.zeros_like(self.data, dtype=np.uint8)
        if self.debug:
            self.style = np.arange(len(self), dtype=np.uint8)
        self.error = error
        self.name = name
        self.page_size = -1
        self.map_width = 40
        self._search_copy = None
    
    def __str__(self):
        return "%s (%d bytes)" % (self.name, len(self.data))
    
    def __len__(self):
        return np.alen(self.data)
    
    def __getitem__(self, index):
        return self.data[index]
    
    def __setitem__(self, index, value):
        self.data[index] = value
        self._search_copy = None
    
    def get_style_bits(self, match=False, comment=False):
        style_bits = 0
        if match:
            style_bits |= 1
        if comment:
            style_bits |= 0x80
        return style_bits
    
    def get_style_mask(self, match=False, comment=False):
        style_mask = 0xff
        if match:
            style_mask &= 0xfe
        if comment:
            style_mask &= 0x7f
        return style_mask
    
    def set_style_ranges(self, ranges, **kwargs):
        style_bits = self.get_style_bits(**kwargs)
        s = self.style
        for start, end in ranges:
            s[start:end] |= style_bits
    
    def clear_style_bits(self, **kwargs):
        style_mask = self.get_style_mask(**kwargs)
        self.style &= style_mask
    
    def label(self, index):
        return "%04x" % (index + self.start_addr)
    
    @property
    def search_copy(self):
        if self._search_copy is None:
            self._search_copy = self.data.tostring()
        return self._search_copy

class NumpyObjSegment(DefaultSegment):
    def __init__(self, metadata_start, data_start, start_addr, end_addr, data, name="", error=None):
        DefaultSegment.__init__(self, start_addr, data, name, error)
        self.metadata_start = metadata_start
        self.data_start = data_start
        self.end_addr = self.start_addr + len(self)
    
    def __str__(self):
        s = "%s %04x-%04x (%04x @ %04x)" % (self.name, self.start_addr, self.end_addr, len(self.data), self.data_start)
        if self.error:
            s += " " + self.error
        return s

class NumpySectorsSegment(DefaultSegment):
    def __init__(self, first_sector, num_sectors, count, data, **kwargs):
        DefaultSegment.__init__(self, 0, data, **kwargs)
        self.page_size = 128
        self.first_sector = first_sector
        self.num_sectors = num_sectors
    
    def __str__(self):
        if self.num_sectors > 1:
            s = "%s (sectors %d-%d)" % (self.name, self.first_sector, self.first_sector + self.num_sectors - 1)
        else:
            s = "%s (sector %d)" % (self.name, self.first_sector)
        if self.error:
            s += " " + self.error
        return s
    
    def label(self, index):
        sector, byte = divmod(index, self.page_size)
        return "s%03d:%02x" % (sector + self.first_sector, byte)

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


class NumpyAtrDiskImage(atrcopy.AtrDiskImage):
    def get_obj_segment(self, metadata_start, data_start, start_addr, end_addr, data, name=""):
        """Subclass use: override this method to create a custom segment.
        
        By default uses an ObjSegment
        """
        return NumpyObjSegment(metadata_start, data_start, start_addr, end_addr, data, name)
    
    def get_raw_sectors_segment(self, first_sector, num_sectors, count, data, **kwargs):
        """Subclass use: override this method to create a custom segment.
        
        By default uses an RawSectorsSegment
        """
        return NumpySectorsSegment(first_sector, num_sectors, count, data, **kwargs)

class ATRSegmentParser(SegmentParser):
    menu_name = "ATR Disk Image"
    
    def parse(self, bytes):
        self.segments.append(DefaultSegment(0, bytes))
        try:
            self.atr = NumpyAtrDiskImage(bytes)
        except:
            raise InvalidSegmentParser
        
        self.atr.parse_segments()
        self.segments.extend(self.atr.segments)


class NumpyAtariDosFile(atrcopy.AtariDosFile):
    def get_obj_segment(self, metadata_start, data_start, start_addr, end_addr, data, name=""):
        """Subclass use: override this method to create a custom segment.
        
        By default uses an ObjSegment
        """
        return NumpyObjSegment(metadata_start, data_start, start_addr, end_addr, data, name)

class XexSegmentParser(SegmentParser):
    menu_name = "XEX (Atari 8-bit executable)"
    
    def parse(self, bytes):
        self.segments.append(DefaultSegment(0, bytes))
        try:
            xex = NumpyAtariDosFile(bytes)
        except atrcopy.InvalidBinaryFile:
            raise InvalidSegmentParser

        self.segments.extend(xex.segments)




known_segment_parsers = [
    DefaultSegmentParser,
    ATRSegmentParser,
    XexSegmentParser,
    ]
