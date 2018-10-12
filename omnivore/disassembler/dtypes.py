# Debugger breakpoint definition
import numpy as np


HISTORY_ENTRY_DTYPE = np.dtype([
    ("pc", np.uint16),
    ("target_addr", np.uint16),
    ("num_bytes", np.uint8),
    ("disassembler_type", np.uint8),
    ("flag", np.uint8),
    ("cycles", np.uint8),
    ("instruction", np.uint8, 16),
])

HISTORY_6502_DTYPE = np.dtype([
    ("pc", np.uint16),
    ("target_addr", np.uint16),
    ("num_bytes", np.uint8),
    ("disassembler_type", np.uint8),
    ("flag", np.uint8),
    ("cycles", np.uint8),
    ("instruction", np.uint8, 3),
    ("a", np.uint8),
    ("x", np.uint8),
    ("y", np.uint8),
    ("sp", np.uint8),
    ("sr", np.uint8),
    ("before1", np.uint8),
    ("after1", np.uint8),
    ("before2", np.uint8),
    ("after2", np.uint8),
    ("before3", np.uint8),
    ("after3", np.uint8),
    ("extra1", np.uint8),
    ("extra2", np.uint8),
])

HISTORY_ATARI800_DTYPE = np.dtype([
    ("pc", np.uint16),
    ("target_addr", np.uint16),
    ("num_bytes", np.uint8),
    ("disassembler_type", np.uint8),
    ("flag", np.uint8),
    ("cycles", np.uint8),
    ("instruction", np.uint8, 3),
    ("a", np.uint8),
    ("x", np.uint8),
    ("y", np.uint8),
    ("sp", np.uint8),
    ("sr", np.uint8),
    ("before1", np.uint8),
    ("after1", np.uint8),
    ("before2", np.uint8),
    ("after2", np.uint8),
    ("before3", np.uint8),
    ("after3", np.uint8),
    ("antic_xpos", np.uint8),
    ("antic_ypos", np.uint8),
])

HISTORY_FRAME_DTYPE = np.dtype([
    ("frame_number", np.uint32),
    ("num_bytes", np.uint8),
    ("disassembler_type", np.uint8),
    ("flag", np.uint8),
    ("cycles", np.uint8),
    ("instruction", np.uint8, 16),
])

HISTORY_INTERRUPT_DTYPE = np.dtype([
    ("pc", np.uint16),
    ("target_addr", np.uint16),
    ("num_bytes", np.uint8),
    ("disassembler_type", np.uint8),
    ("flag", np.uint8),
    ("cycles", np.uint8),
    ("instruction", np.uint8, 16),
])

HISTORY_BREAKPOINT_DTYPE = np.dtype([
    ("pc", np.uint16),
    ("breakpoint_id", np.uint8),
    ("breakpoint_type", np.uint8),
    ("num_bytes", np.uint8),
    ("disassembler_type", np.uint8),
    ("flag", np.uint8),
    ("disassembler_type_cpu", np.uint8),
    ("instruction", np.uint8, 16),
])

EMULATOR_HISTORY_HEADER_DTYPE = np.dtype([
    ("num_allocated_entries", np.int32),
    ("num_entries", np.int32),
    ("first_entry_index", np.int32),
    ("latest_entry_index", np.int32),
    ("cumulative_count", np.uint32),
])
