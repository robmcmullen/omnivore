import os
import time
import tempfile

import wx
import numpy as np
from atrcopy import SegmentData, DefaultSegment, DefaultSegmentParser, InvalidSegmentParser, SegmentParser

# Enthought library imports.
from traits.api import Trait, Any, List, Event, Dict, Property, Bool, Int, String, Float

from omnivore8bit.document import SegmentedDocument

from . import event_loop as el

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


class EmulationTimer(wx.Timer):
    def __init__(self, document):
        self.document = document
        wx.Timer.__init__(self)

    def Notify(self):
        self.document.ready_for_next_frame()


class EmulationDocument(SegmentedDocument):

    # Class attributes

    emulation_timer = None

    # Traits

    source_document = Any(None)

    emulator_type = Any(None)

    emulator = Any(None)

    skip_frames_on_boot = Int(0)

    # Update the graphic screen
    emulator_update_screen_event = Event

    # Update the info panels; updated at a lower refresh rate than the screen
    # because they're slow on some platforms.
    emulator_update_info_event = Event

    framerate = Float(1/60.0)

    tickrate = Float(1/60.0)

    last_update_time = Float(0.0)

    ##### trait default values

    def _emulator_type_changed(self, value):
        emu = self.emulator_type()
        self.emulator = emu

    @property
    def timer_delay(self):
        # wxpython delays are in milliseconds
        return self.tickrate * 1000

    @property
    def emulator_running(self):
        return self.emulation_timer is not None and self.emulation_timer.IsRunning()

    @property
    def emulator_paused(self):
        return self.emulation_timer is not None and not self.emulation_timer.IsRunning()

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
        emu.begin_emulation([bootfile], el.start_monitor, self)
        for i in range(self.skip_frames_on_boot):
            emu.next_frame()
        self.bytes = emu.raw_array
        self.style = np.zeros([len(self.bytes)], dtype=np.uint8)
        self.parse_segments([segment_parser_factory(emu.segments)])
        log.debug("Segments after boot: %s" % str(self.segments))
        try:
            os.remove(bootfile)
        except:  # MSW raises WindowsError, but that's not defined cross-platform
            log.warning("Unable to remove temporary file %s." % bootfile)
        self.create_timer()
        self.start_timer()

    ##### Emulator commands

    def create_timer(self):
        cls = self.__class__
        if cls.emulation_timer is not None:
            raise RuntimeError("Timer already exists, can't run multiple emulators at once!")
        cls.emulation_timer = EmulationTimer(self)

    def start_timer(self, repeat=False, delay=None, forceupdate=True):
        if not self.emulation_timer.IsRunning():
            self.emulation_timer.StartOnce(self.framerate * 1000)

    def stop_timer(self, repeat=False, delay=None, forceupdate=True):
        self.emulation_timer.Stop()

    def ready_for_next_frame(self):
        now = time.time()
        self.emulator.next_frame()
        frame_number = self.emulator.output['frame_number']
        print("showing frame %d" % frame_number)
        self.emulator_update_screen_event = True
        if frame_number % 10 == 0:
            self.emulator_update_info_event = True
        after = time.time()
        delta = after - now
        if delta > self.framerate:
            next_time = self.framerate * .8
        elif delta < self.framerate:
            next_time = self.framerate - delta
        print("now=%f show=%f delta=%f framerate=%f next_time=%f" % (now, after-now, delta, self.framerate, next_time))
        self.emulation_timer.StartOnce(next_time * 1000)
        self.last_update_time = now

    def pause_emulator(self):
        emu = self.emulator
        emu.get_current_state()  # force output array update which normally happens only at the end of a frame
        self.emulator_update_screen_event = True
        self.emulator_update_info_event = True
        a, p, sp, x, y, _, pc = emu.cpu_state
        print("A=%02x X=%02x Y=%02x SP=%02x FLAGS=%02x PC=%04x" % (a, x, y, sp, p, pc))
        self.emulator.enter_debugger()

    def restart_emulator(self):
        print("restart")
        self.emulator.leave_debugger()
        self.start_timer()
        self.emulator_update_screen_event = True

    def debugger_step(self):
        self.emulator.debugger_step()
