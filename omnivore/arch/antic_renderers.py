import numpy as np

from atrcopy import match_bit_mask, comment_bit_mask, data_bit_mask, selected_bit_mask, not_user_bit_mask

try:
    import antic_speedups as speedups
except ImportError:
    speedups = None

import logging
log = logging.getLogger(__name__)


class BaseRenderer(object):
    name = "base"
    pixels_per_byte = 8
    bitplanes = 1
    
    def validate_bytes_per_row(self, bytes_per_row):
        return bytes_per_row

    def get_colors(self, m, registers):
        color_registers = [m.color_registers[r] for r in registers]
        h_colors = [m.color_registers_highlight[r] for r in registers]
        m_colors = [m.color_registers_match[r] for r in registers]
        c_colors = [m.color_registers_comment[r] for r in registers]
        d_colors = [m.color_registers_data[r] for r in registers]
        return color_registers, h_colors, m_colors, c_colors, d_colors

    def reshape(self, bitimage, bytes_per_row, nr):
        h, w, colors = bitimage.shape
        if w == self.pixels_per_byte:
            return bitimage.reshape((nr, bytes_per_row * self.pixels_per_byte, 3))
        
        # create a double-width image to expand the pixels to the correct
        # aspect ratio
        newdims = np.asarray((nr * bytes_per_row, self.pixels_per_byte))
        base=np.indices(newdims)
        d = []
        d.append(base[0])
        d.append(base[1]/(self.pixels_per_byte / w))
        cd = np.array(d)
        array = bitimage[list(cd)]
        return array.reshape((nr, bytes_per_row * self.pixels_per_byte, 3))
    
    def get_2bpp(self, m, bytes_per_row, nr, count, bytes, style, colors):
        bits = np.unpackbits(bytes)
        bits = bits.reshape((-1, 8))
        pixels = np.empty((nr * bytes_per_row, 4), dtype=np.uint8)
        pixels[:,0] = bits[:,0] * 2 + bits[:,1]
        pixels[:,1] = bits[:,2] * 2 + bits[:,3]
        pixels[:,2] = bits[:,4] * 2 + bits[:,5]
        pixels[:,3] = bits[:,6] * 2 + bits[:,7]
        
        style_per_pixel = np.vstack((style, style, style, style)).T
        normal = style_per_pixel == 0
        highlight = (style_per_pixel & selected_bit_mask) == selected_bit_mask
        data = (style_per_pixel & data_bit_mask) == data_bit_mask
        comment = (style_per_pixel & comment_bit_mask) == comment_bit_mask
        match = (style_per_pixel & match_bit_mask) == match_bit_mask
        
        color_registers, h_colors, m_colors, c_colors, d_colors = colors
        bitimage = np.empty((nr * bytes_per_row, 4, 3), dtype=np.uint8)
        for i in range(4):
            color_is_set = (pixels == i)
            bitimage[color_is_set & normal] = color_registers[i]
            bitimage[color_is_set & comment] = c_colors[i]
            bitimage[color_is_set & match] = m_colors[i]
            bitimage[color_is_set & data] = d_colors[i]
            bitimage[color_is_set & highlight] = h_colors[i]
        bitimage[count:,:,:] = m.empty_color
        return bitimage
    
    def get_4bpp(self, m, bytes_per_row, nr, count, bytes, style, colors):
        bits = np.unpackbits(bytes)
        bits = bits.reshape((-1, 8))
        pixels = np.empty((nr * bytes_per_row, 2), dtype=np.uint8)
        pixels[:,0] = bits[:,0] * 8 + bits[:,1] * 4 + bits[:,2] * 2 + bits[:,3]
        pixels[:,1] = bits[:,4] * 8 + bits[:,5] * 4 + bits[:,6] * 2 + bits[:,7]
        
        style_per_pixel = np.vstack((style, style)).T
        normal = style_per_pixel == 0
        highlight = (style_per_pixel & selected_bit_mask) == selected_bit_mask
        data = (style_per_pixel & data_bit_mask) == data_bit_mask
        comment = (style_per_pixel & comment_bit_mask) == comment_bit_mask
        match = (style_per_pixel & match_bit_mask) == match_bit_mask
        
        color_registers, h_colors, m_colors, c_colors, d_colors = colors
        bitimage = np.empty((nr * bytes_per_row, 2, 3), dtype=np.uint8)
        for i in range(16):
            color_is_set = (pixels == i)
            bitimage[color_is_set & normal] = color_registers[i]
            bitimage[color_is_set & comment] = c_colors[i]
            bitimage[color_is_set & match] = m_colors[i]
            bitimage[color_is_set & data] = d_colors[i]
            bitimage[color_is_set & highlight] = h_colors[i]
        bitimage[count:,:,:] = m.empty_color
        return bitimage
    
    def get_bitplane_pixels(self, bits, pixels, bytes_per_row, pixels_per_row):
        """Fill the pixels array with color register data
        
        pixels is passed in as an 8 pixel wide array regardless of the actual
        pixels per row. It will be resized correctly by the calling method.
        """
        raise NotImplemented
    
    def get_bitplane_style(self, style):
        raise NotImplemented
    
    def get_bitplanes(self, m, bytes_per_row, nr, count, bytes, style, colors):
        bitplanes = self.bitplanes
        _, rem = divmod(np.alen(bytes), bitplanes)
        if rem > 0:
            bytes = np.append(bytes, np.zeros(rem, dtype=np.uint8))
            style = np.append(style, np.zeros(rem, dtype=np.uint8))
        bits = np.unpackbits(bytes).reshape((-1, 8))
        pixels_per_row = 8 * bytes_per_row / bitplanes
        pixels = np.empty((nr * bytes_per_row / bitplanes, 8), dtype=np.uint8)
        self.get_bitplane_pixels(bits, pixels, bytes_per_row, pixels_per_row)
        pixels = pixels.reshape((nr, pixels_per_row))
        s = self.get_bitplane_style(style)
        style_per_pixel = s.repeat(8).reshape((-1, pixels_per_row))
        normal = style_per_pixel == 0
        highlight = (style_per_pixel & selected_bit_mask) == selected_bit_mask
        data = (style_per_pixel & data_bit_mask) == data_bit_mask
        comment = (style_per_pixel & comment_bit_mask) == comment_bit_mask
        match = (style_per_pixel & match_bit_mask) == match_bit_mask
        
        color_registers, h_colors, m_colors, c_colors, d_colors = colors
        bitimage = np.empty((nr, pixels_per_row, 3), dtype=np.uint8)
        for i in range(2**bitplanes):
            color_is_set = (pixels == i)
            bitimage[color_is_set & normal] = color_registers[i]
            bitimage[color_is_set & comment] = c_colors[i]
            bitimage[color_is_set & match] = m_colors[i]
            bitimage[color_is_set & data] = d_colors[i]
            bitimage[color_is_set & highlight] = h_colors[i]
        bitimage[count:,:,:] = m.empty_color
        return bitimage


