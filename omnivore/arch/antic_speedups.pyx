from __future__ import division
import cython
import numpy as np
cimport numpy as np


@cython.boundscheck(False)
@cython.wraparound(False)
def get_numpy_memory_map_image(m, np.ndarray[np.uint8_t, ndim=2] bytes, np.ndarray[np.uint8_t, ndim=2] style, int start_byte, int end_byte, int bytes_per_row, int num_rows, int start_col, int num_cols):
    cdef int num_rows_with_data = (end_byte - start_byte + bytes_per_row - 1) // bytes_per_row
    cdef np.uint8_t bgr = m.background_color[0]
    cdef np.uint8_t bgg = m.background_color[1]
    cdef np.uint8_t bgb = m.background_color[2]
    cdef np.uint8_t sr = m.highlight_color[0]
    cdef np.uint8_t sg = m.highlight_color[1]
    cdef np.uint8_t sb = m.highlight_color[2]
    
    cdef int end_row = min(num_rows_with_data, num_rows)
    cdef int end_col = min(bytes_per_row, start_col + num_cols)
    cdef int width = end_col - start_col
    cdef int height = num_rows_with_data
    cdef np.ndarray[np.uint8_t, ndim=3] array = np.empty([height, width, 3], dtype=np.uint8)

    cdef int y = 0
    cdef int e = start_byte
    cdef int x, i, j
    cdef np.uint8_t bw = 0xff
    cdef np.uint8_t c, s
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
                s = style[j, i]
                if s & 0x80:
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

@cython.boundscheck(False)
@cython.wraparound(False)
def get_numpy_font_map_image(m, np.ndarray[np.uint8_t, ndim=2] bytes, np.ndarray[np.uint8_t, ndim=2] style, int start_byte, int end_byte, int bytes_per_row, int num_rows, int start_col, int num_cols):
    cdef int num_rows_with_data = (end_byte - start_byte + bytes_per_row - 1) // bytes_per_row
    cdef np.uint8_t bgr = m.background_color[0]
    cdef np.uint8_t bgg = m.background_color[1]
    cdef np.uint8_t bgb = m.background_color[2]
    
    cdef int end_col = min(bytes_per_row, start_col + num_cols)
    cdef int width = m.antic_font.char_w * num_cols
    cdef int height = num_rows * m.antic_font.char_h
    cdef np.ndarray[np.uint8_t, ndim=3] array = np.empty([height, width, 3], dtype=np.uint8)
    cdef np.uint8_t[:,:,:] fast_array = array

    cdef int y = 0
    cdef int e = start_byte
    cdef int x, i, j
    cdef np.ndarray[np.uint8_t, ndim=4] f = m.antic_font.normal_font
    cdef np.uint8_t[:,:,:,:] fast_f = f
    cdef np.ndarray[np.uint8_t, ndim=4] fh = m.antic_font.highlight_font
    cdef np.uint8_t[:,:,:,:] fast_fh = fh
    cdef np.ndarray[np.uint8_t, ndim=4] fm = m.antic_font.match_font
    cdef np.uint8_t[:,:,:,:] fast_fm = fm
    cdef np.ndarray[np.uint8_t, ndim=4] fc = m.antic_font.comment_font
    cdef np.uint8_t[:,:,:,:] fast_fc = fc
    cdef np.uint8_t s
    cdef np.ndarray[np.uint8_t] mapping = m.font_mapping.font_mapping
    for j in range(num_rows):
        x = 0
        for i in range(start_col, start_col + num_cols):
            if e + i >= end_byte or i >= end_col:
                fast_array[y:y+8,x:x+8,0] = bgr
                fast_array[y:y+8,x:x+8,1] = bgg
                fast_array[y:y+8,x:x+8,2] = bgb
            else:
                c = mapping[bytes[j, i]]
                s = style[j, i]
                if s & 0x80:
                    fast_array[y:y+8,x:x+8,:] = fast_fh[c]
                elif s & 1:
                    fast_array[y:y+8,x:x+8,:] = fast_fm[c]
                elif s & 2:
                    fast_array[y:y+8,x:x+8,:] = fast_fc[c]
                else:
                    fast_array[y:y+8,x:x+8,:] = fast_f[c]
            x += 8
        y += 8
        e += bytes_per_row

    return array
