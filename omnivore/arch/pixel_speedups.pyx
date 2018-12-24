from __future__ import division
import cython
import numpy as np
cimport numpy as np

# from atrcopy; doesn't seem to be a way to import Python constants
# (although, to be fair, nothing in Python can be assumed to be a constant!)
cdef enum:
    user_bit_mask = 0x07
    data_style = 0x1
    not_user_bit_mask = 0xff ^ user_bit_mask
    diff_bit_mask = 0x10
    match_bit_mask = 0x20
    comment_bit_mask = 0x40
    selected_bit_mask = 0x80
    ignore_mask = not_user_bit_mask & (0xff ^ diff_bit_mask)
    invalid_style = 0xff


@cython.boundscheck(False)
@cython.wraparound(False)
def calc_rgb_from_color_indexes_naive(np.ndarray[np.uint8_t, ndim=2] color_indexes, np.ndarray[np.uint8_t, ndim=2] style_per_pixel, colors, empty_color_tuple):
    cdef int h = color_indexes.shape[0]
    cdef int w = color_indexes.shape[1]

    cdef np.uint8_t[:] color_indexes_flat = color_indexes.reshape(-1)
    cdef np.uint8_t[:] style_per_pixel_flat = style_per_pixel.reshape(-1)
    cdef np.ndarray[np.uint8_t, ndim=2] flat_image = np.empty([h * w, 3], dtype=np.uint8)

    cdef np.ndarray[np.uint8_t, ndim=2] color_registers = colors[0]
    cdef np.ndarray[np.uint8_t, ndim=2] h_colors = colors[1]
    cdef np.ndarray[np.uint8_t, ndim=2] m_colors = colors[2]
    cdef np.ndarray[np.uint8_t, ndim=2] c_colors = colors[3]
    cdef np.ndarray[np.uint8_t, ndim=2] d_colors = colors[4]
    cdef np.ndarray[np.uint8_t, ndim=1] empty_color = np.asarray(empty_color_tuple, dtype=np.uint8)

    cdef np.uint8_t color_index, style
    cdef int i
    for i in range(len(color_indexes_flat)):
        color_index = color_indexes_flat[i]
        style = style_per_pixel_flat[i]
        if style == invalid_style:
            flat_image[i] = empty_color
        elif style & ignore_mask == 0:
            flat_image[i] = color_registers[color_index]
        elif style & selected_bit_mask:
            flat_image[i] = h_colors[color_index]
        elif (style & user_bit_mask) > 0:
            flat_image[i] = d_colors[color_index]
        elif style & comment_bit_mask:
            flat_image[i] = c_colors[color_index]
        elif style & match_bit_mask:
            flat_image[i] = h_colors[color_index]
        else:  # not any of the above, which shouldn't happen
            flat_image[i] = (0xff, 0, 0xee)
    return flat_image.reshape((h, w, 3))


