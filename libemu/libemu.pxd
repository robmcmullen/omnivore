cimport numpy as np

cdef struct op_record_t:
    np.uint8_t type;
    np.uint8_t num;
    np.uint8_t payload_byte0;
    np.uint8_t payload_byte1;

cdef struct op_history_t:
    np.uint32_t malloc_size;
    np.uint32_t frame_number;
    np.uint32_t max_records;
    np.uint32_t num_records;
    np.uint32_t max_lookup;
    np.uint32_t num_lookup;

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

ctypedef (op_record_t *) (*parse_func_t)(op_record_t *, unsigned char *, unsigned int, unsigned int, jmp_targets_t *)

ctypedef int (*string_func_t)(op_record_t *, char *, char *, int, jmp_targets_t *)
