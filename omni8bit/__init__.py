from .atari800 import Atari800
from .generic6502 import Generic6502

known_emulators = [Atari800, Generic6502]

default_emulator = Atari800


class Omni8bitError(RuntimeError):
    pass


class UnknownEmulatorError(Omni8bitError):
    pass


def find_emulator(emulator_name):
    for e in known_emulators:
        if e.name == emulator_name or e == emulator_name:
            return e
    raise UnknownEmulatorError("Unknown emulator '%s'" % emulator_name)
