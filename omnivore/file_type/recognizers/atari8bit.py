from traits.api import HasTraits, provides

from omnivore.file_type.i_file_recognizer import IFileRecognizer
from omnivore.framework.document import Document
from omnivore.utils.segmentutil import InvalidSegmentParser, guess_parser_for, DefaultSegment, AnticFontSegment
from omnivore.tasks.map_edit.pane_layout import task_id_with_pane_layout as map_edit_task_id

@provides(IFileRecognizer)
class XEXRecognizer(HasTraits):
    name = "Atari 8-bit Executable"
    
    id = "application/vnd.atari8bit.xex"
    
    def identify(self, guess):
        parser = guess_parser_for(self.id, guess.numpy)
        if parser is not None:
            guess.parser = parser
            return self.id
    
    def load(self, guess):
        doc = Document(metadata=guess.metadata, bytes=guess.numpy)
        doc.set_segments(guess.parser)
        state = doc.bytes[0:6] == [0xff, 0xff, 0x80, 0x2a, 0xff, 0x8a]
        if state.all():
            print "Found getaway.xex!!!"
            font_segment = AnticFontSegment(0x2b00, doc.bytes[0x086:0x486], name="Playfield font")
            doc.add_user_segment(font_segment)
            segment = DefaultSegment(0x4b00, doc.bytes[0x2086:0x6086], name="Playfield map")
            segment.map_width = 256
            doc.add_user_segment(segment)
            doc.extra_metadata = {
                'font': (font_segment.antic_font, 5),
                'initial segment': segment,
                }
            doc.extra_metadata.update(getaway_defaults)
            doc.last_task_id = map_edit_task_id
        return doc


@provides(IFileRecognizer)
class ATRRecognizer(HasTraits):
    name = "Atari 8-bit Disk Image"
    
    id = "application/vnd.atari8bit.atr"
    
    def identify(self, guess):
        parser = guess_parser_for(self.id, guess.numpy)
        if parser is not None:
            guess.parser = parser
            return self.id
    
    def load(self, guess):
        doc = Document(metadata=guess.metadata, bytes=guess.numpy)
        doc.set_segments(guess.parser)
        state = doc.bytes[0x10:0x19] == [0x00, 0xc1, 0x80, 0x0f, 0xcc, 0x22, 0x18, 0x60, 0x0e]
        if state.all():
            print "Found getaway.atr!!!"
            font_segment = AnticFontSegment(0x2b00, doc.bytes[0x090:0x490], name="Playfield font")
            doc.add_user_segment(font_segment)
            segment = DefaultSegment(0x4b00, doc.bytes[0x2090:0x6090], name="Playfield map")
            segment.map_width = 256
            doc.add_user_segment(segment)
            doc.extra_metadata = {
                'font': (font_segment.antic_font, 5),
                'initial segment': segment,
                }
            doc.extra_metadata.update(getaway_defaults)
            doc.last_task_id = map_edit_task_id
        return doc

getaway_defaults = {
    'colors': [0x46, 0xD6, 0x74, 0x0C, 0x14, 0x86, 0x02, 0xB6, 0xBA],
    'tile map': [
        ("road", [0x70]),
        ("trees", range(0x80, 0x96), range(0x01, 0x16),),
        ("buildings", range(0x96, 0x9f), range(0x16, 0x1f), range(0x41, 0x51), range(0x5d, 0x60),),
        ("people", range(0xf1, 0xf4), range(0x71, 0x74)),
        ("water", range(0x2e, 0x41),),
        ("bridges", range(0x69, 0x6d),),
        ("vehicles", range(0x51, 0x59),),
        ("airport", range(0x60, 0x68), [0x5f], range(0x59, 0x5d), range(0xd9, 0xdd)), 
        ("golf", range(0xa9, 0xae),),
        ("other", [0x20, 0x25, 0x26, ]),
        ("special", range(0x21, 0x25), range(0x74, 0x76),), 
        ]
    }
