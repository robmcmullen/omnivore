import logging
logging.basicConfig(level=logging.WARNING)
log = logging.getLogger(__name__)

from .emulator import known_emulators, default_emulator

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
    raise UnknownEmulatorError(f"No emulator for {document.mime}")
