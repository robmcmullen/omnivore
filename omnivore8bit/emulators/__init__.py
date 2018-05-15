import wx

import pyatari800 as a8

from .document import EmulationDocument

known_emulators = [a8.Atari800]

default_emulator = a8.Atari800


class EmulatorError(RuntimeError):
    pass


class UnknownEmulatorError(EmulatorError):
    pass


class EmulatorInUseError(EmulatorError):
    pass


def factory(emulator_name):
    for e in known_emulators:
        if e.name == emulator_name:
            return e
    raise UnknownEmulatorError("Unknown emulator '%s'" % emulator_name)


def restore_emulator(e):
    # restore emulator from defaults supplied in dictionary
    pass


class EmulatorBase(object):
    cpu = "6502"
    name = "<name>"
    pretty_name = "<pretty name>"

    def serialize_state(self, mdict):
        return {"name": self.name}

    def begin_emulation(self, args=None):
        pass

    def next_frame(self):
        pass

    def end_emulation(self):
        pass

    def get_cpu(self):
        # Return current state of the CPU registers. This should be a view such
        # that changes made here will be reflected for the next instruction
        # processed by the emulator
        pass

    def get_ram(self):
        # return current RAM. This should be a view such that changes made here
        # will be reflected for the next instruction processed by the emulator
        pass

    # Utility functions

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
