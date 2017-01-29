from __future__ import division
import cython
import numpy as np
cimport numpy as np
from libc.stdio cimport printf
from libc.string cimport strncpy

cdef extern:
    int parse_instruction_c(char *wrap, int pc, char *src, int last_pc)


@cython.boundscheck(False)
@cython.wraparound(False)
def get_disassembled_chunk_fast(storage_wrapper, np.ndarray[char, ndim=1, mode="c"] binary_array, pc, last, index_of_pc):

    cdef np.ndarray storage_wrapper_array = storage_wrapper.storage
    cdef char *storage = storage_wrapper_array.data
    cdef int c_index = index_of_pc
    cdef char *binary = binary_array.data + c_index
    cdef int c_pc, c_last, count, line, max_lines
    cdef char out[80]

    c_pc = pc
    c_last = last
    line = storage_wrapper.row
    max_lines = storage_wrapper.num_rows

    # fast loop in C
    while c_pc < c_last and line < max_lines:
        count = parse_instruction_c(storage, c_pc, binary, c_last)
        strncpy(out, storage, 48)
        out[48] = '\n'
        out[49] = '\0'
        printf("%s\n", out)
        if count == 0:
            break
        c_pc += count
        c_index += count
        storage += count
        binary += count
        line += 1

    # get data back out in python vars
    pc = c_pc
    index_of_pc = c_index
    return pc, index_of_pc
