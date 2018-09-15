# Debugger breakpoint definition
import numpy as np

MAIN_MEMORY_SIZE = 1<<16

HISTORY_ENTRY_DTYPE = np.dtype([
    ("pc", np.uint16),
    ("target_addr", np.uint16),
    ("num_bytes", np.uint8),
    ("flag", np.uint8),
    ("disassembler_type", np.uint8),
    ("unused", np.uint8),
    ("instruction", np.uint8, 16),
])

