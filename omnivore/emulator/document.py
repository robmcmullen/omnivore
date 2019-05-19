import os
import time

import wx
import numpy as np
from atrip import SegmentData, DefaultSegment, DefaultSegmentParser, SegmentParser

# Enthought library imports.
from traits.api import Trait, Any, List, Event, Dict, Property, Bool, Int, String, Float, Undefined

from .. import find_emulator, guess_emulator, default_emulator, UnknownEmulatorError, EmulatorError

from ..document import DiskImageDocument

import logging
log = logging.getLogger(__name__)


class EmulatorSegmentParser(SegmentParser):
    menu_name = "Emulator Save State"
    def parse(self):
        r = self.segment_data
        self.segments.append(self.collection(r, 0, name=self.menu_name))
        for start, count, offset, name in self.save_state_memory_blocks:
            if count > 0:
                print(f"creating emulator segment {name} at {hex(start)}:{hex(start + count)}")
                self.segments.append(DefaultSegment(r[start:start + count], offset, name))

def segment_parser_factory(save_state_memory_blocks):
    cls = type('EmulatorSegmentParser', (EmulatorSegmentParser, SegmentParser), dict(save_state_memory_blocks = save_state_memory_blocks))
    return cls


class EmulationTimer(wx.Timer):
    def __init__(self, document):
        self.document = document
        wx.Timer.__init__(self)

    def Notify(self):
        self.document.ready_for_next_frame()


