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

cdef struct label_info_t:
    np.uint32_t text_start_index;
    np.int8_t line_length;
    np.int8_t num_bytes;
    np.int8_t item_count;
    np.int8_t type_code;

cdef struct label_description_t:
    np.uint8_t text_length;
    np.uint8_t num_bytes;
    np.uint8_t item_count;
    np.uint8_t type_code;
    char label[12];

cdef struct label_storage_t:
    np.uint16_t flags;
    np.uint16_t first_addr;
    np.uint16_t last_addr;
    np.uint16_t num_labels;
    np.uint16_t index[256*256];
    label_description_t labels[1024];

ctypedef int (*print_label_bridge_t)(int addr, int rw);

cdef struct jmp_targets_t:
    np.uint8_t discovered[256*256];
    label_storage_t *labels;

ctypedef int (*parse_func_t)(history_entry_t *, unsigned char *, unsigned int, unsigned int, jmp_targets_t *)

ctypedef int (*string_func_t)(history_entry_t *, char *, char *, int, jmp_targets_t *)
