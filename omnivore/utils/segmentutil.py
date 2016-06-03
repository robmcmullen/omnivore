import numpy as np

from atrcopy import SegmentData, SegmentParser, InvalidSegmentParser, DefaultSegment, iter_known_segment_parsers


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
