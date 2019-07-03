import numpy as np

import wx

from atrip import style_bits

from sawx.utils.permute import bit_reverse_table
from sawx.utils.nputil import intscale, intwscale, intwscale_font

from atrip.machines import atari8bit
from .bitmap_renderers import BaseRenderer
try:
    from . import antic_speedups as speedups
except ImportError:
    speedups = None

import logging
log = logging.getLogger(__name__)


class Mode2(BaseRenderer):
    name = "Antic 2 (Gr 0)"
    char_bit_width = 8
    char_bit_height = 8
    scale_width = 1
    scale_height = 1
    expected_chars = 128

    @classmethod
    def get_image(cls, machine, antic_font, byte_values, style, start_byte, end_byte, bytes_per_row, nr, start_col, visible_cols):
        if speedups is not None:
            array = speedups.get_numpy_font_map_image(machine, antic_font, byte_values, style, start_byte, end_byte, bytes_per_row, nr, start_col, visible_cols)
        else:
            array = get_numpy_font_map_image(machine, antic_font, byte_values, style, start_byte, end_byte, bytes_per_row, nr, start_col, visible_cols)
        return array

    @property
    def bytes_per_char(self):
        return (self.char_bit_width + 7) // 8 * self.char_bit_height

    def get_font(self, data, colors, gr0_colors, reverse=False):
        bits = self.data_to_bits(data)
        font = self.bits_to_font(bits, colors, gr0_colors, reverse)
        return font

    def data_to_bits(self, data):
        """Convert byte data into bits, returning only a subset if
        required
        """
        padded = self.pad_data(data)
        bits = np.unpackbits(padded)
        bits = bits.reshape((-1, 8, 8))
        bits = self.select_subset(bits)
        return bits

    def pad_data(self, data):
        """Expand (or shrink if necessary) to conform to the expected input
        size of font data array
        """
        count = data.shape[0]
        expected_bytes = self.bytes_per_char * self.expected_chars
        if count > expected_bytes:
            data = data[0:expected_bytes]
        elif count < expected_bytes:
            expanded = np.zeros((expected_bytes), dtype=np.uint8)
            expanded[0:count] = data
            expanded[count:] = 0
            data = expanded
        return data

    def select_subset(self, bits):
        """If the font is made up of only a portion of the data, return the
        array that contains only the interesting bits.
        """
        return bits

    def bits_to_font(self, bits, colors, gr0_colors, reverse=False):
        fg, bg = gr0_colors
        if reverse:
            fg, bg = bg, fg
        r = np.empty(bits.shape, dtype=np.uint8)
        r[bits==0] = bg[0]
        r[bits==1] = fg[0]
        g = np.empty(bits.shape, dtype=np.uint8)
        g[bits==0] = bg[1]
        g[bits==1] = fg[1]
        b = np.empty(bits.shape, dtype=np.uint8)
        b[bits==0] = bg[2]
        b[bits==1] = fg[2]
        font = np.zeros((256, 8, 8, 3), dtype=np.uint8)
        # store the first 128 chars as the normal chars
        font[0:128,:,:,0] = r
        font[0:128,:,:,1] = g
        font[0:128,:,:,2] = b

        # create inverse characters from first 128 chars
        r[bits==0] = fg[0]
        r[bits==1] = bg[0]
        g[bits==0] = fg[1]
        g[bits==1] = bg[1]
        b[bits==0] = fg[2]
        b[bits==1] = bg[2]
        font[128:256,:,:,0] = r
        font[128:256,:,:,1] = g
        font[128:256,:,:,2] = b
        return font


