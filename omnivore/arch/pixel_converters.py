""" Pixel converters

ByteValidator: change byte index list into rectangular grid
ColorIndexGenerator: bytes to pixel color indexes

calc_rgb_from_color_indexes: create RGB array given pixels, styles, and RGB colro mappings


Utility classes/functions to convert byte representations of pixel data into
grids of color register indexes.

Color register indexes are byte values, each byte calculated from the integer
value of the bits making up the corresponding pixel. For example, Antic mode D
(graphics 7) uses 2 bits per pixel, laid out into 4 pixels:

  bit7 bit6 | bit5 bit4 | bit3 bit2 | bit1 bit0

where the color register indexes for each of the pixels is computed by:

  bit7*2 + bit6
  bit5*2 + bit4
  bit3*2 + bit2
  bit1*2 + bit0

Each byte would therefore contain values in the range of [0, 3].

This conversion is device independent; the code that displays pixels on screen will take these values and convert them to the color values referred to by these indexes.
"""
import numpy as np

from atrip import style_bits
ignore_mask = style_bits.not_user_bit_mask & (0xff ^ style_bits.diff_bit_mask)
invalid_style = 0xff

from sawx.utils.permute import bit_reverse_table


class ConverterBase:
    name = "base"
    ui_name = "Base"

    pixels_per_byte = 8
    bitplanes = 1

    scale_width = 1
    scale_height = 1

    @classmethod
    def validate_pixels_per_row(cls, pixels_per_row):
        return (pixels_per_row // cls.pixels_per_byte) * cls.pixels_per_byte

    @classmethod
    def calc_bytes_per_row(cls, pixels_per_row):
        return (pixels_per_row + cls.pixels_per_byte - 1) // cls.pixels_per_byte

    @classmethod
    def calc_grid_height(cls, num_byte_values, bytes_per_row):
        return (num_byte_values + bytes_per_row - 1) // bytes_per_row

    def calc_color_index_grid(self, byte_values, style, bytes_per_row):
        nr = len(byte_values) // bytes_per_row
        pixels = self.calc_pixels(byte_values, bytes_per_row)
        style_per_pixel = self.calc_style_per_pixel(pixels, style)
        return pixels.reshape((-1, bytes_per_row * self.pixels_per_byte)), style_per_pixel.reshape((-1, bytes_per_row * self.pixels_per_byte))


class Converter1bpp(ConverterBase):
    name = "1bpp"
    ui_name = "1 bit per pixel"
    
    pixels_per_byte = 8

    def calc_pixels(self, byte_values, bytes_per_row):
        bits = np.unpackbits(byte_values)
        pixels = bits.reshape((-1, 8))
        return pixels

    def calc_style_per_pixel(self, pixels, style):
        h, w = pixels.shape
        stack = np.empty((len(style), 8), dtype=style.dtype)
        stack[:,0] = style
        stack[:,1] = style
        stack[:,2] = style
        stack[:,3] = style
        stack[:,4] = style
        stack[:,5] = style
        stack[:,6] = style
        stack[:,7] = style
        return stack.reshape((h, w))


class Converter2bpp(ConverterBase):
    name = "2bpp"
    ui_name = "2 bits per pixel"
    
    pixels_per_byte = 4

    def calc_pixels(self, byte_values, bytes_per_row):
        bits = np.unpackbits(byte_values)
        bits = bits.reshape((-1, 8))
        pixels = np.empty((bits.shape[0], 4), dtype=np.uint8)
        pixels[:,0] = bits[:,0] * 2 + bits[:,1]
        pixels[:,1] = bits[:,2] * 2 + bits[:,3]
        pixels[:,2] = bits[:,4] * 2 + bits[:,5]
        pixels[:,3] = bits[:,6] * 2 + bits[:,7]
        return pixels

    def calc_style_per_pixel(self, pixels, style):
        h, w = pixels.shape
        stack = np.empty((len(style), 4), dtype=style.dtype)
        stack[:,0] = style
        stack[:,1] = style
        stack[:,2] = style
        stack[:,3] = style
        return stack.reshape((h, w))


class Converter4bpp(ConverterBase):
    name = "4bpp"
    ui_name = "4 bits per pixel"
    
    pixels_per_byte = 2

    def calc_pixels(self, byte_values, bytes_per_row):
        bits = np.unpackbits(byte_values)
        bits = bits.reshape((-1, 8))
        pixels = np.empty((bits.shape[0], 2), dtype=np.uint8)
        pixels[:,0] = bits[:,0] * 8 + bits[:,1] * 4 + bits[:,2] * 2 + bits[:,3]
        pixels[:,1] = bits[:,4] * 8 + bits[:,5] * 4 + bits[:,6] * 2 + bits[:,7]
        return pixels

    def calc_style_per_pixel(self, pixels, style):
        h, w = pixels.shape
        stack = np.empty((len(style), 2), dtype=style.dtype)
        stack[:,0] = style
        stack[:,1] = style
        return stack.reshape((h, w))


class Converter8bpp(ConverterBase):
    name = "8bpp"
    ui_name = "8 bits per pixel"
    
    pixels_per_byte = 1

    def calc_pixels(self, byte_values, bytes_per_row):
        return byte_values.reshape((-1, 1))

    def calc_style_per_pixel(self, pixels, style):
        h, w = pixels.shape
        style.reshape((h, w))
        return style

    def calc_valid_byte_grid(self, byte_values, style, grid_start_index, data_start_index, num_bytes, byte_width):
        num_prepend = max(data_start_index - grid_start_index, 0)
        _, num_extra = divmod(num_prepend + num_bytes, byte_width)
        if num_extra > 0:
            num_append = byte_width - num_extra
        else:
            num_append = 0
        if num_prepend + num_append > 0:
            total = num_prepend + num_append + num_bytes
            b = np.empty(total, dtype=byte_values.dtype)
            b[0:num_prepend] = 0
            b[num_prepend:num_prepend + num_bytes] = byte_values
            b[num_prepend + num_bytes:-1] = 0
            s[0:num_prepend] = 0
            s[num_prepend:num_prepend + num_bytes] = style
            s[num_prepend + num_bytes:-1] = 0
        else:
            b = byte_values
            s = style
        return b.reshape((-1, byte_width), s.reshape((-1, byte_width)))


class AnticB(Converter1bpp):
    name = "antic_b"
    ui_name = "ANTIC Mode B (Gr 6, 1bpp)"

    scale_width = 2
    scale_height = 2


class AnticC(AnticB):
    name = "antic_c"
    ui_name = "ANTIC Mode C (Gr 6+, 1bpp)"

    scale_width = 2
    scale_height = 1


class AnticD(Converter2bpp):
    name = "antic_d"
    ui_name = "ANTIC Mode D (Gr 7, 2bpp)"

    scale_width = 2
    scale_height = 2


class AnticE(AnticD):
    name = "antic_e"
    ui_name = "ANTIC Mode E (Gr 7+, 2bpp)"

    scale_width = 2
    scale_height = 1


class AnticNormalPlayer(AnticC):
    name = "Player/Missile, normal width"
    scale_width = 2


class AnticDoublePlayer(AnticNormalPlayer):
    name = "Player/Missile, double width"
    scale_width = 4


class AnticQuadPlayer(AnticNormalPlayer):
    name = "Player/Missile, quad width"
    scale_width = 8


def calc_rgb_from_color_indexes_python(color_indexes, style_per_pixel, colors, empty_color):
    h, w = color_indexes.shape
    color_indexes = color_indexes.reshape(-1)
    style_per_pixel = style_per_pixel.reshape(-1)
    flat_image = np.empty((h * w, 3), dtype=np.uint8)
    color_registers, h_colors, m_colors, c_colors, d_colors = colors
    for i in range(len(color_indexes)):
        color_index = color_indexes[i]
        style = style_per_pixel[i]
        if style == invalid_style:
            flat_image[i] = empty_color
        elif style & ignore_mask == 0:
            flat_image[i] = color_registers[color_index]
        elif style & style_bits.selected_bit_mask:
            flat_image[i] = h_colors[color_index]
        elif (style & style_bits.user_bit_mask) > 0:
            flat_image[i] = d_colors[color_index]
        elif style & style_bits.comment_bit_mask:
            flat_image[i] = h_colors[color_index]
        elif style & style_bits.match_bit_mask:
            flat_image[i] = h_colors[color_index]
        else:
            flat_image[i] = (0xff, 0, 0xee)  # not any of the above?
    return flat_image.reshape((h, w, 3))

try:
    from . import pixel_speedups
    calc_rgb_from_color_indexes = pixel_speedups.calc_rgb_from_color_indexes
except ImportError:
    calc_rgb_from_color_indexes = calc_rgb_from_color_indexes_python
