from __future__ import division
import cython
import numpy as np
cimport numpy as np


@cython.boundscheck(False)
@cython.wraparound(False)
def get_numpy_memory_map_image(segment_viewer, np.ndarray[np.uint8_t, ndim=2] bytes, np.ndarray[np.uint8_t, ndim=2] style, int start_byte, int end_byte, int bytes_per_row, int num_rows, int start_col, int num_cols):
    cdef int num_rows_with_data = (end_byte - start_byte + bytes_per_row - 1) // bytes_per_row
    cdef np.uint8_t bgr = segment_viewer.preferences.background_color[0]
    cdef np.uint8_t bgg = segment_viewer.preferences.background_color[1]
    cdef np.uint8_t bgb = segment_viewer.preferences.background_color[2]
    cdef np.uint8_t sr = segment_viewer.preferences.highlight_background_color[0]
    cdef np.uint8_t sg = segment_viewer.preferences.highlight_background_color[1]
    cdef np.uint8_t sb = segment_viewer.preferences.highlight_background_color[2]
    
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


# Fast font rendering. As an optimization, only renders complete rectangles.
# The first and last row may be partial depending on the start offset of the
# segment, but these now have to be rendered separately in their own (single
# row) rectangle
@cython.boundscheck(False)
@cython.wraparound(False)
def get_numpy_font_map_image(segment_viewer, antic_font, np.ndarray[np.uint8_t, ndim=2] bytes, np.ndarray[np.uint8_t, ndim=2] style, int start_byte, int end_byte, int bytes_per_row, int num_rows, int start_col, int num_cols):
    cdef int char_w = antic_font.char_w
    cdef int char_h = antic_font.char_h
    cdef int end_col = min(bytes_per_row, start_col + num_cols)
    cdef int width = char_w * num_cols
    cdef int height = num_rows * char_h
    cdef np.ndarray[np.uint8_t, ndim=3] array = np.empty([height, width, 3], dtype=np.uint8)
    cdef np.uint8_t[:,:,:] fast_array = array

    cdef int y = 0
    cdef int x, i, j
    cdef np.ndarray[np.uint8_t, ndim=4] f = antic_font.normal_font
    cdef np.uint8_t[:,:,:,:] fast_f = f
    cdef np.ndarray[np.uint8_t, ndim=4] fh = antic_font.highlight_font
    cdef np.uint8_t[:,:,:,:] fast_fh = fh
    cdef np.ndarray[np.uint8_t, ndim=4] fd = antic_font.data_font
    cdef np.uint8_t[:,:,:,:] fast_fd = fd
    cdef np.ndarray[np.uint8_t, ndim=4] fm = antic_font.match_font
    cdef np.uint8_t[:,:,:,:] fast_fm = fm
    cdef np.ndarray[np.uint8_t, ndim=4] fc = antic_font.comment_font
    cdef np.uint8_t[:,:,:,:] fast_fc = fc
    cdef np.uint8_t s, c
    cdef np.ndarray[np.uint8_t] mapping = segment_viewer.machine.font_mapping.font_mapping
    for j in range(num_rows):
        x = 0
        for i in range(start_col, start_col + num_cols):
            c = mapping[bytes[j, i]]
            s = style[j, i]
            if s & 0x80:
                fast_array[y:y+char_h,x:x+char_w,:] = fast_fh[c]
            elif s & 0x20:
                fast_array[y:y+char_h,x:x+char_w,:] = fast_fm[c]
            elif s & 0x40:
                fast_array[y:y+char_h,x:x+char_w,:] = fast_fc[c]
            elif s & 0x07:
                fast_array[y:y+char_h,x:x+char_w,:] = fast_fd[c]
            else:
                fast_array[y:y+char_h,x:x+char_w,:] = fast_f[c]
            x += char_w
        y += char_h

    return array


@cython.boundscheck(False)
@cython.wraparound(False)
def get_numpy_memory_access_image(segment_viewer, int bytes_per_row, int num_rows, int count, np.ndarray[np.uint8_t, ndim=2] access_value, np.ndarray[np.uint8_t, ndim=2] access_type, int start_col, int num_cols):

    bg = segment_viewer.preferences.highlight_background_color
    cdef np.uint8_t sr = bg[0]
    cdef np.uint8_t sg = bg[1]
    cdef np.uint8_t sb = bg[2]
    
    cdef int end_col = min(bytes_per_row, start_col + num_cols)
    cdef int width = end_col - start_col
    cdef np.ndarray[np.uint8_t, ndim=3] array = np.empty([num_rows, width, 3], dtype=np.uint8)

    cdef int y = 0
    cdef int x, i, j, r, g, b
    cdef np.uint8_t c, s
    cdef np.uint16_t h
    for j in range(num_rows):
        x = 0
        for i in range(start_col, end_col):
            c = access_value[j, i]
            s = access_type[j, i]
            if s & 1:
                #define ACCESS_TYPE_READ 1
                if c == 255:
                    r = 255
                    g = c
                    b = 255
                else:
                    r = 0
                    g = c
                    b = 0
            elif s & 2:
                #define ACCESS_TYPE_WRITE 2
                if c == 255:
                    r = c
                    g = 255
                    b = 255
                else:
                    r = c
                    g = 0
                    b = 0
            elif s & 4:
                #define ACCESS_TYPE_EXECUTE 4
                if c == 255:
                    r = c
                    g = c
                    b = 255
                else:
                    r = c
                    g = c
                    b = 0
            elif s & 8:
                #define ACCESS_TYPE_VIDEO 8
                if c == 255:
                    r = 255
                    g = 255
                    b = c
                else:
                    r = 0
                    g = 0
                    b = c
            elif s & 16:
                #define ACCESS_TYPE_DISPLAY_LIST 16
                if c == 255:
                    r = c
                    g = 255
                    b = c
                else:
                    r = c
                    g = 0
                    b = c
            else:
                r = 0
                g = 0
                b = 0

            if s & 0x80:
                r = (sr * r) >> 8
                g = (sr * g) >> 8
                b = (sr * b) >> 8


            array[y,x,0] = r
            array[y,x,1] = g
            array[y,x,2] = b
            x += 1
        y += 1

    return array
