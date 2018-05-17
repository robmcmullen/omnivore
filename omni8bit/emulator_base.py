import numpy as np


class EmulatorBase(object):
    cpu = "6502"
    name = "<name>"
    pretty_name = "<pretty name>"

    input_array_dtype = None
    output_array_dtype = None
    width = 320
    height = 192

    def __init__(self):
        self.input = np.zeros([1], dtype=self.input_array_dtype)
        self.output = np.zeros([1], dtype=self.output_array_dtype)

        self.frame_count = 0
        self.frame_event = []
        self.history = []
        self.offsets = None
        self.names = None
        self.segments = None
        self.active_event_loop = None
        self.compute_color_map()
        self.screen_rgb, self.screen_rgba = self.calc_screens()

    def compute_color_map(self):
        pass

    def calc_screens(self):
        return None, None

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

    def begin_emulation(self, emu_args=None, *args, **kwargs):
        pass

    def next_frame(self):
        pass

    def end_emulation(self):
        pass

    def debug_video(self):
        """Return text based view of portion of video array, for debugging
        purposes only so it doesn't have to be fast.
        """
        pass

    def get_cpu(self):
        """Return current state of the CPU registers as a numpy array.

        This should be a view such that changes made here will be reflected for
        the next instruction processed by the emulator. It should also use a
        dtype with names so that viewers can display a list of registers
        without having internal knowledge of the CPU.
        """
        pass

    # Utility functions

    def coldstart(self):
        """Simulate an initial power-on startup.
        """
        pass

    def warmstart(self):
        """Simulate a warm start; i.e. pressing the system reset button
        """
        pass

    def load_disk(self, drive_num, pathname):
        a8.load_disk(drive_num, pathname)

    def save_history(self):
        # History is saved in a big list, which will waste space for empty
        # entries but makes things extremely easy to manage. Simply delete
        # a history entry by setting it to NONE.
        if self.frame_count % 10 == 0:
            d = self.output.copy()
            print "history at %d: %d %s" % (d['frame_number'], len(d), d['state'][0:8])
        else:
            d = None
        self.history.append(d)

    def restore_history(self, frame_number):
        pass

    def print_history(self, frame_number):
        pass

    def get_previous_history(self, frame_cursor):
        raise IndexError("No previous frame")

    def get_next_history(self, frame_cursor):
        raise IndexError("No next frame")

    def get_frame(self, frame_number=-1):
        # Get numpy array of RGB(A) data for the specified frame
        pass