@cython.boundscheck(False)
@cython.wraparound(False)
def calc_rgb_from_color_indexes_better(np.ndarray[np.uint8_t, ndim=2] color_indexes, np.ndarray[np.uint8_t, ndim=2] style_per_pixel, colors, empty_color_tuple):
    cdef int h = color_indexes.shape[0]
    cdef int w = color_indexes.shape[1]

    cdef np.uint8_t[:] color_indexes_flat = color_indexes.reshape(-1)
    cdef np.uint8_t[:] style_per_pixel_flat = style_per_pixel.reshape(-1)
    cdef np.ndarray[np.uint8_t, ndim=2] flat_image = np.empty([h * w, 3], dtype=np.uint8)

    cdef np.ndarray[np.uint8_t, ndim=2] color_registers = colors[0]
    cdef np.ndarray[np.uint8_t, ndim=2] h_colors = colors[1]
    cdef np.ndarray[np.uint8_t, ndim=2] m_colors = colors[2]
    cdef np.ndarray[np.uint8_t, ndim=2] c_colors = colors[3]
    cdef np.ndarray[np.uint8_t, ndim=2] d_colors = colors[4]
    cdef np.ndarray[np.uint8_t, ndim=1] empty_color = np.asarray(empty_color_tuple, dtype=np.uint8)

    cdef np.uint8_t color_index, style, r, g, b
    cdef int i
    for i in range(len(color_indexes_flat)):
        color_index = color_indexes_flat[i]
        style = style_per_pixel_flat[i]
        if style == invalid_style:
            r = empty_color[0]
            g = empty_color[1]
            b = empty_color[2]
        elif style & ignore_mask == 0:
            r = color_registers[color_index, 0]
            g = color_registers[color_index, 1]
            b = color_registers[color_index, 2]
        elif style & selected_bit_mask:
            r = h_colors[color_index, 0]
            g = h_colors[color_index, 1]
            b = h_colors[color_index, 2]
        elif (style & user_bit_mask) > 0:
            r = d_colors[color_index, 0]
            g = d_colors[color_index, 1]
            b = d_colors[color_index, 2]
        elif style & comment_bit_mask:
            r = c_colors[color_index, 0]
            g = c_colors[color_index, 1]
            b = c_colors[color_index, 2]
        elif style & match_bit_mask:
            r = h_colors[color_index, 0]
            g = h_colors[color_index, 1]
            b = h_colors[color_index, 2]
        else:  # not any of the above, which shouldn't happen
            r = 0xff
            g = 0
            b = 0xee

        flat_image[i,0] = r
        flat_image[i,1] = g
        flat_image[i,2] = b
    return flat_image.reshape((h, w, 3))


@cython.boundscheck(False)
@cython.wraparound(False)
def calc_rgb_from_color_indexes_fast(np.ndarray[np.uint8_t, ndim=2] color_indexes, np.ndarray[np.uint8_t, ndim=2] style_per_pixel, colors, empty_color_tuple):
    cdef int h = color_indexes.shape[0]
    cdef int w = color_indexes.shape[1]

    cdef np.uint8_t[:] color_indexes_flat = color_indexes.reshape(-1)
    cdef np.uint8_t[:] style_per_pixel_flat = style_per_pixel.reshape(-1)
    cdef np.ndarray[np.uint8_t, ndim=2] flat_image = np.empty([h * w, 3], dtype=np.uint8)
    cdef np.uint8_t[:,:] flat_image_fast = flat_image

    cdef np.ndarray[np.uint8_t, ndim=2] color_registers = colors[0]
    cdef np.uint8_t[:,:] color_registers_fast = color_registers
    cdef np.ndarray[np.uint8_t, ndim=2] h_colors = colors[1]
    cdef np.uint8_t[:,:] h_colors_fast = h_colors
    cdef np.ndarray[np.uint8_t, ndim=2] m_colors = colors[2]
    cdef np.uint8_t[:,:] m_colors_fast = m_colors
    cdef np.ndarray[np.uint8_t, ndim=2] c_colors = colors[3]
    cdef np.uint8_t[:,:] c_colors_fast = c_colors
    cdef np.ndarray[np.uint8_t, ndim=2] d_colors = colors[4]
    cdef np.uint8_t[:,:] d_colors_fast = d_colors
    cdef np.uint8_t empty_r, empty_g, empty_b
    empty_r = empty_color_tuple[0]
    empty_g = empty_color_tuple[1]
    empty_b = empty_color_tuple[2]

    cdef np.uint8_t color_index, style, r, g, b
    cdef int i
    for i in range(len(color_indexes_flat)):
        color_index = color_indexes_flat[i]
        style = style_per_pixel_flat[i]
        if style == invalid_style:
            r = empty_r
            g = empty_g
            b = empty_b
        elif style & ignore_mask == 0:
            r = color_registers_fast[color_index, 0]
            g = color_registers_fast[color_index, 1]
            b = color_registers_fast[color_index, 2]
        elif style & selected_bit_mask:
            r = h_colors_fast[color_index, 0]
            g = h_colors_fast[color_index, 1]
            b = h_colors_fast[color_index, 2]
        elif (style & user_bit_mask) > 0:
            r = d_colors_fast[color_index, 0]
            g = d_colors_fast[color_index, 1]
            b = d_colors_fast[color_index, 2]
        elif style & comment_bit_mask:
            r = c_colors_fast[color_index, 0]
            g = c_colors_fast[color_index, 1]
            b = c_colors_fast[color_index, 2]
        elif style & match_bit_mask:
            r = h_colors_fast[color_index, 0]
            g = h_colors_fast[color_index, 1]
            b = h_colors_fast[color_index, 2]
        else:  # not any of the above, which shouldn't happen
            r = 0xff
            g = 0
            b = 0xee

        flat_image_fast[i,0] = r
        flat_image_fast[i,1] = g
        flat_image_fast[i,2] = b
    return flat_image.reshape((h, w, 3))


