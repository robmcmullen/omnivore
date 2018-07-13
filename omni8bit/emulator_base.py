import os
import tempfile

import numpy as np

from .debugger import Debugger

import logging
log = logging.getLogger(__name__)


# Values must correspond to values in libdebugger.h
FRAME_START = 0
FRAME_FINISHED = 1
FRAME_BREAKPOINT = 2
FRAME_WATCHPOINT = 3


class EmulatorBase(Debugger):
    cpu = "<base>"
    name = "<name>"
    pretty_name = "<pretty name>"

    mime_prefix = "<mime type>"

    input_array_dtype = None
    output_array_dtype = None
    width = 320
    height = 192

    low_level_interface = None  # cython module; e.g.: libatari800, lib6502

    def __init__(self):
        Debugger.__init__(self)
        self.input_raw = np.zeros([self.input_array_dtype.itemsize], dtype=np.uint8)
        self.input = self.input_raw.view(dtype=self.input_array_dtype)
        self.output_raw = np.zeros([self.output_array_dtype.itemsize], dtype=np.uint8)
        self.output = self.output_raw.view(dtype=self.output_array_dtype)

        self.bootfile = None
        self.frame_count = 0
        self.frame_event = []
        self.history = {}
        self.offsets = None
        self.names = None
        self.segments = None
        self.active_event_loop = None
        self.main_memory = None
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
    def current_frame_number(self):
        return self.output['frame_number'][0]

    @property
    def is_frame_finished(self):
        return self.output['frame_status'][0] == FRAME_FINISHED

    @property
    def current_cycle_in_frame(self):
        return self.output['current_cycle_in_frame'][0]

    @property
    def break_condition(self):
        if self.output['frame_status'][0] == FRAME_BREAKPOINT:
            bpid = self.output['breakpoint_id'][0]
            return self.get_breakpoint(bpid)
        elif self.output['frame_status'][0] == FRAME_WATCHPOINT:
            bpid = self.output['breakpoint_id'][0]
            return self.get_watchpoint(bpid)
        else:
            return None

    @property
    def current_cpu_status(self):
        return "not running"

    @classmethod
    def guess_from_document(cls, document):
        try:
            mime = document.metadata.mime
        except:
            pass
        else:
            if mime.startswith(cls.mime_prefix):
                return True
        return False

    ##### Video

    def compute_color_map(self):
        pass

    def calc_screens(self):
        rgb = np.empty((self.height, self.width, 3), np.uint8)
        rgba = np.empty((self.height, self.width, 4), np.uint8)
        return rgb, rgba

    ##### Object serialization

    def report_configuration(self):
        """Return dictionary of configuration parameters"""
        return {}

    def update_configuration(self, conf):
        """Sets some configuration parameters based on the input dictionary.

        Only the parameters specified by the dictionary members are updated,
        other parameters not mentioned are unchanged.
        """
        pass

    def serialize_state(self, mdict):
        return {"name": self.name}

    ##### Initialization

    def configure_emulator(self, emu_args=None, *args, **kwargs):
        self.args = self.process_args(emu_args)
        self.low_level_interface.clear_state_arrays(self.input, self.output)
        self.low_level_interface.start_emulator(self.args)
        self.configure_io_arrays()

    def configure_io_arrays(self):
        self.low_level_interface.configure_state_arrays(self.input, self.output)
        self.parse_state()
        self.generate_extra_segments()
        self.cpu_state = self.calc_cpu_data_array()
        self.main_memory = self.calc_main_memory_array()

    def process_args(self, emu_args):
        return emu_args if emu_args else []

    ##### Machine boot

    def boot_from_segment(self, boot_segment):
        if self.bootfile is not None:
            try:
                os.remove(self.bootfile)
                self.bootfile = None
            except:  # MSW raises WindowsError, but that's not defined cross-platform
                log.warning("Unable to remove temporary boot file %s." % self.bootfile)
        if boot_segment is not None:
            fd, self.bootfile = tempfile.mkstemp(".atari_boot_segment")
            fh = os.fdopen(fd, "wb")
            fh.write(boot_segment.data.tobytes())
            fh.close()
            log.debug(f"Created temporary file {self.bootfile} to use as boot disk image")
            self.boot_from_file(self.bootfile)
        else:
            self.bootfile = None

    def boot_from_file(self, filename):
        log.debug(f"booting {self.pretty_name} from {filename}")
        self.load_disk(1, filename)
        self.coldstart()

    def parse_state(self):
        base = np.byte_bounds(self.output)[0]
        self.video_start_offset = np.byte_bounds(self.video_array)[0] - base
        self.audio_start_offset = np.byte_bounds(self.audio_array)[0] - base
        self.state_start_offset = np.byte_bounds(self.state_array)[0] - base
        self.segments = [
            (self.video_start_offset, len(self.video_array), 0, "Video Frame"),
            (self.audio_start_offset, len(self.audio_array), 0, "Audio Data"),
        ]

    def generate_extra_segments(self):
        pass

    def next_frame(self):
        self.process_key_state()
        if not self.is_frame_finished:
            print(f"next_frame: continuing frame from cycle {self.current_cycle_in_frame} of frame {self.current_frame_number}")
        self.low_level_interface.next_frame(self.input, self.output, self.debug_cmd)
        if self.is_frame_finished:
            self.frame_count += 1
            self.process_frame_events()
            self.save_history()
        return self.break_condition

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
        pass

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

    # Utility functions

    def load_disk(self, drive_num, pathname):
        self.low_level_interface.load_disk(drive_num, pathname)

    def save_history(self):
        # History is saved in a big list, which will waste space for empty
        # entries but makes things extremely easy to manage. Simply delete
        # a history entry by setting it to NONE.
        frame_number = self.output['frame_number'][0]
        if self.frame_count % 10 == 0:
            d = self.output.copy()
            self.history[frame_number] = d
            # self.print_history(frame_number)

    def restore_history(self, frame_number):
        print(("restoring state from frame %d" % frame_number))
        if frame_number < 0:
            return
        try:
            d = self.history[frame_number]
        except KeyError:
            pass
        else:
            self.low_level_interface.restore_state(d)
            self.history[frame_number + 1:] = []  # remove frames newer than this
            print(("  %d items remain in history" % len(self.history)))
            self.frame_event = []

    def print_history(self, frame_number):
        d = self.history[frame_number]
        print("history[%d] of %d: %d %s" % (d['frame_number'], len(self.history), len(d), d['state'][0][0:8]))

    def get_previous_history(self, frame_cursor):
        n = frame_cursor - 1
        while n > 0:
            if n in self.history:
                return n
            n -= 1
        raise IndexError("No previous frame")

    def get_next_history(self, frame_cursor):
        n = frame_cursor + 1
        while n < len(self.history):
            if n in self.history:
                return n
            n += 1
        raise IndexError("No next frame")

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
