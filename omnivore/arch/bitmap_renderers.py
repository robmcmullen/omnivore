import numpy as np

import wx

from atrip import style_bits

from sawx.utils.permute import bit_reverse_table
from sawx.utils.nputil import intscale, intwscale, intwscale_font

from atrip.machines import atari8bit
from . import colors
try:
    from . import antic_speedups as speedups
except ImportError:
    speedups = None

import logging
log = logging.getLogger(__name__)


class BaseRenderer(object):
    name = "base"
    scale_width = 1
    scale_height = 1
    pixels_per_byte = 8
    bitplanes = 1
    ignore_mask = style_bits.not_user_bit_mask & (0xff ^ style_bits.diff_bit_mask)

    def __str__(self):
        return self.name

    def __eq__(self, other):
        try:
            return other is not None and self.name == other.name and self.pixels_per_byte == other.pixels_per_byte and self.bitplanes == other.bitplanes
        except AttributeError:
            pass
        return False

    # to be usable in dicts, py3 needs __hash__ defined if __eq__ is defined
    def __hash__(self):
        return id(self)

    def validate_bytes_per_row(self, bytes_per_row):
        return bytes_per_row

    def get_colors(self, segment_viewer, registers):
        color_registers = [segment_viewer.color_registers[r] for r in registers]
        log.debug(f"get_colors: {color_registers} from {segment_viewer}")
        h_colors = colors.get_blended_color_registers(color_registers, segment_viewer.preferences.highlight_background_color)
        m_colors = colors.get_blended_color_registers(color_registers, segment_viewer.preferences.match_background_color)
        c_colors = colors.get_blended_color_registers(color_registers, segment_viewer.preferences.comment_background_color)
        d_colors = colors.get_dimmed_color_registers(color_registers, segment_viewer.preferences.background_color, segment_viewer.preferences.data_background_color)
        return color_registers, h_colors, m_colors, c_colors, d_colors

    def reshape(self, bitimage, bytes_per_row, nr):
        # source array 'bitimage' in the shape of (size, w, 3)
        h, w, colors = bitimage.shape
        # create a new image with pixels in the correct aspect ratio
        output = bitimage.reshape((nr, self.pixels_per_byte * bytes_per_row, 3))
        output = intscale(output, self.scale_height, self.scale_width)
        log.debug("bitimage: %d,%d,%d; ppb=%d bpr=%d, output=%s" % (h, w, colors, self.pixels_per_byte * self.scale_width, bytes_per_row, str(output.shape)))
        return output

    def calc_style_per_pixel_1bpp(self, style):
        stack = np.empty((len(style), 8), dtype=style.dtype)
        stack[:,0] = style
        stack[:,1] = style
        stack[:,2] = style
        stack[:,3] = style
        stack[:,4] = style
        stack[:,5] = style
        stack[:,6] = style
        stack[:,7] = style
        return stack

    def calc_style_per_pixel_2bpp(self, style):
        stack = np.empty((len(style), 4), dtype=style.dtype)
        stack[:,0] = style
        stack[:,1] = style
        stack[:,2] = style
        stack[:,3] = style
        return stack

    def calc_style_per_pixel_4bpp(self, style):
        stack = np.empty((len(style), 2), dtype=style.dtype)
        stack[:,0] = style
        stack[:,1] = style
        return stack

    def calc_style_per_pixel(self, style):
        if self.pixels_per_byte == 1:
            return style
        elif self.pixels_per_byte == 2:
            return self.calc_style_per_pixel_4bpp(style)
        elif self.pixels_per_byte == 4:
            return self.calc_style_per_pixel_2bpp(style)
        elif self.pixels_per_byte == 8:
            return self.calc_style_per_pixel_1bpp(style)

    def get_2bpp(self, segment_viewer, bytes_per_row, nr, count, byte_values, style, colors, style_per_pixel=None):
        bits = np.unpackbits(byte_values)
        bits = bits.reshape((-1, 8))
        pixels = np.empty((nr * bytes_per_row, 4), dtype=np.uint8)
        pixels[:,0] = bits[:,0] * 2 + bits[:,1]
        pixels[:,1] = bits[:,2] * 2 + bits[:,3]
        pixels[:,2] = bits[:,4] * 2 + bits[:,5]
        pixels[:,3] = bits[:,6] * 2 + bits[:,7]

        if style_per_pixel is None:
            style_per_pixel = self.calc_style_per_pixel_2bpp(style)
        normal = (style_per_pixel & self.ignore_mask) == 0
        highlight = (style_per_pixel & style_bits.selected_bit_mask) == style_bits.selected_bit_mask
        data = (style_per_pixel & style_bits.data_bit_mask) == style_bits.data_bit_mask
        comment = (style_per_pixel & style_bits.comment_bit_mask) == style_bits.comment_bit_mask
        match = (style_per_pixel & style_bits.match_bit_mask) == style_bits.match_bit_mask

        color_registers, h_colors, m_colors, c_colors, d_colors = colors
        bitimage = np.empty((nr * bytes_per_row, 4, 3), dtype=np.uint8)
        for i in range(4):
            color_is_set = (pixels == i)
            bitimage[color_is_set & normal] = color_registers[i]
            bitimage[color_is_set & data] = d_colors[i]
            bitimage[color_is_set & comment] = c_colors[i]
            bitimage[color_is_set & match] = m_colors[i]
            bitimage[color_is_set & highlight] = h_colors[i]
        bitimage[count:,:,:] = segment_viewer.preferences.empty_background_color.Get(False)
        return bitimage

    def get_4bpp(self, segment_viewer, bytes_per_row, nr, count, byte_values, style, colors, style_per_pixel=None):
        bits = np.unpackbits(byte_values)
        bits = bits.reshape((-1, 8))
        pixels = np.empty((nr * bytes_per_row, 2), dtype=np.uint8)
        pixels[:,0] = bits[:,0] * 8 + bits[:,1] * 4 + bits[:,2] * 2 + bits[:,3]
        pixels[:,1] = bits[:,4] * 8 + bits[:,5] * 4 + bits[:,6] * 2 + bits[:,7]

        if style_per_pixel is None:
            style_per_pixel = self.calc_style_per_pixel_4bpp(style)
        normal = (style_per_pixel & self.ignore_mask) == 0
        highlight = (style_per_pixel & style_bits.selected_bit_mask) == style_bits.selected_bit_mask
        data = (style_per_pixel & style_bits.data_bit_mask) == style_bits.data_bit_mask
        comment = (style_per_pixel & style_bits.comment_bit_mask) == style_bits.comment_bit_mask
        match = (style_per_pixel & style_bits.match_bit_mask) == style_bits.match_bit_mask

        color_registers, h_colors, m_colors, c_colors, d_colors = colors
        bitimage = np.empty((nr * bytes_per_row, 2, 3), dtype=np.uint8)
        for i in range(16):
            color_is_set = (pixels == i)
            bitimage[color_is_set & normal] = color_registers[i]
            bitimage[color_is_set & data] = d_colors[i]
            bitimage[color_is_set & comment] = c_colors[i]
            bitimage[color_is_set & match] = m_colors[i]
            bitimage[color_is_set & highlight] = h_colors[i]
        bitimage[count:,:,:] = segment_viewer.preferences.empty_background_color.Get(False)
        return bitimage

    def get_bitplane_pixels(self, bits, pixels, bytes_per_row, pixels_per_row):
        """Fill the pixels array with color register data
        
        pixels is passed in as an 8 pixel wide array regardless of the actual
        pixels per row. It will be resized correctly by the calling method.
        """
        raise NotImplemented

    def get_bitplane_style(self, style):
        raise NotImplemented

    def get_bitplanes(self, segment_viewer, bytes_per_row, nr, count, byte_values, style, colors):
        bitplanes = self.bitplanes
        _, rem = divmod(np.alen(byte_values), bitplanes)
        if rem > 0:
            byte_values = np.append(byte_values, np.zeros(rem, dtype=np.uint8))
            style = np.append(style, np.zeros(rem, dtype=np.uint8))
        pixels_per_row = 8 * bytes_per_row // bitplanes
        bits = np.unpackbits(byte_values).reshape((-1, 8))
        pixels = np.empty((nr * bytes_per_row // bitplanes, pixels_per_row), dtype=np.uint8)
        self.get_bitplane_pixels(bits, pixels, bytes_per_row, pixels_per_row)
        pixels = pixels.reshape((nr, pixels_per_row))
        s = self.get_bitplane_style(style)
        style_per_pixel = s.repeat(8).reshape((-1, pixels_per_row))
        normal = (style_per_pixel & self.ignore_mask) == 0
        highlight = (style_per_pixel & style_bits.selected_bit_mask) == style_bits.selected_bit_mask
        data = (style_per_pixel & style_bits.data_bit_mask) == style_bits.data_bit_mask
        comment = (style_per_pixel & style_bits.comment_bit_mask) == style_bits.comment_bit_mask
        match = (style_per_pixel & style_bits.match_bit_mask) == style_bits.match_bit_mask

        color_registers, h_colors, m_colors, c_colors, d_colors = colors
        bitimage = np.empty((nr, pixels_per_row, 3), dtype=np.uint8)
        for i in range(2**bitplanes):
            color_is_set = (pixels == i)
            bitimage[color_is_set & normal] = color_registers[i]
            bitimage[color_is_set & data] = d_colors[i]
            bitimage[color_is_set & comment] = c_colors[i]
            bitimage[color_is_set & match] = m_colors[i]
            bitimage[color_is_set & highlight] = h_colors[i]
        bitimage[count:,:,:] = segment_viewer.preferences.empty_background_color.Get(False)
        return bitimage


class OneBitPerPixelB(BaseRenderer):
    name = "B/W, 1bpp, on=black"

    def get_bw_colors(self, segment_viewer):
        return ((255, 255, 255), (0, 0, 0))

    def get_image(self, segment_viewer, bytes_per_row, nr, count, byte_values, style, style_per_pixel=None):
        bits = np.unpackbits(byte_values)
        pixels = bits.reshape((-1, 8))

        background = (pixels == 0)
        color1 = (pixels == 1)

        bw_colors = self.get_bw_colors(segment_viewer)
        h_colors = colors.get_blended_color_registers(bw_colors, segment_viewer.preferences.highlight_background_color)
        m_colors = colors.get_blended_color_registers(bw_colors, segment_viewer.preferences.match_background_color)
        c_colors = colors.get_blended_color_registers(bw_colors, segment_viewer.preferences.comment_background_color)
        d_colors = colors.get_dimmed_color_registers(bw_colors, segment_viewer.preferences.background_color, segment_viewer.preferences.data_background_color)

        if style_per_pixel is None:
            style_per_pixel = self.calc_style_per_pixel_1bpp(style)
        normal = (style_per_pixel & self.ignore_mask) == 0
        highlight = (style_per_pixel & style_bits.selected_bit_mask) == style_bits.selected_bit_mask
        data = (style_per_pixel & style_bits.data_bit_mask) == style_bits.data_bit_mask
        comment = (style_per_pixel & style_bits.comment_bit_mask) == style_bits.comment_bit_mask
        match = (style_per_pixel & style_bits.match_bit_mask) == style_bits.match_bit_mask

        bitimage = np.empty((nr * bytes_per_row, 8, 3), dtype=np.uint8)
        bitimage[background & normal] = bw_colors[0]
        bitimage[background & data] = d_colors[0]
        bitimage[background & comment] = c_colors[0]
        bitimage[background & match] = m_colors[0]
        bitimage[background & highlight] = h_colors[0]
        bitimage[color1 & normal] = bw_colors[1]
        bitimage[color1 & data] = d_colors[1]
        bitimage[color1 & comment] = c_colors[1]
        bitimage[color1 & match] = m_colors[1]
        bitimage[color1 & highlight] = h_colors[1]
        bitimage[count:,:,:] = segment_viewer.preferences.empty_background_color.Get(False)

        return self.reshape(bitimage, bytes_per_row, nr)


class OneBitPerPixelW(OneBitPerPixelB):
    name = "B/W, 1bpp, on=white"

    def get_bw_colors(self, segment_viewer):
        return ((0, 0, 0), (255, 255, 255))


class OneBitPerPixelPM1(OneBitPerPixelB):
    name = "Player/Missile, normal width"
    scale_width = 2


class OneBitPerPixelPM2(OneBitPerPixelB):
    name = "Player/Missile, double width"
    scale_width = 4


class OneBitPerPixelPM4(OneBitPerPixelB):
    name = "Player/Missile, quad width"
    scale_width = 8


class ModeB(OneBitPerPixelB):
    name = "Antic B (Gr 6, 1bpp)"
    scale_width = 2
    scale_height = 2

    def get_bw_colors(self, segment_viewer):
        color_registers = [segment_viewer.color_registers[r] for r in [8, 4]]
        return color_registers


class ModeC(ModeB):
    name = "Antic C (Gr 6+, 1bpp)"
    scale_width = 2
    scale_height = 2


class OneBitPerPixelApple2Linear(BaseRenderer):
    name = "B/W, Apple 2, Linear"

    def get_bw_colors(self, segment_viewer):
        return ((0, 0, 0), (255, 255, 255))

    def calc_style_per_pixel(self, style):
        return np.vstack((style, style, style, style, style, style, style)).T

    def get_image(self, segment_viewer, bytes_per_row, nr, count, byte_values, style, style_per_pixel=None):
        bits = np.unpackbits(bit_reverse_table[byte_values])
        pixels = bits.reshape((-1, 8))

        background = (pixels[:,0:7] == 0)
        color1 = (pixels[:,0:7] == 1)

        bw_colors = self.get_bw_colors(segment_viewer)
        h_colors = colors.get_blended_color_registers(bw_colors, segment_viewer.preferences.highlight_background_color)
        m_colors = colors.get_blended_color_registers(bw_colors, segment_viewer.preferences.match_background_color)
        c_colors = colors.get_blended_color_registers(bw_colors, segment_viewer.preferences.comment_background_color)
        d_colors = colors.get_dimmed_color_registers(bw_colors, segment_viewer.preferences.background_color, segment_viewer.preferences.data_background_color)

        if style_per_pixel is None:
            style_per_pixel = self.calc_style_per_pixel(style)
        normal = (style_per_pixel & self.ignore_mask) == 0
        highlight = (style_per_pixel & style_bits.selected_bit_mask) == style_bits.selected_bit_mask
        data = (style_per_pixel & style_bits.data_bit_mask) == style_bits.data_bit_mask
        comment = (style_per_pixel & style_bits.comment_bit_mask) == style_bits.comment_bit_mask
        match = (style_per_pixel & style_bits.match_bit_mask) == style_bits.match_bit_mask

        bitimage = np.empty((nr * bytes_per_row, 7, 3), dtype=np.uint8)
        bitimage[background & normal] = bw_colors[0]
        bitimage[background & data] = d_colors[0]
        bitimage[background & comment] = c_colors[0]
        bitimage[background & match] = m_colors[0]
        bitimage[background & highlight] = h_colors[0]
        bitimage[color1 & normal] = bw_colors[1]
        bitimage[color1 & data] = d_colors[1]
        bitimage[color1 & comment] = c_colors[1]
        bitimage[color1 & match] = m_colors[1]
        bitimage[color1 & highlight] = h_colors[1]
        bitimage[count:,:,:] = segment_viewer.preferences.empty_background_color.Get(False)

        return bitimage.reshape((nr, bytes_per_row * 7, 3))


def generate_apple2_row_offsets():
    offsets = np.zeros(192, dtype=np.int32)
    for y in range(192):
        # From Apple Graphics and Arcade Game Design
        a = y // 64
        d = y - (64 * a)
        b = d // 8
        c = d - 8 * b
        offsets[i] = (1024 * c) + (128 * b) + (40 * a)
    return offsets

def generate_apple2_index():
    offsets = generate_apple2_row_offsets()
    bytepos = np.empty((192, 280), dtype=np.int32)
    bytepos[:,0] = offsets * 7

class OneBitPerPixelApple2FullScreen(OneBitPerPixelApple2Linear):
    name = "B/W, Apple 2, Screen Order"

    def get_image(self, segment_viewer, bytes_per_row, nr, count, byte_values, style, style_per_pixel=None):
        screen = np.zeros((8192,), dtype=np.uint8)
        byte_values = byte_values[0:8192]
        num_valid = len(byte_values)  # might be smaller than 8192
        screen[:num_valid] = byte_values
        bits = np.unpackbits(bit_reverse_table[screen])
        pixels = bits.reshape((-1, 8))

        background = (pixels[:,0:7] == 0)
        color1 = (pixels[:,0:7] == 1)

        bw_colors = self.get_bw_colors(segment_viewer)
        h_colors = colors.get_blended_color_registers(bw_colors, segment_viewer.preferences.highlight_background_color)
        m_colors = colors.get_blended_color_registers(bw_colors, segment_viewer.preferences.match_background_color)
        c_colors = colors.get_blended_color_registers(bw_colors, segment_viewer.preferences.comment_background_color)
        d_colors = colors.get_dimmed_color_registers(bw_colors, segment_viewer.preferences.background_color, segment_viewer.preferences.data_background_color)

        if style_per_pixel is None:
            style_per_pixel = self.calc_style_per_pixel(style)
        normal = (style_per_pixel & self.ignore_mask) == 0
        highlight = (style_per_pixel & style_bits.selected_bit_mask) == style_bits.selected_bit_mask
        data = (style_per_pixel & style_bits.data_bit_mask) == style_bits.data_bit_mask
        comment = (style_per_pixel & style_bits.comment_bit_mask) == style_bits.comment_bit_mask
        match = (style_per_pixel & style_bits.match_bit_mask) == style_bits.match_bit_mask

        bitimage = np.empty((192 * 40, 7, 3), dtype=np.uint8)
        bitimage[background & normal] = bw_colors[0]
        bitimage[background & data] = d_colors[0]
        bitimage[background & comment] = c_colors[0]
        bitimage[background & match] = m_colors[0]
        bitimage[background & highlight] = h_colors[0]
        bitimage[color1 & normal] = bw_colors[1]
        bitimage[color1 & data] = d_colors[1]
        bitimage[color1 & comment] = c_colors[1]
        bitimage[color1 & match] = m_colors[1]
        bitimage[color1 & highlight] = h_colors[1]
        bitimage[count:,:,:] = segment_viewer.preferences.empty_background_color.Get(False)

        return bitimage.reshape((nr, bytes_per_row * 7, 3))


class OneBitPerPixelApple2Artifacting(OneBitPerPixelApple2Linear):
    name = "Apple 2 (artifacting colors)"

    def get_bw_colors(self, segment_viewer):
        return ((255, 255, 255), (0, 0, 0))

    # 0 0000000 0 0000000  # black 0, 0, 0
    # 0 0101010 0 1010101  # green 32, 192, 0
    # 0 1010101 0 0101010  # purple 159, 0, 253
    # 0 1111111 0 1111111  # white 255, 255, 255
    # 1 0000000 1 0000000  # black 0, 0, 0
    # 1 0101010 1 1010101  # orange 240, 80, 0
    # 1 1010101 1 0101010  # blue 0, 128, 255
    # 1 1111111 1 1111111  # white 255, 255, 255
    #
    # From https://groups.google.com/forum/#!msg/comp.sys.apple2.programmer/vxtFo6QEYGg/9kh1RfovGQAJ
    # bit #
    # 0 1 2 3 4 5 6 7   0 1 2 3 4 5 6 7

    #          color bit          color bit
    #               |                 |
    # 0 0 0 0 0 0 0 0   0 0 0 0 0 0 0 0
    # |_| |_| |_| |_____| |_| |_| |_|

    #  0   1   2     3     4   5   6

    # every 2 byte_values starting on an even number ($2000.2001) gives seven pixels.
    # As you can see, pixel #3 uses a bit from byte $2000 and byte 2001 to form
    # a pixel. if any two bits are consecutive (except the color bit) you get
    # two white pixels. with color bit clear, each group of bits will show
    # violet or green. with color bit set, each group of bits will show blue or
    # orange.

    # color bit clear
    # bits-color
    # 00 - black
    # 10 - violet
    # 01 - green
    # 11 - white

    # color bit set
    # 00 - black
    # 10 - blue
    # 01 - orange
    # 11 - white

    def get_image(self, segment_viewer, bytes_per_row, nr, count, byte_values, style, style_per_pixel=None):
        bits = np.unpackbits(bit_reverse_table[byte_values])
        pixels = bits.reshape((-1, 8))

        background = (pixels[:,0:7] == 0)
        color1 = (pixels[:,0:7] == 1)

        bw_colors = self.get_bw_colors(segment_viewer)
        h_colors = colors.get_blended_color_registers(bw_colors, segment_viewer.preferences.highlight_background_color)
        m_colors = colors.get_blended_color_registers(bw_colors, segment_viewer.preferences.match_background_color)
        c_colors = colors.get_blended_color_registers(bw_colors, segment_viewer.preferences.comment_background_color)
        d_colors = colors.get_dimmed_color_registers(bw_colors, segment_viewer.preferences.background_color, segment_viewer.preferences.data_background_color)

        if style_per_pixel is None:
            style_per_pixel = self.calc_style_per_pixel(style)
        normal = (style_per_pixel & self.ignore_mask) == 0
        highlight = (style_per_pixel & style_bits.selected_bit_mask) == style_bits.selected_bit_mask
        data = (style_per_pixel & style_bits.data_bit_mask) == style_bits.data_bit_mask
        comment = (style_per_pixel & style_bits.comment_bit_mask) == style_bits.comment_bit_mask
        match = (style_per_pixel & style_bits.match_bit_mask) == style_bits.match_bit_mask

        bitimage = np.empty((nr * bytes_per_row, 7, 3), dtype=np.uint8)
        bitimage[background & normal] = bw_colors[0]
        bitimage[background & data] = d_colors[0]
        bitimage[background & comment] = c_colors[0]
        bitimage[background & match] = m_colors[0]
        bitimage[background & highlight] = h_colors[0]
        bitimage[color1 & normal] = bw_colors[1]
        bitimage[color1 & data] = d_colors[1]
        bitimage[color1 & comment] = c_colors[1]
        bitimage[color1 & match] = m_colors[1]
        bitimage[color1 & highlight] = h_colors[1]
        bitimage[count:,:,:] = segment_viewer.preferences.empty_background_color.Get(False)

        return bitimage.reshape((nr, bytes_per_row * 7, 3))


class TwoBitsPerPixel(BaseRenderer):
    name = "2bpp"
    pixels_per_byte = 4

    def get_image(self, segment_viewer, bytes_per_row, nr, count, byte_values, style, style_per_pixel=None):
        colors = self.get_colors(segment_viewer, [0, 1, 2, 3])
        bitimage = self.get_2bpp(segment_viewer, bytes_per_row, nr, count, byte_values, style, colors, style_per_pixel)
        return self.reshape(bitimage, bytes_per_row, nr)


class ModeD(TwoBitsPerPixel):
    name = "Antic D (Gr 7, 2bpp)"
    scale_width = 2
    scale_height = 2
    pixels_per_byte = 4

    def get_image(self, segment_viewer, bytes_per_row, nr, count, byte_values, style, style_per_pixel=None):
        colors = self.get_colors(segment_viewer, [8, 4, 5, 6])
        bitimage = self.get_2bpp(segment_viewer, bytes_per_row, nr, count, byte_values, style, colors, style_per_pixel)
        return self.reshape(bitimage, bytes_per_row, nr)


class ModeE(ModeD):
    name = "Antic E (Gr 7+, 2bpp)"
    scale_width = 2
    scale_height = 1
    pixels_per_byte = 4


class FourBitsPerPixel(BaseRenderer):
    name = "4bpp"
    pixels_per_byte = 2

    def get_image(self, segment_viewer, bytes_per_row, nr, count, byte_values, style, style_per_pixel=None):
        colors = self.get_colors(segment_viewer, list(range(16)))
        bitimage = self.get_4bpp(segment_viewer, bytes_per_row, nr, count, byte_values, style, colors, style_per_pixel)
        return self.reshape(bitimage, bytes_per_row, nr)


class TwoBitPlanesLE(BaseRenderer):
    name = "2 Bit Planes (little endian)"
    pixels_per_byte = 8
    bitplanes = 2

    def get_bitplane_pixels(self, bits, pixels, bytes_per_row, pixels_per_row):
        for i in range(pixels_per_row):
            pixels[:,i] = bits[0::2,i] + bits[1::2,i] * 2

    def get_bitplane_style(self, style):
        return style[0::2] | style[1::2]

    def validate_bytes_per_row(self, bytes_per_row):
        scale, rem = divmod(bytes_per_row, self.bitplanes)
        if rem > 0:
            bytes_per_row = (scale + 1) * self.bitplanes
        return bytes_per_row

    def get_image(self, segment_viewer, bytes_per_row, nr, count, byte_values, style, style_per_pixel=None):
        colors = self.get_colors(segment_viewer, list(range(2**self.bitplanes)))
        bitimage = self.get_bitplanes(segment_viewer, bytes_per_row, nr, count, byte_values, style, colors, style_per_pixel)
        return bitimage


class TwoBitPlanesBE(TwoBitPlanesLE):
    name = "2 Bit Planes (big endian)"

    def get_bitplane_pixels(self, bits, pixels, bytes_per_row, pixels_per_row):
        for i in range(pixels_per_row):
            pixels[:,i] = bits[0::2,i] * 2 + bits[1::2,i]


class TwoBitPlanesLineLE(TwoBitPlanesLE):
    name = "2 Bit Planes (little endian, interleave by line)"

    def get_bitplane_pixels(self, bits, pixels, bytes_per_row, pixels_per_row):
        pixel_rows = bytes_per_row // 2
        for i in range(pixels_per_row):
            for j in range(pixel_rows):
                little = j
                big = j + pixel_rows
                pixels[j::pixel_rows,i] = bits[big::bytes_per_row,i] * 2 + bits[little::bytes_per_row,i]


class TwoBitPlanesLineBE(TwoBitPlanesLE):
    name = "2 Bit Planes (big endian, interleave by line)"

    def get_bitplane_pixels(self, bits, pixels, bytes_per_row, pixels_per_row):
        pixel_rows = bytes_per_row // 2
        for i in range(pixels_per_row):
            for j in range(pixel_rows):
                little = j + pixel_rows
                big = j
                pixels[j::pixel_rows,i] = bits[big::bytes_per_row,i] * 2 + bits[little::bytes_per_row,i]


class ThreeBitPlanesLE(TwoBitPlanesLE):
    name = "3 Bit Planes (little endian)"
    bitplanes = 3

    def get_bitplane_pixels(self, bits, pixels, bytes_per_row, pixels_per_row):
        for i in range(pixels_per_row):
            pixels[:,i] = bits[0::3,i] * 4 + bits[1::3,i] * 2 + bits[2::3,i]

    def get_bitplane_style(self, style):
        return style[0::3] | style[1::3] | style[2::3]


class ThreeBitPlanesBE(ThreeBitPlanesLE):
    name = "3 Bit Planes (big endian)"
    bitplanes = 3

    def get_bitplane_pixels(self, bits, pixels, bytes_per_row, pixels_per_row):
        for i in range(pixels_per_row):
            pixels[:,i] = bits[0::3,i] + bits[1::3,i] * 2 + bits[2::3,i] * 4


class ThreeBitPlanesLineLE(ThreeBitPlanesLE):
    name = "3 Bit Planes (little endian, interleave by line)"

    def get_bitplane_pixels(self, bits, pixels, bytes_per_row, pixels_per_row):
        pixel_rows = bytes_per_row // 3
        for i in range(pixels_per_row):
            for j in range(pixel_rows):
                little = j
                mid = j + pixel_rows
                big = j + (2 * pixel_rows)
                pixels[j::pixel_rows,i] = bits[big::bytes_per_row,i] * 4 + bits[mid::bytes_per_row,i] * 2 + bits[little::bytes_per_row,i]


class ThreeBitPlanesLineBE(ThreeBitPlanesBE):
    name = "3 Bit Planes (big endian, interleave by line)"

    def get_bitplane_pixels(self, bits, pixels, bytes_per_row, pixels_per_row):
        pixel_rows = bytes_per_row // 3
        for i in range(pixels_per_row):
            for j in range(pixel_rows):
                little = j + (2 * pixel_rows)
                mid = j + pixel_rows
                big = j
                pixels[j::pixel_rows,i] = bits[big::bytes_per_row,i] * 4 + bits[mid::bytes_per_row,i] * 2 + bits[little::bytes_per_row,i]


class FourBitPlanesLE(TwoBitPlanesLE):
    name = "4 Bit Planes (little endian)"
    bitplanes = 4

    def get_bitplane_pixels(self, bits, pixels, bytes_per_row, pixels_per_row):
        for i in range(pixels_per_row):
            pixels[:,i] = bits[0::4,i] * 8 + bits[1::4,i] * 4 + bits[2::4,i] * 2 + bits[3::4,i]

    def get_bitplane_style(self, style):
        return style[0::4] | style[1::4] | style[2::4] | style[3::4]


class FourBitPlanesBE(FourBitPlanesLE):
    name = "4 Bit Planes (big endian)"

    def get_bitplane_pixels(self, bits, pixels, bytes_per_row, pixels_per_row):
        for i in range(pixels_per_row):
            pixels[:,i] = bits[0::4,i] + bits[1::4,i] * 2 + bits[2::4,i] * 4 + bits[3::4,i] * 8


class FourBitPlanesLineLE(FourBitPlanesLE):
    name = "4 Bit Planes (little endian, interleave by line)"

    def get_bitplane_pixels(self, bits, pixels, bytes_per_row, pixels_per_row):
        pixel_rows = bytes_per_row // 4
        for i in range(pixels_per_row):
            for j in range(pixel_rows):
                little = j
                little_mid = j + pixel_rows
                big_mid = j + (2 * pixel_rows)
                big = j + (3 * pixel_rows)
                pixels[j::pixel_rows,i] = bits[big::bytes_per_row,i] * 8 + bits[big_mid::bytes_per_row,i] * 4 + bits[little_mid::bytes_per_row,i] * 2 + bits[little::bytes_per_row,i]


class FourBitPlanesLineBE(FourBitPlanesLE):
    name = "4 Bit Planes (big endian, interleave by line)"

    def get_bitplane_pixels(self, bits, pixels, bytes_per_row, pixels_per_row):
        pixel_rows = bytes_per_row // 4
        for i in range(pixels_per_row):
            for j in range(pixel_rows):
                little = j + (3 * pixel_rows)
                little_mid = j + (2 * pixel_rows)
                big_mid = j + pixel_rows
                big = j
                pixels[j::pixel_rows,i] = bits[big::bytes_per_row,i] * 8 + bits[big_mid::bytes_per_row,i] * 4 + bits[little_mid::bytes_per_row,i] * 2 + bits[little::bytes_per_row,i]


class GTIA9(FourBitsPerPixel):
    name = "GTIA 9 (4bpp, 16 luminances, 1 color)"
    scale_width = 4
    pixels_per_byte = 2

    def get_antic_color_registers(self, segment_viewer):
        first_color = segment_viewer.antic_color_registers[8] & 0xf0
        return list(range(first_color, first_color + 16))

    def get_colors(self, segment_viewer, registers):
        antic_color_registers = self.get_antic_color_registers(segment_viewer)
        color_registers = colors.get_color_registers(antic_color_registers, segment_viewer.color_standard)
        h_colors = colors.get_blended_color_registers(color_registers, segment_viewer.preferences.highlight_background_color)
        m_colors = colors.get_blended_color_registers(color_registers, segment_viewer.preferences.match_background_color)
        c_colors = colors.get_blended_color_registers(color_registers, segment_viewer.preferences.comment_background_color)
        d_colors = colors.get_dimmed_color_registers(color_registers, segment_viewer.preferences.background_color, segment_viewer.preferences.data_background_color)
        return color_registers, h_colors, m_colors, c_colors, d_colors


class GTIA10(GTIA9):
    name = "GTIA 10 (4bpp, 9 colors)"

    def get_antic_color_registers(self, segment_viewer):
        return list(segment_viewer.antic_color_registers[0:9]) + [0] * 7


class GTIA11(GTIA9):
    name = "GTIA 11 (4bpp, 1 luminace, 16 colors)"

    def get_antic_color_registers(self, segment_viewer):
        first_color = segment_viewer.antic_color_registers[8] & 0x0f
        return list(range(first_color, first_color + 256, 16))


class BaseBytePerPixelRenderer(BaseRenderer):
    """A generic renderer to display one pixel of the source using a byte
    for the image. This provides highlighting on a per-pixel level which isn't possible with modes that have multiple pixels in a byte. This is used as an intermediate renderer, so the image format can convert to byte per pixel, and this renderer can display it.

    Theoretically this will be able to display 256 colors, but at the
    moment only uses the first 16 colors. It is mapped to the ANTIC color
    register order, so the first 4 colors are player colors, then the 5
    playfield colors. A blank screen corresponds to the index value of 8, so
    the last playfield color.
    """
    name = "Intermediate Mode 1 Byte Per Pixel"
    pixels_per_byte = 1
    bitplanes = 1

    def pixels_from_2bpp(self, segment_viewer, bytes_per_row, nr, count, byte_values, style, colors):
        bits = np.unpackbits(byte_values)
        bits = bits.reshape((-1, 8))
        pixels = np.empty((nr * bytes_per_row, 4), dtype=np.uint8)
        pixels[:,0] = bits[:,0] * 2 + bits[:,1]
        pixels[:,1] = bits[:,2] * 2 + bits[:,3]
        pixels[:,2] = bits[:,4] * 2 + bits[:,5]
        pixels[:,3] = bits[:,6] * 2 + bits[:,7]
        style_per_pixel = np.vstack((style, style, style, style)).T
        return pixels, style_per_pixel

    def get_image(self, segment_viewer, bytes_per_row, nr, count, byte_values, style, style_per_pixel=None):
        normal = style == 0
        highlight = (style & style_bits.selected_bit_mask) == style_bits.selected_bit_mask
        comment = (style & style_bits.comment_bit_mask) == style_bits.comment_bit_mask
        data = (style & style_bits.data_bit_mask) == style_bits.data_bit_mask
        match = (style & style_bits.match_bit_mask) == style_bits.match_bit_mask

        color_registers, h_colors, m_colors, c_colors, d_colors = self.get_colors(segment_viewer, list(range(16)))
        bitimage = np.empty((nr * bytes_per_row, 3), dtype=np.uint8)
        for i in range(16):
            color_is_set = (byte_values == i)
            bitimage[color_is_set & normal] = color_registers[i]
            bitimage[color_is_set & comment] = c_colors[i]
            bitimage[color_is_set & match] = m_colors[i]
            bitimage[color_is_set & data] = d_colors[i]
            bitimage[color_is_set & highlight] = h_colors[i]
        bitimage[count:,:] = segment_viewer.preferences.empty_background_color.Get(False)
        return bitimage.reshape((nr, bytes_per_row, 3))


class BytePerPixelMemoryMap(BaseRenderer):
    name = "1Bpp Greyscale"

    def get_image(self, segment_viewer, byte_values, style, start_byte, end_byte, bytes_per_row, nr, start_col, visible_cols):
        if speedups is not None:
            array = speedups.get_numpy_memory_map_image(segment_viewer, byte_values, style, start_byte, end_byte, bytes_per_row, nr, start_col, visible_cols)
        else:
            array = get_numpy_memory_map_image(segment_viewer, byte_values, style, start_byte, end_byte, bytes_per_row, nr, start_col, visible_cols)
        return array

    def get_image(self, segment_viewer, bytes_per_row, nr, count, byte_values, style, style_per_pixel=None):
        array = get_numpy_memory_map_image(segment_viewer, bytes_per_row, nr, count, byte_values, style)
        return array


def get_numpy_memory_map_image(segment_viewer, bytes_per_row, nr, count, byte_values, style):
    log.debug("SLOW VERSION OF get_numpy_memory_map_image!!!")

    array = np.empty((nr, bytes_per_row, 3), dtype=np.uint8)
    array[:,:] = segment_viewer.preferences.empty_background_color.Get(False)
    selected_color = segment_viewer.preferences.highlight_background_color

    for j in range(nr):
        for i in range(bytes_per_row):
            c = byte_values[j * 256 + i] ^ 0xff
            s = style[j * 256 + i]
            if s & style_bits.selected_bit_mask:
                r = selected_color[0] * c >> 8
                g = selected_color[1] * c >> 8
                b = selected_color[2] * c >> 8
                array[j,i,:] = (r, g, b)
            else:
                array[j,i,:] = (c, c, c)
    return array


class MemoryAccessMap(BytePerPixelMemoryMap):
    name = "Memory Access"

    def get_image(self, segment_viewer, bytes_per_row, nr, count, byte_values, style):
        if speedups is not None:
            source = byte_values.reshape((nr, bytes_per_row))
            style = style.reshape((nr, bytes_per_row))
            array = speedups.get_numpy_memory_access_image(segment_viewer, bytes_per_row, nr, count, source, style, 0, bytes_per_row)
        else:
            array = get_numpy_memory_access_image(segment_viewer, bytes_per_row, nr, count, byte_values, style)
        return array


def get_numpy_memory_access_image(segment_viewer, bytes_per_row, nr, count, byte_values, style):

    source = byte_values.reshape((nr, bytes_per_row))
    style = style.reshape((nr, bytes_per_row))
    array = np.empty((nr, bytes_per_row, 3), dtype=np.uint8)
    array[:,:] = segment_viewer.preferences.empty_background_color.Get(False)
    selected_color = segment_viewer.preferences.highlight_background_color

    current_frame_number = segment_viewer.current_frame_number
    print(f"SLOW VERSION OF get_numpy_memory_access_image; frame = {current_frame_number}")
    print(source)

    from ..debugger import dtypes as dd

    for j in range(nr):
        for i in range(bytes_per_row):
            c = source[j, i]
            s = style[j, i]

            rgb = ((np.asarray(dd.default_access_type_colors[s])*c)/256).astype(np.uint8)
            if s & style_bits.selected_bit_mask:
                rgb = rgb >> 8
            array[j,i,:] = rgb
    return array


bitmap_renderer_list = [
    OneBitPerPixelB(),
    OneBitPerPixelW(),
    OneBitPerPixelPM1(),
    OneBitPerPixelPM2(),
    OneBitPerPixelPM4(),
    OneBitPerPixelApple2Linear(),
    ModeB(),
    ModeC(),
    ModeD(),
    ModeE(),
    GTIA9(),
    GTIA10(),
    GTIA11(),
    TwoBitsPerPixel(),
    FourBitsPerPixel(),
    TwoBitPlanesLE(),
    TwoBitPlanesLineLE(),
    TwoBitPlanesBE(),
    TwoBitPlanesLineBE(),
    ThreeBitPlanesLE(),
    ThreeBitPlanesLineLE(),
    ThreeBitPlanesBE(),
    ThreeBitPlanesLineBE(),
    FourBitPlanesLE(),
    FourBitPlanesLineLE(),
    FourBitPlanesBE(),
    FourBitPlanesLineBE(),
]

valid_bitmap_renderers = {item.name: item for item in bitmap_renderer_list}
