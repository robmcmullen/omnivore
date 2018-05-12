import os
import tempfile

import numpy as np

# Enthought library imports.
from traits.api import Trait, Any, List, Event, Dict, Property, Bool, Int, String

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
        emu = self.emulator_type()
        self.emulator = emu

    #### serialization methods

    def restore_extra_from_dict(self, e):
        SegmentedDocument.restore_extra_from_dict(self, e)

        if 'emulator_type' in e:
            self.emulator_type = emu.factory[e['emulator_type']]
        self.skip_frames_on_boot = e.get('skip_frames_on_boot', 0)

    def serialize_extra_to_dict(self, mdict):
        SegmentedDocument.serialize_extra_to_dict(self, mdict)

        mdict["emulator_type"] = self.emulator_type.name
        mdict["skip_frames_on_boot"] = self.skip_frames_on_boot

    #####

    def calc_layout_template_name(self, task_id):
        return "%s.emulator_layout" % task_id

    def boot(self, boot_file_type=None):
        if boot_file_type is None:
            boot_file_type = self.source_document.extension
        fd, bootfile = tempfile.mkstemp(boot_file_type)
        fh = os.fdopen(fd, "wb")
        fh.write(self.source_document.container_segment.data.tostring())
        fh.close()
        emu = self.emulator
        emu.begin_emulation([bootfile])
        for i in range(self.skip_frames_on_boot):
            emu.next_frame()
        self.bytes = emu.raw_array
        self.style = np.zeros([len(self.bytes)], dtype=np.uint8)
        self.parse_segments([segment_parser_factory(emu.segments)])
        log.debug("Segments after boot: %s" % str(self.segments))
        try:
            os.remove(bootfile)
        except IOError:
            log.warning("Unable to remove temporary file %s." % bootfile)
