import logging
logging.basicConfig(level=logging.WARNING)
log = logging.getLogger(__name__)

known_emulators = []
default_emulator = None

debug_import = False

try:
    from .atari8bit import wxAtari800, wxAtari800XL, wxAtari5200
    known_emulators.append(wxAtari800)
    known_emulators.append(wxAtari800XL)
    known_emulators.append(wxAtari5200)
    if default_emulator is None:
        default_emulator = wxAtari800
except ImportError as e:
    log.warning(f"Atari800 emulator not available: {e}")
    if debug_import:
        raise

try:
    from .generic6502 import Generic6502
    known_emulators.append(Generic6502)
    if default_emulator is None:
        default_emulator = Generic6502
except ImportError as e:
    log.warning(f"Generic6502 emulator not available: {e}")
    if debug_import:
        raise

try:
    from .apple2 import Crabapple
    known_emulators.append(Crabapple)
    if default_emulator is None:
        default_emulator = Crabapple
except ImportError as e:
    log.warning(f"Crabapple emulator not available: {e}")
    if debug_import:
        raise
