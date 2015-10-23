from __future__ import division
import numpy as np
cimport numpy as np


def get_numpy_memory_map_image(np.ndarray[np.uint8_t, ndim=2] bytes, int start_byte, int end_byte, int bytes_per_row, int num_rows, int start_col, int num_cols, background_color, selected_color):
    cdef int num_rows_with_data = (end_byte - start_byte + bytes_per_row - 1) // bytes_per_row
    cdef int width = num_cols
    cdef int height = num_rows_with_data
    cdef int bgr = background_color[0]
    cdef int bgg = background_color[1]
    cdef int bgb = background_color[2]
    cdef int sr = selected_color[0]
    cdef int sg = selected_color[1]
    cdef int sb = selected_color[2]
    
    cdef np.ndarray array = np.empty((height, width, 3), dtype=np.uint8)
    array[:,:,0] = bgr
    array[:,:,1] = bgg
    array[:,:,2] = bgb
    
    cdef int end_row = min(num_rows_with_data, num_rows)
    cdef int end_col = min(bytes_per_row, start_col + num_cols)
    cdef int y = 0
    cdef int e = start_byte
    cdef int x, i, j
    for j in range(end_row):
        x = 0
        for i in range(start_col, end_col):
            if e + i >= end_byte:
                break
            c = bytes[j, i]
            array[y,x,0] = c
            array[y,x,1] = c
            array[y,x,2] = c
            x += 1
        y += 1
        e += bytes_per_row

    return array
