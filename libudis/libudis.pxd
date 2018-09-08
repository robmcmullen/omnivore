cimport numpy as np

cdef struct history_entry_t:
    np.uint16_t pc;
    np.uint16_t target_addr;
    np.uint8_t num_bytes;
    np.uint8_t flag;
    np.uint8_t disassembler_type;
    np.uint8_t unused;
    np.uint8_t instruction[16];


ctypedef int (*parse_func_t)(history_entry_t *line, unsigned char *, unsigned int, unsigned int, unsigned short *)
