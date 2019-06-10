import os
import tempfile

import numpy as np

from atrip import find_container

from ..debugger import Debugger
from ..debugger.dtypes import FRAME_STATUS_DTYPE
from .save_state import FrameHistory
from .. import disassembler as disasm
from ..utils.archutil import Labels, load_memory_map

import logging
log = logging.getLogger(__name__)


# Values must correspond to values in libdebugger.h
FRAME_START = 0
FRAME_FINISHED = 1
FRAME_BREAKPOINT = 2
FRAME_WATCHPOINT = 3


class EmulatorBase(Debugger):
    cpu = "<base>"
    ui_name = "<pretty name>"

    mime_prefix = ""
    mime_types = set()

    serializable_attributes = ['input_raw', 'output_raw', 'frame_count']
    serializable_computed = {'input_raw', 'output_raw'}

    input_array_dtype = None
    output_array_dtype = None
    width = 320
    height = 192

    low_level_interface = None  # cython module; e.g.: libatari800, lib6502

    history_entry_dtype = disasm.HISTORY_ENTRY_DTYPE

    def __init__(self):
        Debugger.__init__(self)
        self.input_raw = np.zeros([self.input_array_dtype.itemsize], dtype=np.uint8)
        self.input = self.input_raw.view(dtype=self.input_array_dtype)
        self.output_raw = np.zeros([FRAME_STATUS_DTYPE.itemsize + self.output_array_dtype.itemsize], dtype=np.uint8)
        self.status = self.output_raw[0:FRAME_STATUS_DTYPE.itemsize].view(dtype=FRAME_STATUS_DTYPE)
        self.output = self.output_raw[FRAME_STATUS_DTYPE.itemsize:].view(dtype=self.output_array_dtype)
        self.bootfile = None
        self.frame_count = 0
        self.frame_event = []
        self.frame_history = FrameHistory()
        self.offsets = None
        self.names = None
        self.save_state_memory_blocks = None
        self.main_memory = None
        self.last_boot_state = None
        self.forced_modifier = None
        self.emulator_started = False
        self.cpu_history = None
        self.labels = None

        self.compute_color_map()
        self.screen_rgb, self.screen_rgba = self.calc_screens()

    @property
    def raw_array(self):
        return self.output_raw

    @property
    def raw_state(self):
        return self.output_raw[self.state_start_offset:]

    @property
    def video_array(self):
        return self.output['video'][0]

    @property
    def audio_array(self):
        return self.output['audio'][0]

    @property
    def state_array(self):
        return self.output['state'][0]

    @property
    def memory_access_array(self):
        return self.status['memory_access'][0]

    @property
    def access_type_array(self):
        return self.status['access_type'][0]

    @property
    def current_frame_number(self):
        return self.status['frame_number'][0]

    @property
    def is_frame_finished(self):
        return self.status['frame_status'][0] == FRAME_FINISHED

    @property
    def current_cycle_in_frame(self):
        return self.status['current_cycle_in_frame'][0]

    @property
    def cycles_user(self):
        return self.status['cycles_user'][0]

    @property
    def cycles_since_power_on(self):
        return self.status['cycles_since_power_on'][0]

    @property
    def instructions_since_power_on(self):
        return self.status['instructions_since_power_on'][0]

    @property
    def stack_pointer(self):
        raise NotImplementedError("define stack_pointer property in subclass")

    @stack_pointer.setter
    def stack_pointer(self, value):
        raise NotImplementedError("define stack_pointer property in subclass")

    @property
    def program_counter(self):
        raise NotImplementedError("define program_counter property in subclass")

    @program_counter.setter
    def program_counter(self, value):
        raise NotImplementedError("define program_counter property in subclass")

    @property
    def current_cpu_status(self):
        return "not running"

    @property
    def has_save_points(self):
        return len(self.frame_history) > 0

    @classmethod
    def guess_from_document(cls, document):
        try:
            mime = document.metadata.mime
        except:
            pass
        else:
            if mime in cls.mime_types:
                return True
            elif cls.mime_prefix and mime.startswith(cls.mime_prefix):
                return True
        return False

    ##### Video

    def compute_color_map(self):
        pass

    def calc_screens(self):
        rgb = np.empty((self.height, self.width, 3), np.uint8)
        rgba = np.empty((self.height, self.width, 4), np.uint8)
        return rgb, rgba

    ##### Serialization

    def restore_computed_attributes(self, state):
        Debugger.restore_computed_attributes(self, state)
        self.input_raw[:] = state['input_raw']
        self.restore_state(state['output_raw'])

        # recalculate any internal offsets within output_raw, e.g. atari800
        # needs this because the size of the state save file changes depending
        # on the emulator configuration
        self.low_level_interface.get_current_state(state['output_raw'])
        self.configure_save_state_memory_blocks()

    ##### Initialization

    def configure_emulator(self, emu_args=None, instruction_history_count=100000, *args, **kwargs):
        self.configure_labels()
        self.init_cpu_history(instruction_history_count)
        self.args = self.process_args(emu_args)
        self.low_level_interface.clear_state_arrays(self.input, self.output_raw)
        self.low_level_interface.start_emulator(self.args)
        self.configure_emulator_defaults()
        self.emulator_started = True
        self.configure_io_arrays()

    def configure_labels(self, labels=None):
        if labels is None:
            labels = load_memory_map(self.name)
        self.labels = labels

    def configure_emulator_defaults(self):
        pass

    def configure_io_arrays(self):
        if not self.emulator_started:
            print(f"configure_io_arrays can't be called before emulator started")
            return
        print(f"input_raw: {self.input_raw.shape}  {self.input_raw}")
        print(f"output_raw: {self.output_raw.shape} {self.output_raw}")
        self.low_level_interface.configure_state_arrays(self.input, self.output_raw)
        self.configure_save_state_memory_blocks()

    def configure_save_state_memory_blocks(self):
        self.parse_state()
        self.generate_save_state_memory_blocks()
        self.cpu_state = self.calc_cpu_data_array()
        self.main_memory = self.calc_main_memory_array()

    def process_args(self, emu_args):
        return emu_args if emu_args else []

    def add_segment_to_memory(self, segment):
        start = segment.origin
        end = (start + len(segment)) & 0xffff
        count = end - start
        log.debug(f"Copying {segment} to memory: {start:#04x}-{end:#04x}")
        self.main_memory[start:end] = segment.data[:count]

    ##### Machine boot

    def find_default_boot_segment(self, segments):
        for segment in segments:
            if segment.origin > 0:
                return segment
        return None

    def boot_from_segment(self, boot_segment):
        if boot_segment is not None:
            data = boot_segment.data[:]
            origin = boot_segment.origin
            self.boot_from_raw(data, origin)

    def boot_from_raw(self, data, origin):
        if self.bootfile is not None:
            try:
                os.remove(self.bootfile)
                self.bootfile = None
            except:  # MSW raises WindowsError, but that's not defined cross-platform
                log.warning("Unable to remove temporary boot file %s." % self.bootfile)
        fd, self.bootfile = tempfile.mkstemp(".omnivore_boot_segment")
        fh = os.fdopen(fd, "wb")
        fh.write(data)
        fh.close()
        log.debug(f"Created temporary file {self.bootfile} to use as boot disk image")
        self.boot_from_file(self.bootfile)

    def boot_from_file(self, filename):
        container = find_container(filename, True)
        print(f"container: filename={filename} {container}")
        run_addr = None
        for s in container.iter_segments():
            print(f"segment: {s}")
            if s.origin > 0:
                try:
                    run_addr = s.run_address()
                except AttributeError:
                    if run_addr is None:
                        run_addr = s.origin
                self.add_segment_to_memory(s)
        print(f"running at: {hex(run_addr)}")
        self.program_counter = run_addr
        self.last_boot_state = self.calc_current_state()
        self.coldstart()

    def parse_state(self):
        base = np.byte_bounds(self.output_raw)[0]
        self.state_start_offset = np.byte_bounds(self.state_array)[0] - base

        memaccess_offset = np.byte_bounds(self.memory_access_array)[0] - base
        memtype_offset = np.byte_bounds(self.access_type_array)[0] - base
        video_offset = np.byte_bounds(self.video_array)[0] - base
        audio_offset = np.byte_bounds(self.audio_array)[0] - base
        self.save_state_memory_blocks = [
            (memaccess_offset, self.memory_access_array.nbytes, 0, "Memory Access"),
            (memtype_offset, self.access_type_array.nbytes, 0, "Access Type"),
            (video_offset, self.video_array.nbytes, 0, "Video Frame"),
            (audio_offset, self.audio_array.nbytes, 0, "Audio Data"),
        ]

    def generate_save_state_memory_blocks(self):
        pass

    def next_frame(self):
        self.process_key_state()
        if not self.is_frame_finished:
            print(f"next_frame: continuing frame from cycle {self.current_cycle_in_frame} of frame {self.current_frame_number}")
        bpid = self.low_level_interface.next_frame(self.input, self.output_raw, self.debug_cmd, self.cpu_history)
        if self.is_frame_finished:
            self.frame_count += 1
            self.process_frame_events()
            self.save_history()
        self.forced_modifier = None
        return self.get_breakpoint(bpid)

    def process_frame_events(self):
        still_waiting = []
        for count, callback in self.frame_event:
            if self.frame_count >= count:
                log.debug("processing %s", callback)
                callback()
            else:
                still_waiting.append((count, callback))
        self.frame_event = still_waiting

    def end_emulation(self):
        pass

    def debug_video(self):
        """Return text based view of portion of video array, for debugging
        purposes only so it doesn't have to be fast.
        """
        pass

    def debug_state(self):
        """Show CPU status registers
        """
        print(self.current_cpu_status)

    # Emulator user input functions

    def get_special_key_actions(self):
        """If this emulator has any special keys that may be hard to duplicate
        on a modern keyboard, an action name can be added here and it will be
        added to the menubar.
        """
        return []

    def coldstart(self):
        """Simulate an initial power-on startup.
        """
        pass

    def warmstart(self):
        """Simulate a warm start; i.e. pressing the system reset button
        """
        pass

    def keypress(self, ascii_char):
        """Pass an ascii char to the emulator
        """
        self.send_char(ord(ascii_char))

    def joystick(self, stick_num, direction_value, trigger_pressed=False):
        """Pass a joystick/trigger value to the emulator
        """
        pass

    def paddle(self, paddle_num, paddle_percentage):
        """Pass a paddle value to the emulator
        """
        pass

    def process_key_state(self):
        """Read keyboard and compute any values that should be sent to the
        emulator.
        """
        pass

    def process_key_down(self, evt, keycode):
        pass

    def process_key_up(self, evt, keycode):
        pass

    ##### Input routines

    def send_char(self, key_char):
        print(f"sending char: {key_char}")
        self.input['keychar'] = key_char
        self.input['keycode'] = 0
        self.input['special'] = 0

    def send_keycode(self, keycode):
        self.input['keychar'] = 0
        self.input['keycode'] = keycode
        self.input['special'] = 0

    def send_special_key(self, key_id):
        self.input['keychar'] = 0
        self.input['keycode'] = 0
        self.input['special'] = key_id

    def clear_keys(self):
        self.input['keychar'] = 0
        self.input['keycode'] = 0
        self.input['special'] = 0

    # Utility functions

    def load_disk(self, drive_num, pathname):
        self.low_level_interface.load_disk(drive_num, pathname)

    def calc_current_state(self):
        return self.output_raw.copy()

    def save_history(self, force=False):
        # History is saved in a big list, which will waste space for empty
        # entries but makes things extremely easy to manage. Simply delete
        # a history entry by setting it to NONE.
        frame_number = int(self.status['frame_number'][0])
        if force or self.frame_history.is_memorable(frame_number):
            print(f"Saving history at {frame_number}")
            d = self.calc_current_state()
            self.frame_history.save_frame(frame_number, d)
            self.print_history(frame_number)

    def get_history(self, frame_number):
        frame_number = int(frame_number)
        raw = self.frame_history[frame_number]
        status = raw[0:FRAME_STATUS_DTYPE.itemsize].view(dtype=FRAME_STATUS_DTYPE)
        output = raw[FRAME_STATUS_DTYPE.itemsize:].view(dtype=self.output_array_dtype)
        return status, output

    def restore_state(self, state):
        self.low_level_interface.restore_state(state)
        self.output_raw[:] = state

    def restore_history(self, frame_number):
        print(("restoring state from frame %d" % frame_number))
        frame_number = int(frame_number)
        if frame_number < 0:
            return
        try:
            d = self.frame_history[frame_number]
        except KeyError:
            log.error(f"{frame_number} not in history")
            pass
        else:
            self.restore_state(d)
            # self.frame_history[(frame_number + 1):] = []  # remove frames newer than this
            # print(("  %d items remain in history" % len(self.frame_history)))
            # self.frame_event = []

    def print_history(self, frame_number):
        d = self.frame_history[frame_number]
        status = d[:FRAME_STATUS_DTYPE.itemsize].view(dtype=FRAME_STATUS_DTYPE)
        output = d[FRAME_STATUS_DTYPE.itemsize:].view(dtype=self.output_array_dtype)
        print("history[%d] of %d: %d %s" % (status['frame_number'], len(self.frame_history), len(d), output['state'][0][0:8]))

    def get_previous_history(self, frame_cursor):
        return self.frame_history.get_previous_frame(frame_cursor)

    def get_next_history(self, frame_cursor):
        return self.frame_history.get_next_frame(frame_cursor)

    # graphics

    def get_color_indexed_screen(self, frame_number=-1):
        """Return color indexed screen in whatever native format this
        emulator supports
        """
        pass

    def get_frame_rgb(self, frame_number=-1):
        """Return RGB image of the current screen
        """

    def get_frame_rgba(self, frame_number=-1):
        """Return RGBA image of the current screen
        """

    def get_frame_rgba_opengl(self, frame_number=-1):
        """Return RGBA image of the current screen, suitable for use with
        OpenGL (flipped vertically)
        """

    # CPU history

    def init_cpu_history(self, num_entries):
        self.cpu_history = disasm.HistoryStorage(num_entries)

    def cpu_history_show_range(self, from_index, details=False):
        self.cpu_history.debug_range(from_index)

    def cpu_history_show_next_instruction(self):
        self.low_level_interface.show_next_instruction(self.cpu_history)

    def calc_stringified_history(self, start_index, count):
        """Returns an list of indexes into the entries array for the
        range of history requested.

        Because it's a circular buffer, the wraparound case is unable to be
        handled by numpy, so instead is used to map the row number in the
        display window (which ranges from 0 -> count) to the history entry
        starting at first_entry_index + start_index for count entries.
        """
        return self.cpu_history.stringify(start_index, count, self.labels.labels)

    @property
    def num_cpu_history_entries(self):
        return len(self.cpu_history)
