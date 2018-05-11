import numpy as np

# Enthought library imports.
from traits.api import Trait, Any, List, Event, Dict, Property, Bool, Int

from omnivore8bit.document import SegmentedDocument

from atrcopy import SegmentData, DefaultSegment, DefaultSegmentParser, InvalidSegmentParser, SegmentParser

import logging
log = logging.getLogger(__name__)


class EmulatorSegmentParser(SegmentParser):
    menu_name = "Atari 800 Save State"
    def parse(self):
        r = self.segment_data
        self.segments.append(self.container_segment(r, 0, name=self.menu_name))
        for start, end, offset, name in self.emulator_segments:
            if end - start > 0:
                self.segments.append(DefaultSegment(r[start:end], offset, name))

def segment_parser_factory(emulator_segments):
    cls = type('EmulatorSegmentParser', (EmulatorSegmentParser, SegmentParser), dict(emulator_segments = emulator_segments))
    return cls


class EmulationDocument(SegmentedDocument):
    source_document = Any(None)

    emulator_type = Any(None)

    emulator = Any(None)

    skip_frames_on_boot = Int(0)

    ##### trait default values

    def _emulator_type_changed(self, value):
        print("VALUE", value)
        emu = self.emulator_type()
        emu.begin_emulation(["/nas/share/dreamhost/playermissile.com/jumpman/tutorial/clockwise.atr"])
        for i in range(self.skip_frames_on_boot):
            emu.next_frame()
        self.emulator = emu
        print("EMULATOR SEGMENST", emu.segments)
        self.bytes = emu.raw_array
        self.style = np.zeros([len(self.bytes)], dtype=np.uint8)
        self.parse_segments([segment_parser_factory(emu.segments)])
        print("CERATED SEGMENST:", self.segments)