class EmulationDocument(DiskImageDocument):

    # Class attributes

    emulation_timer = None

    metadata_extension = ".omniemu"

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

    #### object methods

    def __str__(self):
        return f"EmulationDocument: id={self.document_id}, mime={self.metadata.mime}, {self.metadata.uri}. {self.emulator_type} source={self.source_document}"

    @classmethod
    def create_document(cls, source_document, emulator_type, skip_frames_on_boot=False, extra_metadata=None):
        try:
            emu_cls = find_emulator(emulator_type)
        except UnknownEmulatorError:
            if not emulator_type:
                # if no value specified, try to determine from binary data
                try:
                    emu_cls = guess_emulator(source_document)
                except UnknownEmulatorError:
                    emu_cls = default_emulator
            else:
                # if emulator name specified but not known, return error
                raise RuntimeError(f"Unknown emulator {emulator_type}")
        emu = emu_cls()
        emu.configure_emulator()
        log.debug(f"emulator changed to {emu}")
        doc = cls(emulator_type=emulator_type, emulator=emu, source_document=source_document)
        if extra_metadata:
            doc.restore_save_points_from_dict(extra_metadata)
        return doc

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
        DiskImageDocument.restore_extra_from_dict(self, e)
        self.restore_save_points_from_dict(e)

    def restore_save_points_from_dict(self, e):
        # emulator type will already be set at document creation time
        if 'frame_history' in e:
            self.emulator.frame_history.restore_from_dict(e)
            self.emulator.configure_io_arrays()
            self.create_segments()
        if 'current_frame' in e:
            self.emulator.restore_from_dict(e['current_frame'])
        self.skip_frames_on_boot = e.get('skip_frames_on_boot', 0)

    def serialize_extra_to_dict(self, mdict):
        DiskImageDocument.serialize_extra_to_dict(self, mdict)

        mdict["emulator_type"] = self.emulator.name
        mdict.update(self.emulator.frame_history.serialize_to_dict())
        mdict["current_frame"] = self.emulator.serialize_to_dict()
        mdict["skip_frames_on_boot"] = self.skip_frames_on_boot

    def save_to_uri(self, uri, editor, saver=None, save_metadata=True):
        # save both the source document and its .omnivore metadata and...
        self.source_document.save_to_uri(uri, editor, saver, save_metadata)

        # the emulator metadata .omniemu from this emulator document
        if save_metadata:
            self.save_metadata_to_uri(uri, editor)

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

    def boot(self, segment=None):
        emu = self.emulator
        if not emu.has_save_points:
            emu.configure_emulator([])
            if segment is None:
                segment = self.source_document.segment_parser.image.create_emulator_boot_segment()
            elif segment.origin == 0:
                segment = emu.find_default_boot_segment(self.source_document.segments)

            if segment is not None:
                boot_data = segment.data
                origin = segment.origin
            else:
                raise EmulatorError(f"Can't find bootable segment in {self.source_document}")
            emu.boot_from_segment(segment)
            for i in range(self.skip_frames_on_boot):
                emu.next_frame()
        self.create_segments()
        self.start_timer()

    def load(self, segment=None):
        if segment is None:
            segment = self.source_document.collection
        emu = self.emulator
        emu.begin_emulation([], segment)
        for i in range(self.skip_frames_on_boot):
            emu.next_frame()
        self.create_segments()
        self.start_timer()

    def create_segments(self):
        emu = self.emulator
        self.raw_bytes = emu.raw_array
        self.style = np.zeros([len(self.raw_bytes)], dtype=np.uint8)
        self.parse_segments([segment_parser_factory(emu.save_state_memory_blocks)])
        log.debug("Segments after boot: %s" % str(self.segments))
        self.create_timer()

    ##### Emulator commands

    def create_timer(self):
        cls = self.__class__
        if cls.emulation_timer is None:
            cls.emulation_timer = EmulationTimer(self)

    def start_timer(self, repeat=False, delay=None, forceupdate=True):
        if not self.emulation_timer.IsRunning():
            self.emulation_timer.StartOnce(self.framerate * 1000)

    def stop_timer(self, repeat=False, delay=None, forceupdate=True):
        self.emulation_timer.Stop()

    def ready_for_next_frame(self):
        now = time.time()
        breakpoint = self.emulator.next_frame()
        frame_number = self.emulator.status['frame_number']
        log.debug(f"showing frame {frame_number}, breakpoint_id={breakpoint}")
        if breakpoint is None:
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
        else:
            self.emulator_update_screen_event = True
            self.priority_level_refresh_event = 100
            print(f"generating breakpoint event: {breakpoint} at cycles={self.emulator.cycles_since_power_on}")
            self.emulator_breakpoint_event = breakpoint
            self.stop_timer()
        self.last_update_time = now

    def pause_emulator(self):
        print("pause")
        emu = self.emulator
        self.stop_timer()
        emu.cpu_history_show_next_instruction()
        self.emulator_update_screen_event = True
        self.priority_level_refresh_event = 100

    def restart_emulator(self):
        print("restart")
        self.start_timer()
        self.emulator_update_screen_event = True

    def debugger_step(self):
        print("stepping")
        self.emulator.step_into(1)
        self.start_timer()

    def debugger_break_vbi_start(self, count=1):
        print("stepping")
        self.emulator.break_vbi_start(count)
        self.start_timer()

    def debugger_count_frames(self, number=1):
        print(f"counting {number} frames")
        self.emulator.count_frames(number)
        self.start_timer()

    def history_previous(self):
        emu = self.emulator
        try:
            desired = emu.get_previous_history(emu.current_frame_number)
        except IndexError:
            log.warning("No previous frame")
        else:
            emu.restore_history(desired)
            frame_number = self.emulator.status['frame_number']
            log.debug(f"showing frame {frame_number}")
            self.emulator_update_screen_event = True
            self.priority_level_refresh_event = 100

    def history_next(self):
        emu = self.emulator
        try:
            desired = emu.get_next_history(emu.current_frame_number)
        except IndexError:
            log.warning(f"No next frame: current = {emu.current_frame_number}")
        else:
            emu.restore_history(desired)
            frame_number = self.emulator.status['frame_number']
            log.debug(f"showing frame {frame_number}")
            self.emulator_update_screen_event = True
            self.priority_level_refresh_event = 100
