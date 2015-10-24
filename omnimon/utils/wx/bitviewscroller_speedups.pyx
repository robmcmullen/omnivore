from __future__ import division
import cython
import numpy as np
cimport numpy as np


@cython.boundscheck(False)
def get_numpy_memory_map_image(np.ndarray[np.uint8_t, ndim=2] bytes, int start_byte, int end_byte, int bytes_per_row, int num_rows, int start_col, int num_cols, background_color, selected_color):
    cdef int num_rows_with_data = (end_byte - start_byte + bytes_per_row - 1) // bytes_per_row
    cdef int width = num_cols
    cdef int height = num_rows_with_data
    cdef np.uint8_t bgr = background_color[0]
    cdef np.uint8_t bgg = background_color[1]
    cdef np.uint8_t bgb = background_color[2]
    cdef np.uint8_t sr = selected_color[0]
    cdef np.uint8_t sg = selected_color[1]
    cdef np.uint8_t sb = selected_color[2]
    
    cdef np.ndarray[np.uint8_t, ndim=3] array = np.empty([height, width, 3], dtype=np.uint8)
    cdef np.uint8_t[:,:,:] array_view = array
    array_view[:,:,0] = bgr
    array_view[:,:,1] = bgg
    array_view[:,:,2] = bgb
    
    cdef int end_row = min(num_rows_with_data, num_rows)
    cdef int end_col = min(bytes_per_row, start_col + num_cols)
    cdef int y = 0
    cdef int e = start_byte
    cdef int x, i, j
    cdef np.uint8_t c
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