class OneBitPerPixelB(BaseRenderer):
    name = "B/W, 1bpp, on=black"
    bw_colors = ((255, 255, 255), (0, 0, 0))
    
    def get_image(self, m, bytes_per_row, nr, count, bytes, style):
        bits = np.unpackbits(bytes)
        pixels = bits.reshape((-1, 8))

        background = (pixels == 0)
        color1 = (pixels == 1)
        
        h_colors = m.get_blended_color_registers(self.bw_colors, m.highlight_color)
        m_colors = m.get_blended_color_registers(self.bw_colors, m.match_background_color)
        c_colors = m.get_blended_color_registers(self.bw_colors, m.comment_background_color)
        d_colors = m.get_dimmed_color_registers(self.bw_colors, m.background_color, m.data_color)
        
        style_per_pixel = np.vstack((style, style, style, style, style, style, style, style)).T
        normal = (style_per_pixel & not_user_bit_mask) == 0
        highlight = (style_per_pixel & selected_bit_mask) == selected_bit_mask
        data = (style_per_pixel & data_bit_mask) == data_bit_mask
        comment = (style_per_pixel & comment_bit_mask) == comment_bit_mask
        match = (style_per_pixel & match_bit_mask) == match_bit_mask
        
        bitimage = np.empty((nr * bytes_per_row, 8, 3), dtype=np.uint8)
        bitimage[background & normal] = self.bw_colors[0]
        bitimage[background & comment] = c_colors[0]
        bitimage[background & match] = m_colors[0]
        bitimage[background & data] = d_colors[0]
        bitimage[background & highlight] = h_colors[0]
        bitimage[color1 & normal] = self.bw_colors[1]
        bitimage[color1 & comment] = c_colors[1]
        bitimage[color1 & match] = m_colors[1]
        bitimage[color1 & data] = d_colors[1]
        bitimage[color1 & highlight] = h_colors[1]
        bitimage[count:,:,:] = m.empty_color

        return bitimage.reshape((nr, bytes_per_row * 8, 3))


