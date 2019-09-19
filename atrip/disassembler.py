import importlib
import functools

import numpy as np

from .disassemblers import dtypes as dd
from .disassemblers import flags

import logging
log = logging.getLogger(__name__)


try:
    from .disassemblers.miniasm import MiniAssembler, processors, get_miniasm, mini_assemble
    from .disassemblers.disasm import DisassemblyConfig, ParsedDisassembly
    from .disassemblers.history import HistoryStorage, StringifiedHistory
    from .disassemblers import libudis, cputables
except RuntimeError:
    log.warning("cputables.py not generated; disassembler and mini assembler will not be available")
except ModuleNotFoundError:
    log.warning("libudis C extensions not created; disassembler and mini assembler will not be availabe")
    raise
except ImportError as e:
    log.warning(f"libudis C extension not loaded (likely an undefined symbol):\n{str(e)}")

try:
    from .disassemblers.valid_cpus import valid_cpu_ids, cpu_id_to_name, cpu_name_to_id
except:
    valid_cpu_ids = [10]
    cpu_name_to_id = {"6502": 10}
    cpu_id_to_name = {10: "6502"}



def create_history_dtype(num_entries, history_dtype):
    size = (num_entries + 1) * dd.HISTORY_ENTRY_DTYPE.itemsize
    dtype_entries = list(dd.EMULATOR_HISTORY_HEADER_DTYPE.descr)
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
