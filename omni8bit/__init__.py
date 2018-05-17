from .atari800 import Atari800

known_emulators = [Atari800]

default_emulator = Atari800


def find_emulator(emulator_name):
    for e in known_emulators:
        if e.name == emulator_name or e == emulator_name:
            return e
    raise UnknownEmulatorError("Unknown emulator '%s'" % emulator_name)