class OneBitPerPixelW(OneBitPerPixelB):
    name = "B/W, 1bpp, on=white"
    bw_colors = ((0, 0, 0), (255, 255, 255))


class TwoBitsPerPixel(BaseRenderer):
    name = "2bpp"
    pixels_per_byte = 4
    
    def get_image(self, m, bytes_per_row, nr, count, bytes, style):
        colors = self.get_colors(m, [0, 1, 2, 3])
        bitimage = self.get_2bpp(m, bytes_per_row, nr, count, bytes, style, colors)
        return self.reshape(bitimage, bytes_per_row, nr)


class ModeD(TwoBitsPerPixel):
    name = "Antic D (Gr 7, 2bpp)"
    pixels_per_byte = 4
    
    def get_image(self, m, bytes_per_row, nr, count, bytes, style):
        colors = self.get_colors(m, [8, 4, 5, 6])
        bitimage = self.get_2bpp(m, bytes_per_row, nr, count, bytes, style, colors)
        return self.reshape(bitimage, bytes_per_row, nr)

class ModeE(ModeD):
    name = "Antic E (Gr 7+, 2bpp)"
    pixels_per_byte = 8


class FourBitsPerPixel(BaseRenderer):
    name = "4bpp"
    pixels_per_byte = 2
    
    def get_image(self, m, bytes_per_row, nr, count, bytes, style):
        colors = self.get_colors(m, range(16))
        bitimage = self.get_4bpp(m, bytes_per_row, nr, count, bytes, style, colors)
        return self.reshape(bitimage, bytes_per_row, nr)


class TwoBitPlanesLE(BaseRenderer):
    name = "2 Bit Planes (little endian)"
    pixels_per_byte = 8
    bitplanes = 2
    
    def get_bitplane_pixels(self, bits, pixels, bytes_per_row, pixels_per_row):
        for i in range(8):
            pixels[:,i] = bits[0::2,i] + bits[1::2,i] * 2
    
    def get_bitplane_style(self, style):
        return style[0::2] | style[1::2]
    
    def validate_bytes_per_row(self, bytes_per_row):
        scale, rem = divmod(bytes_per_row, self.bitplanes)
        if rem > 0:
            bytes_per_row = (scale + 1) * self.bitplanes
        print "bytes_per_row", bytes_per_row
        return bytes_per_row
    
    def get_image(self, m, bytes_per_row, nr, count, bytes, style):
        colors = self.get_colors(m, range(2**self.bitplanes))
        bitimage = self.get_bitplanes(m, bytes_per_row, nr, count, bytes, style, colors)
        return bitimage

class TwoBitPlanesBE(TwoBitPlanesLE):
    name = "2 Bit Planes (big endian)"
    
    def get_bitplane_pixels(self, bits, pixels, bytes_per_row, pixels_per_row):
        for i in range(8):
            pixels[:,i] = bits[0::2,i] * 2 + bits[1::2,i]

class TwoBitPlanesLineLE(TwoBitPlanesLE):
    name = "2 Bit Planes (little endian, interleave by line)"
    
    def get_bitplane_pixels(self, bits, pixels, bytes_per_row, pixels_per_row):
        pixel_rows = bytes_per_row / 2
        for i in range(8):
            for j in range(pixel_rows):
                little = j
                big = j + pixel_rows
                pixels[j::pixel_rows,i] = bits[big::bytes_per_row,i] * 2 + bits[little::bytes_per_row,i]