class Mode4(Mode2):
    name = "Antic 4 (40x24, 5 color)"

    def bits_to_font(self, bits, colors, gr0_colors, reverse=False):
        """ http://www.atarimagazines.com/compute/issue49/419_1_Graphics_0_Text_In_Four_Colors.php
        
        There are four possible combinations of two bits: 00, 01, 10, 11. Each combination represents a different color. The color corresponding to the bit-pair 00 is stored at location 712; the color for the bit-pair 01 is at location 708; the color for bit-pair 10 is at 709; the color for bit-pair 11 is at 710.
        """
        pf0, pf1, pf2, pf3, bak = colors[4:9]
        r = np.empty(bits.shape, dtype=np.uint8)
        g = np.empty(bits.shape, dtype=np.uint8)
        b = np.empty(bits.shape, dtype=np.uint8)

        c = np.empty((128, 8, 4), dtype=np.uint8)
        c[:,:,0] = bits[:,:,0]*2 + bits[:,:,1]
        c[:,:,1] = bits[:,:,2]*2 + bits[:,:,3]
        c[:,:,2] = bits[:,:,4]*2 + bits[:,:,5]
        c[:,:,3] = bits[:,:,6]*2 + bits[:,:,7]

        pixels = np.empty((128, 8, 4, 3), dtype=np.uint8)
        pixels[c==0] = bak
        pixels[c==1] = pf0
        pixels[c==2] = pf1
        pixels[c==3] = pf2

        font = np.zeros((256, 8, 4, 3), dtype=np.uint8)
        font[0:128,:,:,:] = pixels

        # Inverse characters use pf3 in place of pf2
        pixels[c==3] = pf3
        font[128:256,:,:,:] = pixels

        # create a double-width image to expand the pixels to the correct
        # aspect ratio
        output = intwscale_font(font, 2)
        return output


class Mode5(Mode4):
    name = "Antic 5 (40x12, 5 color)"
    scale_height = 2


class Mode6Base(Mode2):
    name = "Antic 6 (base class)"
    scale_width = 2

    def bits_to_font(self, bits, colors, gr0_colors, reverse=False):
        bg = colors[8]
        r = np.empty(bits.shape, dtype=np.uint8)
        g = np.empty(bits.shape, dtype=np.uint8)
        b = np.empty(bits.shape, dtype=np.uint8)
        font = np.zeros((256, 8, 8, 3), dtype=np.uint8)

        start_char = 0
        for i in range(4, 8):
            end_char = start_char + 64
            fg = colors[i]
            r[bits==0] = bg[0]
            r[bits==1] = fg[0]
            g[bits==0] = bg[1]
            g[bits==1] = fg[1]
            b[bits==0] = bg[2]
            b[bits==1] = fg[2]
            font[start_char:end_char,:,:,0] = r
            font[start_char:end_char,:,:,1] = g
            font[start_char:end_char,:,:,2] = b
            start_char = end_char
        return font


class Mode6Upper(Mode6Base):
    name = "Antic 6 (Gr 1) Uppercase and Numbers"

    def select_subset(self, bits):
        return bits[0:64,:,:]


class Mode6Lower(Mode6Base):
    name = "Antic 6 (Gr 1) Lowercase and Symbols"

    def select_subset(self, bits):
        return bits[64:128,:,:]


class Mode7Upper(Mode6Base):
    name = "Antic 7 (Gr 2) Uppercase and Numbers"
    scale_height = 2

    def select_subset(self, bits):
        return bits[0:64,:,:]


class Mode7Lower(Mode6Base):
    name = "Antic 7 (Gr 2) Lowercase and Symbols"
    scale_height = 2

    def select_subset(self, bits):
        return bits[64:128,:,:]