@cython.boundscheck(False)
@cython.wraparound(False)
def calc_rgb_from_color_indexes_fast_optimize(np.ndarray[np.uint8_t, ndim=2] color_indexes, np.ndarray[np.uint8_t, ndim=2] style_per_pixel, colors, empty_color_tuple):
    cdef int h = color_indexes.shape[0]
    cdef int w = color_indexes.shape[1]

    cdef np.uint8_t[:] color_indexes_flat = color_indexes.reshape(-1)
    cdef np.uint8_t[:] style_per_pixel_flat = style_per_pixel.reshape(-1)
    cdef np.ndarray[np.uint8_t, ndim=2] flat_image = np.empty([h * w, 3], dtype=np.uint8)
    cdef np.uint8_t[:,:] flat_image_fast = flat_image

    cdef np.ndarray[np.uint8_t, ndim=2] color_registers = colors[0]
    cdef np.uint8_t[::1] color_registers_fast_temp = color_registers
    cdef np.uint8_t[:] color_registers_fast = color_registers_fast_temp
    cdef np.ndarray[np.uint8_t, ndim=2] h_colors = colors[1]
    cdef np.uint8_t[:,:] h_colors_fast = h_colors
    cdef np.ndarray[np.uint8_t, ndim=2] m_colors = colors[2]
    cdef np.uint8_t[:,:] m_colors_fast = m_colors
    cdef np.ndarray[np.uint8_t, ndim=2] c_colors = colors[3]
    cdef np.uint8_t[:,:] c_colors_fast = c_colors
    cdef np.ndarray[np.uint8_t, ndim=2] d_colors = colors[4]
    cdef np.uint8_t[:,:] d_colors_fast = d_colors
    cdef np.uint8_t empty_r, empty_g, empty_b
    empty_r = empty_color_tuple[0]
    empty_g = empty_color_tuple[1]
    empty_b = empty_color_tuple[2]

    cdef np.uint8_t style, r, g, b
    cdef int i, color_index
    for i in range(len(color_indexes_flat)):
        color_index = color_indexes_flat[i] * 3
        style = style_per_pixel_flat[i]
        if style == invalid_style:
            r = empty_r
            g = empty_g
            b = empty_b
        elif style & ignore_mask == 0:
            r = color_registers_fast[color_index]
            color_index += 1
            g = color_registers_fast[color_index]
            color_index += 1
            b = color_registers_fast[color_index]
        elif style & selected_bit_mask:
            r = h_colors_fast[color_index, 0]
            g = h_colors_fast[color_index, 1]
            b = h_colors_fast[color_index, 2]
        elif (style & user_bit_mask) > 0:
            r = d_colors_fast[color_index, 0]
            g = d_colors_fast[color_index, 1]
            b = d_colors_fast[color_index, 2]
        elif style & comment_bit_mask:
            r = c_colors_fast[color_index, 0]
            g = c_colors_fast[color_index, 1]
            b = c_colors_fast[color_index, 2]
        elif style & match_bit_mask:
            r = h_colors_fast[color_index, 0]
            g = h_colors_fast[color_index, 1]
            b = h_colors_fast[color_index, 2]
        else:  # not any of the above, which shouldn't happen
            r = 0xff
            g = 0
            b = 0xee

        flat_image_fast[i,0] = r
        flat_image_fast[i,1] = g
        flat_image_fast[i,2] = b
    return flat_image.reshape((h, w, 3))


# The best seems to be better

calc_rgb_from_color_indexes = calc_rgb_from_color_indexes_better