class TwoBitPlanesLineBE(TwoBitPlanesLE):
    name = "2 Bit Planes (big endian, interleave by line)"
    
    def get_bitplane_pixels(self, bits, pixels, bytes_per_row, pixels_per_row):
        pixel_rows = bytes_per_row / 2
        for i in range(8):
            for j in range(pixel_rows):
                little = j + pixel_rows
                big = j
                pixels[j::pixel_rows,i] = bits[big::bytes_per_row,i] * 2 + bits[little::bytes_per_row,i]


class ThreeBitPlanesLE(TwoBitPlanesLE):
    name = "3 Bit Planes (little endian)"
    bitplanes = 3

    def get_bitplane_pixels(self, bits, pixels, bytes_per_row, pixels_per_row):
        for i in range(8):
            pixels[:,i] = bits[0::3,i] * 4 + bits[1::3,i] * 2 + bits[2::3,i]
    
    def get_bitplane_style(self, style):
        return style[0::3] | style[1::3] | style[2::3]

class ThreeBitPlanesBE(ThreeBitPlanesLE):
    name = "3 Bit Planes (big endian)"
    bitplanes = 3

    def get_bitplane_pixels(self, bits, pixels, bytes_per_row, pixels_per_row):
        for i in range(8):
            pixels[:,i] = bits[0::3,i] + bits[1::3,i] * 2 + bits[2::3,i] * 4

class ThreeBitPlanesLineLE(ThreeBitPlanesLE):
    name = "3 Bit Planes (little endian, interleave by line)"
    
    def get_bitplane_pixels(self, bits, pixels, bytes_per_row, pixels_per_row):
        pixel_rows = bytes_per_row / 3
        for i in range(8):
            for j in range(pixel_rows):
                little = j
                mid = j + pixel_rows
                big = j + (2 * pixel_rows)
                pixels[j::pixel_rows,i] = bits[big::bytes_per_row,i] * 4 + bits[mid::bytes_per_row,i] * 2 + bits[little::bytes_per_row,i]

class ThreeBitPlanesLineBE(ThreeBitPlanesBE):
    name = "3 Bit Planes (big endian, interleave by line)"
    
    def get_bitplane_pixels(self, bits, pixels, bytes_per_row, pixels_per_row):
        pixel_rows = bytes_per_row / 3
        for i in range(8):
            for j in range(pixel_rows):
                little = j + (2 * pixel_rows)
                mid = j + pixel_rows
                big = j
                pixels[j::pixel_rows,i] = bits[big::bytes_per_row,i] * 4 + bits[mid::bytes_per_row,i] * 2 + bits[little::bytes_per_row,i]


class FourBitPlanesLE(TwoBitPlanesLE):
    name = "4 Bit Planes (little endian)"
    bitplanes = 4
    
    def get_bitplane_pixels(self, bits, pixels, bytes_per_row, pixels_per_row):
        for i in range(8):
            pixels[:,i] = bits[0::4,i] * 8 + bits[1::4,i] * 4 + bits[2::4,i] * 2 + bits[3::4,i]
    
    def get_bitplane_style(self, style):
        return style[0::4] | style[1::4] | style[2::4] | style[3::4]

class FourBitPlanesBE(FourBitPlanesLE):
    name = "4 Bit Planes (big endian)"

    def get_bitplane_pixels(self, bits, pixels, bytes_per_row, pixels_per_row):
        for i in range(8):
            pixels[:,i] = bits[0::4,i] + bits[1::4,i] * 2 + bits[2::4,i] * 4 + bits[3::4,i] * 8

