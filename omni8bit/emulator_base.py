import numpy as np


class EmulatorBase(object):
    cpu = "<base>"
    name = "<name>"
    pretty_name = "<pretty name>"

    input_array_dtype = None
    output_array_dtype = None
    width = 320
    height = 192

    low_level_interface = None  # cython module; e.g.: libatari800, lib6502

    # It's possible that the emulator (like atari800) needs the timer to
    # continue so that the next cpu emulation step will enter the debugger.
    # Emulators that don't have an alternate event loop will turn the timer
    # off.
    stop_timer_for_debugger = True

    def __init__(self):
        self.input = np.zeros([1], dtype=self.input_array_dtype)
        self.output = np.zeros([1], dtype=self.output_array_dtype)

        self.frame_count = 0
        self.frame_event = []
        self.history = {}
        self.offsets = None
        self.names = None
        self.segments = None
        self.active_event_loop = None
        self.compute_color_map()
        self.screen_rgb, self.screen_rgba = self.calc_screens()

    @property
    def raw_array(self):
        return self.output.view(dtype=np.uint8)

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

    def debug_video(self):
        pass

    def compute_color_map(self):
        pass

    def calc_screens(self):
        rgb = np.empty((self.height, self.width, 3), np.uint8)
        rgba = np.empty((self.height, self.width, 4), np.uint8)
        return rgb, rgba

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

    def begin_emulation(self, emu_args=None, boot_segment=None, *args, **kwargs):
        self.args = self.process_args(emu_args, boot_segment)
        event_loop, event_loop_args = self.configure_event_loop(*args, **kwargs)
        self.low_level_interface.start_emulator(self.args, event_loop, event_loop_args)
        self.low_level_interface.prepare_arrays(self.input, self.output)
        self.parse_state()
        self.generate_extra_segments()
        self.cpu_state = self.calc_cpu_data_array()
        self.main_memory = self.calc_main_memory_array()
        self.boot_from_segment(boot_segment)

    def configure_event_loop(self, event_loop=None, event_loop_args=None, *args, **kwargs):
        return None, None

    def process_args(self, emu_args, boot_segment):
        return emu_args

    def boot_from_segment(self, segment):
        pass

    def parse_state(self):
        base = np.byte_bounds(self.output)[0]
        self.video_start_offset = np.byte_bounds(self.video_array)[0] - base
        self.audio_start_offset = np.byte_bounds(self.audio_array)[0] - base
        self.state_start_offset = np.byte_bounds(self.state_array)[0] - base
        self.segments = [
            (self.video_start_offset, self.video_start_offset + len(self.video_array), 0, "Video Frame"),
            (self.audio_start_offset, self.audio_start_offset + len(self.audio_array), 0, "Audio Data"),
        ]

    def generate_extra_segments(self):
        pass

    def next_frame(self):
        self.process_key_state()
        self.frame_count += 1
        self.low_level_interface.next_frame(self.input, self.output)
        self.process_frame_events()
        self.save_history()

    def process_frame_events(self):
        still_waiting = []
        for count, callback in self.frame_event:
            if self.frame_count >= count:
                print("processing %s", callback)
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
        pass

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

    # Debugger interface

    def enter_debugger(self):
        pass

    def leave_debugger(self):
        self.low_level_interface.monitor_clear()
        self.restart_cpu()

    def restart_cpu(self):
        self.low_level_interface.monitor_summary()

    def get_current_state(self):
        self.low_level_interface.get_current_state(self.output)

    def debugger_step(self):
        """Process one CPU instruction.

        Returns boolean indicating if normal processing is to resume (True) or
        continue debugging (False)
        """
        self.low_level_interface.monitor_step()
        return self.is_debugger_finished()

    def is_debugger_finished(self):
        raise NotImplementedError("subclass must check if debugger is still running.")

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
            self.print_history(frame_number)

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
