import importlib
import functools

import numpy as np

from .dtypes import *
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



def create_history_dtype(num_entries, history_dtype):
    size = (num_entries + 1) * HISTORY_ENTRY_DTYPE.itemsize
    dtype_entries = list(EMULATOR_HISTORY_HEADER_DTYPE.descr)
    dtype_entries.append(("entries", history_dtype, num_entries))
    print(f"new dtype: {dtype_entries}")
    return np.dtype(dtype_entries)

def create_history(num_entries, history_dtype):
    dtype = create_history_dtype(num_entries, history_dtype)
    # print(f"new dtype: {dtype.itemsize} bytes")
    history = np.zeros(1, dtype=dtype)
    history['num_allocated_entries'] = num_entries
    clear_history(history)
    return history

def clear_history(history):
    history['num_entries'] = 0
    history['first_entry_index'] = 0
    history['latest_entry_index'] = -1