class FourBitPlanesLineLE(FourBitPlanesLE):
    name = "4 Bit Planes (little endian, interleave by line)"
    
    def get_bitplane_pixels(self, bits, pixels, bytes_per_row, pixels_per_row):
        pixel_rows = bytes_per_row / 4
        for i in range(8):
            for j in range(pixel_rows):
                little = j
                little_mid = j + pixel_rows
                big_mid = j + (2 * pixel_rows)
                big = j + (3 * pixel_rows)
                pixels[j::pixel_rows,i] = bits[big::bytes_per_row,i] * 8 + bits[big_mid::bytes_per_row,i] * 4 + bits[little_mid::bytes_per_row,i] * 2 + bits[little::bytes_per_row,i]

class FourBitPlanesLineBE(FourBitPlanesLE):
    name = "4 Bit Planes (big endian, interleave by line)"
    
    def get_bitplane_pixels(self, bits, pixels, bytes_per_row, pixels_per_row):
        pixel_rows = bytes_per_row / 4
        for i in range(8):
            for j in range(pixel_rows):
                little = j + (3 * pixel_rows)
                little_mid = j + (2 * pixel_rows)
                big_mid = j + pixel_rows 
                big = j
                pixels[j::pixel_rows,i] = bits[big::bytes_per_row,i] * 8 + bits[big_mid::bytes_per_row,i] * 4 + bits[little_mid::bytes_per_row,i] * 2 + bits[little::bytes_per_row,i]


class GTIA9(FourBitsPerPixel):
    name = "GTIA 9 (4bpp, 16 luminances, 1 color)"
    pixels_per_byte = 8
    
    def get_antic_color_registers(self, m):
        first_color = m.antic_color_registers[8] & 0xf0
        return range(first_color, first_color + 16)
    
    def get_colors(self, m, registers):
        antic_color_registers = self.get_antic_color_registers(m)
        color_registers = m.get_color_registers(antic_color_registers)
        h_colors = m.get_blended_color_registers(color_registers, m.highlight_color)
        m_colors = m.get_blended_color_registers(color_registers, m.match_background_color)
        c_colors = m.get_blended_color_registers(color_registers, m.comment_background_color)
        d_colors = m.get_dimmed_color_registers(color_registers, m.background_color, m.data_color)
        return color_registers, h_colors, m_colors, c_colors, d_colors


class GTIA10(GTIA9):
    name = "GTIA 10 (4bpp, 9 colors)"
    
    def get_antic_color_registers(self, m):
        return list(m.antic_color_registers[0:9]) + [0] * 7


class GTIA11(GTIA9):
    name = "GTIA 11 (4bpp, 1 luminace, 16 colors)"
    
    def get_antic_color_registers(self, m):
        first_color = m.antic_color_registers[8] & 0x0f
        return range(first_color, first_color + 256, 16)


def get_numpy_font_map_image(m, bytes, style, start_byte, end_byte, bytes_per_row, num_rows, start_col, num_cols):
    width = int(m.antic_font.char_w * num_cols)
    height = int(num_rows * m.antic_font.char_h)
    log.debug("pixel width: %dx%d" % (width, height))
    array = np.empty((height, width, 3), dtype=np.uint8)
    
    log.debug("start byte: %s, end_byte: %s, bytes_per_row=%d num_rows=%d start_col=%d num_cols=%d" % (start_byte, end_byte, bytes_per_row, num_rows, start_col, num_cols))
    end_col = min(bytes_per_row, start_col + num_cols)
    y = 0
    e = start_byte
    f = m.antic_font.normal_font
    fh = m.antic_font.highlight_font
    fd = m.antic_font.data_font
    fm = m.antic_font.match_font
    fc = m.antic_font.comment_font
    mapping = m.font_mapping.font_mapping
    for j in range(num_rows):
        x = 0
        for i in range(start_col, start_col + num_cols):
            if e + i >= end_byte or i >= end_col:
                array[y:y+8,x:x+8,:] = m.background_color
            else:
                c = mapping[bytes[j, i]]
                s = style[j, i]
                if s & selected_bit_mask:
                    array[y:y+8,x:x+8,:] = fh[c]
                elif s & match_bit_mask:
                    array[y:y+8,x:x+8,:] = fm[c]
                elif s & comment_bit_mask:
                    array[y:y+8,x:x+8,:] = fc[c]
                elif s & data_bit_mask:
                    array[y:y+8,x:x+8,:] = fd[c]
                else:
                    array[y:y+8,x:x+8,:] = f[c]
            x += 8
        y += 8
        e += bytes_per_row
    return array


