import os
import time

import wx
import numpy as np
from atrcopy import SegmentData, DefaultSegment, DefaultSegmentParser, InvalidSegmentParser, SegmentParser

# Enthought library imports.
from traits.api import Trait, Any, List, Event, Dict, Property, Bool, Int, String, Float, Undefined

from omni8bit import find_emulator, guess_emulator, default_emulator, UnknownEmulatorError

from ..document import SegmentedDocument

from . import event_loop as el

import logging
log = logging.getLogger(__name__)


class EmulatorSegmentParser(SegmentParser):
    menu_name = "Emulator Save State"
    def parse(self):
        r = self.segment_data
        self.segments.append(self.container_segment(r, 0, name=self.menu_name))
        for start, count, offset, name in self.emulator_segments:
            if count > 0:
                self.segments.append(DefaultSegment(r[start:start + count], offset, name))

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

    boot_segment = Any(None)

    emulator_type = Any(Undefined)

    emulator = Any(None)

    skip_frames_on_boot = Int(0)

    # Update the graphic screen
    emulator_update_screen_event = Event

    framerate = Float(1/60.0)

    tickrate = Float(1/60.0)

    last_update_time = Float(0.0)

    ##### trait default values

    def _emulator_type_changed(self, value):
        try:
            emu_cls = find_emulator(value)
        except UnknownEmulatorError:
            try:
                emu_cls = guess_emulator(self.source_document)
            except UnknownEmulatorError:
                emu_cls = emu.default_emulator
        emu = emu_cls()
        log.debug(f"emulator changed to {emu}")
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
            self.emulator_type = find_emulator(e['emulator_type'])
        self.skip_frames_on_boot = e.get('skip_frames_on_boot', 0)

    def serialize_extra_to_dict(self, mdict):
        SegmentedDocument.serialize_extra_to_dict(self, mdict)

        mdict["emulator_type"] = self.emulator.name
        mdict["skip_frames_on_boot"] = self.skip_frames_on_boot

    ##### Initial viewer defaults

    def find_initial_visible_segment(self, linked_base, default=0):
        for segment in self.segments:
            log.debug(f"Looking for Main Memory segment: {segment}")
            if segment.name == "Main Memory":
                linked_base.find_segment(segment, refresh=False)
                break
        else:
            log.warning("Didn't find Main Memory segment in emulator")

    #####

    def calc_layout_template_name(self, task_id):
        return "%s.emulator_layout" % task_id

    def boot(self, segment=None):
        if segment is None:
            segment = self.source_document.container_segment
        emu = self.emulator
        emu.configure_emulator([], event_loop=el.start_monitor, event_loop_args=self)
        emu.boot_from_segment(segment)
        for i in range(self.skip_frames_on_boot):
            emu.next_frame()
        self.raw_bytes = emu.raw_array
        self.style = np.zeros([len(self.raw_bytes)], dtype=np.uint8)
        self.parse_segments([segment_parser_factory(emu.segments)])
        log.debug("Segments after boot: %s" % str(self.segments))
        self.create_timer()
        self.start_timer()

    def load(self, segment=None):
        if segment is None:
            segment = self.source_document.container_segment
        emu = self.emulator
        emu.begin_emulation([], segment, event_loop=el.start_monitor, event_loop_args=self)
        for i in range(self.skip_frames_on_boot):
            emu.next_frame()
        self.raw_bytes = emu.raw_array
        self.style = np.zeros([len(self.raw_bytes)], dtype=np.uint8)
        self.parse_segments([segment_parser_factory(emu.segments)])
        log.debug("Segments after boot: %s" % str(self.segments))
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
        log.debug(f"showing frame {frame_number}")
        self.emulator_update_screen_event = True
        self.priority_level_refresh_event = True
        after = time.time()
        delta = after - now
        if delta > self.framerate:
            next_time = self.framerate * .8
        elif delta < self.framerate:
            next_time = self.framerate - delta
        log.debug(f"now={now} show={after-now} delta={delta} framerate={self.framerate} next_time={next_time}")
        if next_time <= 0.001:
            log.warning("need to drop frames!")
            next_time = .001
        self.emulation_timer.StartOnce(next_time * 1000)
        self.last_update_time = now

    def pause_emulator(self):
        print("pause")
        emu = self.emulator
        if emu.stop_timer_for_debugger:
            self.stop_timer()
        emu.get_current_state()  # force output array update which normally happens only at the end of a frame
        self.emulator_update_screen_event = True
        self.priority_level_refresh_event = 100
        emu.debug_state()
        emu.enter_debugger()

    def restart_emulator(self):
        print("restart")
        self.emulator.leave_debugger()
        self.start_timer()
        self.emulator_update_screen_event = True

    def debugger_step(self):
        print("stepping")
        resume_normal_processing = self.emulator.debugger_step()
        if not resume_normal_processing:
            print("updating after step")
            self.emulator_update_screen_event = True
            self.priority_level_refresh_event = 100
