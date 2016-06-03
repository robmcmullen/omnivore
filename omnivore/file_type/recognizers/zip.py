import zipfile

import numpy as np

from traits.api import HasTraits, provides

from omnivore.file_type.i_file_recognizer import IFileRecognizer
from omnivore.framework.document import Document
from omnivore.utils.segmentutil import SegmentParser, InvalidSegmentParser

from atrcopy import SegmentData, DefaultSegment, ObjSegment

@provides(IFileRecognizer)
class ZipRecognizer(HasTraits):
    name = "Zip File Container"
    
    id = "application/vnd.mame.zip"
    
    def identify(self, guess):
        fh = guess.get_stream()
        if zipfile.is_zipfile(fh):
            with zipfile.ZipFile(fh) as zf:
                for item in zf.infolist():
                    _, r = divmod(item.file_size, 256)
                    if r > 0:
                        break
                else:
                    # else clause on for: executed if makes it through without
                    # hitting the break statement
                    return self.id
    
    def load(self, guess):
        fh = guess.get_stream()
        roms = []
        segment_info = []
        offset = 0
        with zipfile.ZipFile(fh) as zf:
            for item in zf.infolist():
                rom = np.fromstring(zf.open(item).read(), dtype=np.uint8)
                roms.append(rom)
                segment_info.append((offset, item.file_size, item.filename, item.CRC))
                offset += item.file_size
        bytes = np.concatenate(roms)
        print bytes
        print "found size", np.alen(bytes)
        doc = Document(metadata=guess.metadata, bytes=bytes)
        doc.zip_segment_info = segment_info
        doc.set_segments(MameZipParser(doc))
        return doc

class MameZipParser(SegmentParser):
    def parse(self, doc):
        r = SegmentData(doc.bytes, doc.style)
        self.segments.append(DefaultSegment(r, 0))
        for offset, size, name, crc in doc.zip_segment_info:
            end = offset + size
            self.segments.append(ObjSegment(r[offset:end], 0, offset, offset, end, name=name))
    
