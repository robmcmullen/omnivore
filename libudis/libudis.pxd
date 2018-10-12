cimport numpy as np

cdef struct history_entry_t:
    np.uint16_t pc;
    np.uint16_t target_addr;
    np.uint8_t num_bytes;
    np.uint8_t disassembler_type;
    np.uint8_t flag;
    np.uint8_t unused;
    np.uint8_t instruction[16];

cdef struct emulator_history_t:
    np.int32_t num_allocated_entries;
    np.int32_t num_entries;
    np.int32_t first_entry_index;
    np.int32_t latest_entry_index;
    np.uint32_t cumulative_count;
    history_entry_t *entries;

ctypedef int (*parse_func_t)(history_entry_t *, unsigned char *, unsigned int, unsigned int, unsigned short *)

ctypedef int (*string_func_t)(history_entry_t *, char *, char *, int, unsigned short *)
