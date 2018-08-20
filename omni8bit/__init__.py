import logging
logging.basicConfig(level=logging.WARNING)
log = logging.getLogger(__name__)

known_emulators = []
default_emulator = None

try:
    from .atari800 import wxAtari800
    known_emulators.append(wxAtari800)
    if default_emulator is None:
        default_emulator = wxAtari800
except ImportError as e:
    log.warning(f"Atari800 emulator not available: {e}")

try:
    from .generic6502 import Generic6502
    known_emulators.append(Generic6502)
    if default_emulator is None:
        default_emulator = Generic6502
except ImportError as e:
    log.warning(f"Generic6502 emulator not available: {e}")

try:
    from .crabapple import Crabapple
    known_emulators.append(Crabapple)
    if default_emulator is None:
        default_emulator = Crabapple
except ImportError as e:
    log.warning(f"Crabapple emulator not available: {e}")


from . import debugger
from .errors import *


def find_emulator(emulator_name):
    for e in known_emulators:
        if e.name == emulator_name or e == emulator_name:
            return e
    raise UnknownEmulatorError("Unknown emulator '%s'" % emulator_name)


def guess_emulator(document):
    for e in known_emulators:
        if e.guess_from_document(document):
            return e
    raise UnknownEmulatorError("Unknown emulator '%s'" % emulator_name)
