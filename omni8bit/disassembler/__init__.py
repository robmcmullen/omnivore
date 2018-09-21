import importlib
import functools

import numpy as np

from . import dtypes as ud
from . import flags

import logging
log = logging.getLogger(__name__)


try:
    from .miniasm import MiniAssembler
    from .disasm import DisassemblyConfig, ParsedDisassembly
    from . import libudis
except RuntimeError:
    log.warning("cputables.py not generated; disassembler and mini assembler will not be available")
except ModuleNotFoundError:
    log.warning("udis_fast C extensions not created; disassembler and mini assembler will not be availabe")

