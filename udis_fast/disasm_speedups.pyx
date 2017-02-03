from __future__ import division
import cython
import numpy as np
cimport numpy as np

ctypedef int (*parse_func_t)(char *, int, char *, int, np.uint16_t *)

cdef extern:
    int parse_instruction_c_LL(char *wrap, int pc, char *src, int last_pc, np.uint16_t *labels)
    int parse_instruction_c_LU(char *wrap, int pc, char *src, int last_pc, np.uint16_t *labels)
    int parse_instruction_c_UL(char *wrap, int pc, char *src, int last_pc, np.uint16_t *labels)
    int parse_instruction_c_UU(char *wrap, int pc, char *src, int last_pc, np.uint16_t *labels)


@cython.boundscheck(False)
@cython.wraparound(False)
def get_disassembled_chunk_fast(storage_wrapper, np.ndarray[char, ndim=1, mode="c"] binary_array, pc, last, index_of_pc, mnemonic_lower, hex_lower):

    cdef np.ndarray storage_wrapper_array = storage_wrapper.storage
    cdef itemsize = storage_wrapper_array.itemsize
    cdef char *storage = storage_wrapper_array.data
    cdef int c_index = index_of_pc
    cdef char *binary = binary_array.data + c_index
    cdef int c_pc, c_last, count, row, max_rows, i
    cdef np.ndarray[np.uint16_t, ndim=1] labels_array = storage_wrapper.labels
    cdef np.uint16_t *labels = <np.uint16_t *>labels_array.data
    cdef np.ndarray[np.uint32_t, ndim=1] index_array = storage_wrapper.index
    cdef np.uint32_t *index = <np.uint32_t *>index_array.data
    cdef parse_func_t parse_func

    c_pc = pc
    c_last = last
    row = storage_wrapper.row
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
    while c_pc < c_last and row < max_rows:
        count = parse_func(storage, c_pc, binary, c_last, labels)
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
        c_pc += count
        c_index += count
        storage += itemsize
        binary += count
        row += 1

    # get data back out in python vars
    pc = c_pc
    index_of_pc = c_index
    storage_wrapper.row = row
    return pc, index_of_pc
