import wx

import pyatari800 as a8
EmulatorBase = a8.EmulatorBase

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
