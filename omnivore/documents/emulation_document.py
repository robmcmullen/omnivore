import os
import time

import wx
import numpy as np

from atrip import Collection, Container, Segment, errors

from sawx.document import SawxDocument
from sawx.utils.nputil import to_numpy
from sawx.events import EventHandler

from .. import emulator as em
from .. import errors
from ..document import DiskImageDocument

import logging
log = logging.getLogger(__name__)


class EmulationTimer(wx.Timer):
    def __init__(self, document):
        self.document = document
        wx.Timer.__init__(self)

    def Notify(self):
        self.document.ready_for_next_frame()


class EmulationDocument(DiskImageDocument):
    """A wrapper around the low-level `Emulator` instance that manages
    the timing when running the emulator.

    Only one instance of a particular emulator type is allowed at any one time.
    The low level C code used in most emulators can't run multiple instances of
    themselves, e.g. atari800 uses global variables for most of its state.
    """

    # Class attributes

    emulation_timer = None

    metadata_extension = ".omniemu"

    # Lookup mapping of emulator ui_name to actual emulator instance to make
    # sure only one emulator of a particular type is used at any one time. I
    # think that's a livable restriction for now.
    emulator_document = {}

    def __init__(self, file_metadata, emulator_type, emulator, source_document=None):
        super().__init__(file_metadata)
        self.source_document = source_document
        self.boot_segment = None
        self.emulator_type = emulator_type
        self.emulator = emulator
        self.skip_frames_on_boot = 0
        self.pause_emulator_on_boot = False
        self.emu_container = None
        self.collection = None

        # Update the graphic screen
        self.priority_level_refresh_event = EventHandler(self)
        self.emulator_breakpoint_event = EventHandler(self)
        self.emulator_update_screen_event = EventHandler(self)
        self.framerate = 1/60.0
        self.tickrate = 1/60.0
        self.last_update_time = 0.0

    #### dunder methods

    def __str__(self):
        return f"EmulationDocument: mime={self.mime}, {self.uri}. {self.emulator_type} source={self.source_document}"

    @classmethod
    def create_document(cls, source_document, emulator_type, skip_frames_on_boot=None, extra_metadata=None):
        try:
            emu_cls = em.find_emulator(emulator_type)
        except errors.UnknownEmulatorError:
            if not emulator_type:
                # if no value specified, try to determine from binary data
                try:
                    emu_cls = em.guess_emulator(source_document)
                except errors.UnknownEmulatorError:
                    emu_cls = em.default_emulator
            else:
                # if emulator name specified but not known, return error
                raise RuntimeError(f"Unknown emulator {emulator_type}")
        if emu_cls is None:
            raise RuntimeError(f"Couldn't determine an emulator for:\n\n{source_document.uri}\n\nand no default emulator specified. Chose an emulator in preferences")
        emu_doc = cls.emulator_document.get(emu_cls.ui_name, None)
        if emu_doc is not None:
            error = errors.EmulatorInUseError(f"Only one {emu_doc.emulator.ui_name} emulator can run at one time.")
            error.current_emulator_document = emu_doc
            raise error
        emu = emu_cls()
        emu.configure_emulator()
        log.debug(f"emulator changed to {emu}")
        doc = cls(None, emulator_type, emu, source_document)
        if skip_frames_on_boot is not None:
            doc.skip_frames_on_boot = skip_frames_on_boot
        elif source_document.skip_frames_on_boot > 0:
            doc.skip_frames_on_boot = source_document.skip_frames_on_boot
        if extra_metadata:
            doc.restore_save_points_from_dict(extra_metadata)
        cls.pause_emulator_on_boot = source_document.pause_emulator_on_boot
        cls.emulator_document[emu_cls.ui_name] = doc
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
        if 'restart_tree' in e:
            self.emulator.restart_tree.restore_from_dict(e)
            self.emulator.configure_io_arrays()
            self.create_segments()
        if 'current_restart' in e:
            self.emulator.restore_from_dict(e['current_restart'])
        self.skip_frames_on_boot = e.get('skip_frames_on_boot', 0)

    def serialize_extra_to_dict(self, mdict):
        DiskImageDocument.serialize_extra_to_dict(self, mdict)

        mdict["emulator_type"] = self.emulator.name
        mdict.update(self.emulator.restart_tree.serialize_to_dict())
        mdict["current_restart"] = self.emulator.serialize_to_dict()
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
        emu.configure_emulator([])
        if segment is None:
            segment = emu.find_default_boot_segment(self.source_document.segments)

        if segment is not None:
            boot_data = segment.data
            origin = segment.origin
        else:
            raise errors.EmulatorError(f"Can't find bootable segment in {self.source_document}")
        emu.boot_from_segment(segment)
        for i in range(self.skip_frames_on_boot):
            emu.next_frame()
        self.create_segments()
        self.create_timer()
        if not self.pause_emulator_on_boot:
            self.start_timer()

    def load(self, segment=None):
        SawxDocument.load(self, segment)

    def create_segments(self):
        emu = self.emulator
        ec = Container(emu.raw_array, force_numpy_data=True)
        for offset, count, origin, name in emu.save_state_memory_blocks:
            s = Segment(ec, offset, origin, name, length=count)
            ec.segments.append(s)
        collection = Collection(emu.ui_name, container=ec, guess=False)
        log.debug(f"Emulator: {emu} collection:{collection.verbose_info}")
        self.load_collection(collection, self.file_metadata)

    #### cleanup

    def halt_background_processing(self):
        print(f"STOPPING TIMERS! {self}")
        self.stop_timer()
        try:
            emu_doc = self.emulator_document.pop(self.emulator.ui_name)
            if emu_doc != self:
                print(f"Weird: emulator not same as remembered!")
        except KeyError:
            log.error(f"Emulator instance not found! Weird.")
        else:
            emu = self.emulator
            print(f"Removing emulator {emu}")
            emu.prepare_destroy()

    def prepare_destroy(self):
        pass

    #### timer control

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
            self.emulator_update_screen_event(True)
            self.priority_level_refresh_event(True)
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
            self.emulator_update_screen_event(True)
            self.priority_level_refresh_event(100)
            print(f"generating breakpoint event: {breakpoint} at cycles={self.emulator.cycles_since_power_on}")
            self.emulator_breakpoint_event(breakpoint)
            self.stop_timer()
        self.last_update_time = now

    #### emulator commands

    def pause_emulator(self):
        print("pause")
        if not self.emulator_paused:
            emu = self.emulator
            self.stop_timer()
            emu.cpu_history_show_next_instruction()
            self.emulator_update_screen_event(True)
            self.priority_level_refresh_event(100)

    def resume_emulator(self):
        print("resume")
        if self.emulator_paused:
            self.emulator.begin_restart()
            self.start_timer()
            self.emulator_update_screen_event(True)

    def debugger_step(self):
        print("stepping")
        self.emulator.step_into(1)
        self.start_timer()

    def debugger_break_vbi_start(self, count=1):
        print("stepping to VBI")
        self.emulator.break_vbi_start(count)
        self.start_timer()

    def debugger_break_vbi_end(self, count=1):
        print("stepping to end of VBI")
        self.emulator.break_vbi_end(count)
        self.start_timer()

    def debugger_break_dli_start(self, count=1):
        print("stepping to DLI")
        self.emulator.break_dli_start(count)
        self.start_timer()

    def debugger_break_dli_end(self, count=1):
        print("stepping to end of DLI")
        self.emulator.break_dli_end(count)
        self.start_timer()

    def debugger_break_next_scan_line(self, count=1):
        print("stepping to next scan line")
        self.emulator.break_scan_line(count)
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
            self.checkpoint_restore(emu.current_restart, desired)

    def history_next(self):
        emu = self.emulator
        try:
            desired = emu.get_next_history(emu.current_frame_number)
        except IndexError:
            log.warning(f"No next frame: current = {emu.current_frame_number}")
        else:
            self.checkpoint_restore(emu.current_restart, desired)

    def checkpoint_restore(self, restart_number, frame_number):
        emu = self.emulator
        emu.restore_restart(restart_number, frame_number)
        frame_number = self.emulator.status['frame_number']
        log.debug(f"showing frame {frame_number}")
        self.emulator_update_screen_event(True)
        self.priority_level_refresh_event(100)