class Mode2(BaseRenderer):
    name = "Antic 2 (Gr 0)"
    font_mode = 2
    
    @classmethod
    def get_image(cls, machine, bytes, style, start_byte, end_byte, bytes_per_row, nr, start_col, visible_cols):
        if speedups is not None:
            array = speedups.get_numpy_font_map_image(machine, bytes, style, start_byte, end_byte, bytes_per_row, nr, start_col, visible_cols)
        else:
            array = get_numpy_font_map_image(machine, bytes, style, start_byte, end_byte, bytes_per_row, nr, start_col, visible_cols)
        return array


class Mode4(Mode2):
    name = "Antic 4 (40x24, 5 color)"
    font_mode = 4


class Mode5(Mode2):
    name = "Antic 5 (40x12, 5 color)"
    font_mode = 5


class Mode6Upper(Mode2):
    name = "Antic 6 (Gr 1) Uppercase and Numbers"
    font_mode = 6


class Mode6Lower(Mode2):
    name = "Antic 6 (Gr 1) Lowercase and Symbols"
    font_mode = 8


class Mode7Upper(Mode2):
    name = "Antic 7 (Gr 2) Uppercase and Numbers"
    font_mode = 7


class Mode7Lower(Mode2):
    name = "Antic 7 (Gr 2) Lowercase and Symbols"
    font_mode = 9


class ATASCIIFontMapping(object):
    name = "ATASCII Characters"
    font_mapping = np.hstack([np.arange(64, 96, dtype=np.uint8),np.arange(64, dtype=np.uint8),np.arange(96, 128, dtype=np.uint8)])
    font_mapping = np.hstack([font_mapping, font_mapping + 128])

class AnticFontMapping(object):
    name = "Antic Map"
    font_mapping = np.arange(256, dtype=np.uint8)



class BytePerPixelMemoryMap(BaseRenderer):
    name = "1Bpp Greyscale"
    
    def get_image(self, m, bytes, style, start_byte, end_byte, bytes_per_row, nr, start_col, visible_cols):
        if speedups is not None:
            array = speedups.get_numpy_memory_map_image(m, bytes, style, start_byte, end_byte, bytes_per_row, nr, start_col, visible_cols)
        else:
            array = get_numpy_memory_map_image(m, bytes, style, start_byte, end_byte, bytes_per_row, nr, start_col, visible_cols)
        return array

def get_numpy_memory_map_image(m, bytes, style, start_byte, end_byte, bytes_per_row, num_rows, start_col, num_cols):
    log.debug("SLOW VERSION OF get_numpy_memory_map_image!!!")
    num_rows_with_data = (end_byte - start_byte + bytes_per_row - 1) / bytes_per_row
    
    log.debug(str([end_byte, start_byte, (end_byte - start_byte) / bytes_per_row]))
    end_row = min(num_rows_with_data, num_rows)
    end_col = min(bytes_per_row, start_col + num_cols)
    
    width = end_col - start_col
    height = num_rows_with_data
    log.debug("memory map size: %dx%d, rows with data=%d, rows %d, cols %d-%d" % (width, height, num_rows_with_data, num_rows, start_col, start_col + width - 1))
    array = np.empty((height, width, 3), dtype=np.uint8)
    array[:,:] = m.empty_color
    selected_color = m.highlight_color
    
    y = 0
    e = start_byte
    for j in range(end_row):
        x = 0
        for i in range(start_col, end_col):
            if e + i >= end_byte:
                break
            c = bytes[j, i] ^ 0xff
            s = style[j, i]
            if s & selected_bit_mask:
                r = selected_color[0] * c >> 8
                g = selected_color[1] * c >> 8
                b = selected_color[2] * c >> 8
                array[y,x,:] = (r, g, b)
            else:
                array[y,x,:] = (c, c, c)
            x += 1
        y += 1
        e += bytes_per_row
    return array
