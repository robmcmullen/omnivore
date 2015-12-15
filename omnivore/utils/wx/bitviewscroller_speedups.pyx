from __future__ import division
import cython
import numpy as np
cimport numpy as np


@cython.boundscheck(False)
@cython.wraparound(False)
def get_numpy_memory_map_image(np.ndarray[np.uint8_t, ndim=2] bytes, int start_byte, int end_byte, int bytes_per_row, int num_rows, int start_col, int num_cols, background_color, anchor_start, anchor_end, selected_color):
    cdef int num_rows_with_data = (end_byte - start_byte + bytes_per_row - 1) // bytes_per_row
    cdef np.uint8_t bgr = background_color[0]
    cdef np.uint8_t bgg = background_color[1]
    cdef np.uint8_t bgb = background_color[2]
    cdef np.uint8_t sr = selected_color[0]
    cdef np.uint8_t sg = selected_color[1]
    cdef np.uint8_t sb = selected_color[2]
    
    cdef int end_row = min(num_rows_with_data, num_rows)
    cdef int end_col = min(bytes_per_row, start_col + num_cols)
    cdef int width = end_col - start_col
    cdef int height = num_rows_with_data
    cdef np.ndarray[np.uint8_t, ndim=3] array = np.empty([height, width, 3], dtype=np.uint8)
    cdef int start = anchor_start
    cdef int end = anchor_end

    cdef int y = 0
    cdef int e = start_byte
    cdef int x, i, j
    cdef np.uint8_t bw = 0xff
    cdef np.uint8_t c
    cdef np.uint16_t h
    for j in range(end_row):
        x = 0
        for i in range(start_col, end_col):
            if e + i >= end_byte:
                array[y,x,0] = bgr
                array[y,x,1] = bgg
                array[y,x,2] = bgb
            else:
                c = bytes[j, i] ^ bw
                if start <= e + i < end:
                    h = sr * c >> 8
                    array[y,x,0] = h
                    h = sg * c >> 8
                    array[y,x,1] = h
                    h = sb * c >> 8
                    array[y,x,2] = h
                else:
                    array[y,x,0] = c
                    array[y,x,1] = c
                    array[y,x,2] = c
            x += 1
        y += 1
        e += bytes_per_row

    return array