class Apple2TextMode(Mode2):
    name = "Apple ]["
    char_bit_width = 7
    expected_chars = 256

    def pad_data(self, data):
        """Expand (or shrink if necessary) to conform to the expected input
        size of font data array
        """
        count = data.shape[0]

        # if more than 128 characters, assume not blinking and pad/truncate to
        # 256 chars
        if count >= 2048:
            return data[0:2048]
        if count > 1024:
            expanded = np.zeros(2048, dtype=np.uint8)
            expanded[0:count] = data
            expanded[count:] = 0
            return expanded

        # pad to 1024 if necessary; inverse/blinking will be applied later
        if count < 1024:
            expanded = np.zeros(1024, dtype=np.uint8)
            expanded[0:count] = data
            expanded[count:] = 0
            data = expanded
        return data

    def bits_to_font(self, bits, colors, gr0_colors, reverse=False):
        bg = (0, 0, 0)
        fg = (255, 255, 255)
        r = np.empty(bits.shape, dtype=np.uint8)
        r[bits==0] = bg[0]
        r[bits==1] = fg[0]
        g = np.empty(bits.shape, dtype=np.uint8)
        g[bits==0] = bg[1]
        g[bits==1] = fg[1]
        b = np.empty(bits.shape, dtype=np.uint8)
        b[bits==0] = bg[2]
        b[bits==1] = fg[2]
        font = np.zeros((256, 8, 7, 3), dtype=np.uint8)
        if bits.shape[0] == 256:
            # all 256 chars are defined, so just store them
            font[:,:,:,0] = r[:,:,8:0:-1]
            font[:,:,:,1] = g[:,:,8:0:-1]
            font[:,:,:,2] = b[:,:,8:0:-1]
        else:
            # only 128 chars are present, so create inversed/blink copies

            # Normal characters get stored in 2nd 128 char positions
            font[128:256,:,:,0] = r[:,:,8:0:-1]
            font[128:256,:,:,1] = g[:,:,8:0:-1]
            font[128:256,:,:,2] = b[:,:,8:0:-1]

            # First 64 are inversed
            r[bits==0] = fg[0]
            r[bits==1] = bg[0]
            g[bits==0] = fg[1]
            g[bits==1] = bg[1]
            b[bits==0] = fg[2]
            b[bits==1] = bg[2]
            font[0:64,:,:,0] = r[0:64,:,8:0:-1]
            font[0:64,:,:,1] = g[0:64,:,8:0:-1]
            font[0:64,:,:,2] = b[0:64,:,8:0:-1]

            # Next 64 are blinking!
            if reverse:
                fg, bg = bg, fg
            r[bits==0] = fg[0]
            r[bits==1] = bg[0]
            g[bits==0] = fg[1]
            g[bits==1] = bg[1]
            b[bits==0] = fg[2]
            b[bits==1] = bg[2]
            font[64:128,:,:,0] = r[0:64,:,8:0:-1]
            font[64:128,:,:,1] = g[0:64,:,8:0:-1]
            font[64:128,:,:,2] = b[0:64,:,8:0:-1]
        return font


def get_numpy_font_map_image(segment_viewer, antic_font, byte_values, style, start_byte, end_byte, bytes_per_row, num_rows, start_col, num_cols):
    width = int(antic_font.char_w * num_cols)
    height = int(num_rows * antic_font.char_h)
    log.debug("pixel width: %dx%d" % (width, height))
    array = np.empty((height, width, 3), dtype=np.uint8)

    log.debug("start byte: %s, end_byte: %s, bytes_per_row=%d num_rows=%d start_col=%d num_cols=%d" % (start_byte, end_byte, bytes_per_row, num_rows, start_col, num_cols))
    end_col = min(bytes_per_row, start_col + num_cols)
    y = 0
    e = start_byte
    f = antic_font.normal_font
    fh = antic_font.highlight_font
    fd = antic_font.data_font
    fm = antic_font.match_font
    fc = antic_font.comment_font
    char_w = antic_font.char_w
    char_h = antic_font.char_h
    mapping = segment_viewer.font_mapping.font_mapping
    for j in range(num_rows):
        x = 0
        for i in range(start_col, start_col + num_cols):
            if e + i >= end_byte or i >= end_col:
                array[y:y+char_h,x:x+char_w,:] = segment_viewer.preferences.background_color
            else:
                c = mapping[byte_values[j, i]]
                s = style[j, i]
                if s & style_bits.selected_bit_mask:
                    array[y:y+char_h,x:x+char_w,:] = fh[c]
                elif s & style_bits.match_bit_mask:
                    array[y:y+char_h,x:x+char_w,:] = fm[c]
                elif s & style_bits.comment_bit_mask:
                    array[y:y+char_h,x:x+char_w,:] = fc[c]
                elif s & style_bits.user_bit_mask:
                    array[y:y+char_h,x:x+char_w,:] = fd[c]
                else:
                    array[y:y+char_h,x:x+char_w,:] = f[c]
            x += char_w
        y += char_h
        e += bytes_per_row
    return array



font_renderer_list = [
    Mode2(),
    Mode4(),
    Mode5(),
    Mode6Upper(),
    Mode6Lower(),
    Mode7Upper(),
    Mode7Lower(),
    Apple2TextMode(),
]

valid_font_renderers = {item.name: item for item in font_renderer_list}
