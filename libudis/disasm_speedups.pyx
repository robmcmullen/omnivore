from __future__ import division
import cython
import numpy as np
cimport numpy as np

ctypedef int (*parse_func_t)(char *, char *, int, int, np.uint16_t *, char *, int)

cdef extern:
    int parse_instruction_c_LL(char *wrap, char *src, int pc, int last_pc, np.uint16_t *labels, char *instructions, int strpos)
    int parse_instruction_c_LU(char *wrap, char *src, int pc, int last_pc, np.uint16_t *labels, char *instructions, int strpos)
    int parse_instruction_c_UL(char *wrap, char *src, int pc, int last_pc, np.uint16_t *labels, char *instructions, int strpos)
    int parse_instruction_c_UU(char *wrap, char *src, int pc, int last_pc, np.uint16_t *labels, char *instructions, int strpos)


@cython.boundscheck(False)
@cython.wraparound(False)
def get_disassembled_chunk_fast(storage_wrapper, np.ndarray[char, ndim=1, mode="c"] binary_array, pc, last, index_of_pc, mnemonic_lower, hex_lower):

    cdef np.ndarray metadata_array = storage_wrapper.metadata
    cdef itemsize = metadata_array.itemsize
    cdef row = storage_wrapper.row
    cdef char *metadata = metadata_array.data
    cdef int c_index = index_of_pc
    cdef char *binary = binary_array.data + c_index
    cdef int c_pc, c_last, count, max_rows, i
    cdef np.ndarray[np.uint16_t, ndim=1] labels_array = storage_wrapper.labels
    cdef np.uint16_t *labels = <np.uint16_t *>labels_array.data
    cdef np.ndarray[np.uint32_t, ndim=1] index_array = storage_wrapper.index
    cdef np.uint32_t *index = <np.uint32_t *>index_array.data + c_index
    cdef parse_func_t parse_func
    cdef np.ndarray instructions_array = storage_wrapper.instructions
    cdef char *instructions = instructions_array.data
    cdef int strpos = storage_wrapper.last_strpos
    cdef int max_strpos = storage_wrapper.max_strpos
    cdef int retval

    metadata += (row * itemsize)
    instructions += strpos
    c_pc = pc
    c_last = last
    max_rows = storage_wrapper.num_rows
    if mnemonic_lower:
        if hex_lower:
            parse_func = parse_instruction_c_LL
        else:
            parse_func = parse_instruction_c_LU
    else:
        if hex_lower:
            parse_func = parse_instruction_c_UL
        else:
            parse_func = parse_instruction_c_UU

    # fast loop in C
    while c_pc < c_last and row < max_rows and strpos < max_strpos:
        count = parse_func(metadata, binary, c_pc, c_last, labels, instructions, strpos)
        if count == 0:
            break
        elif count == 1:
            index[0] = row
            index += 1
        elif count == 2:
            index[0] = row
            index += 1
            index[0] = row
            index += 1
        elif count == 3:
            index[0] = row
            index += 1
            index[0] = row
            index += 1
            index[0] = row
            index += 1
        elif count == 4:
            index[0] = row
            index += 1
            index[0] = row
            index += 1
            index[0] = row
            index += 1
            index[0] = row
            index += 1
        else:
            for i in range(count):
                index[0] = row
                index += 1
        strlen = <int>metadata[6]
        c_pc += count
        c_index += count
        metadata += itemsize
        binary += count
        strpos += strlen
        instructions += strlen
        row += 1

    # get data back out in python vars
    pc = c_pc
    index_of_pc = c_index
    storage_wrapper.row = row
    storage_wrapper.last_strpos = strpos
    return pc, index_of_pc
