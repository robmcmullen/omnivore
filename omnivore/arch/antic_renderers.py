import numpy as np

try:
    import antic_speedups as speedups
except ImportError:
    speedups = None

import logging
log = logging.getLogger(__name__)


class ModeF(object):
    name = "Antic F (Gr 8, 1bpp)"
    
    def get_image(self, m, bytes_per_row, nr, count, bytes, style):
        bits = np.unpackbits(bytes)
        pixels = bits.reshape((-1, 8))

        background = (pixels == 0)
        color1 = (pixels == 1)
        
        bw_colors = ((0, 0, 0), (255, 255, 255))
        h_colors = m.get_blended_color_registers(bw_colors, m.highlight_color)
        m_colors = m.get_blended_color_registers(bw_colors, m.match_background_color)
        c_colors = m.get_blended_color_registers(bw_colors, m.comment_background_color)
        
        style_per_pixel = np.vstack((style, style, style, style, style, style, style, style)).T
        normal = style_per_pixel == 0
        highlight = (style_per_pixel & 0x80) == 0x80
        comment = (style_per_pixel & 0x2) == 0x2
        match = (style_per_pixel & 0x1) == 0x1
        
        bitimage = np.empty((nr * bytes_per_row, 8, 3), dtype=np.uint8)
        bitimage[background & normal] = bw_colors[0]
        bitimage[background & comment] = c_colors[0]
        bitimage[background & match] = m_colors[0]
        bitimage[background & highlight] = h_colors[0]
        bitimage[color1 & normal] = bw_colors[1]
        bitimage[color1 & comment] = c_colors[1]
        bitimage[color1 & match] = m_colors[1]
        bitimage[color1 & highlight] = h_colors[1]
        bitimage[count:,:,:] = m.empty_color

        return bitimage


class ModeE(object):
    name = "Antic E (Gr 7+, 2bpp)"
    
    def get_image(self, m, bytes_per_row, nr, count, bytes, style):
        bits = np.unpackbits(bytes)
        bits = bits.reshape((-1, 8))
        pixels = np.empty((nr * bytes_per_row, 4), dtype=np.uint8)
        pixels[:,0] = bits[:,0] * 2 + bits[:,1]
        pixels[:,1] = bits[:,2] * 2 + bits[:,3]
        pixels[:,2] = bits[:,4] * 2 + bits[:,5]
        pixels[:,3] = bits[:,6] * 2 + bits[:,7]
        
        background = (pixels == 0)
        color1 = (pixels == 1)
        color2 = (pixels == 2)
        color3 = (pixels == 3)
        
        style_per_pixel = np.vstack((style, style, style, style)).T
        normal = style_per_pixel == 0
        highlight = (style_per_pixel & 0x80) == 0x80
        comment = (style_per_pixel & 0x2) == 0x2
        match = (style_per_pixel & 0x1) == 0x1
        
        bitimage = np.empty((nr * bytes_per_row, 4, 3), dtype=np.uint8)
        bitimage[background & normal] = m.color_registers[4]
        bitimage[background & comment] = m.color_registers_comment[4]
        bitimage[background & match] = m.color_registers_match[4]
        bitimage[background & highlight] = m.color_registers_highlight[4]
        bitimage[color1 & normal] = m.color_registers[0]
        bitimage[color1 & comment] = m.color_registers_comment[0]
        bitimage[color1 & match] = m.color_registers_match[0]
        bitimage[color1 & highlight] = m.color_registers_highlight[0]
        bitimage[color2 & normal] = m.color_registers[1]
        bitimage[color2 & comment] = m.color_registers_comment[1]
        bitimage[color2 & match] = m.color_registers_match[1]
        bitimage[color2 & highlight] = m.color_registers_highlight[1]
        bitimage[color3 & normal] = m.color_registers[2]
        bitimage[color3 & comment] = m.color_registers_comment[2]
        bitimage[color3 & match] = m.color_registers_match[2]
        bitimage[color3 & highlight] = m.color_registers_highlight[2]
        bitimage[count:,:,:] = m.empty_color

        # create a double-width image to expand the pixels to the correct
        # aspect ratio
        newdims = np.asarray((nr * bytes_per_row, 8))
        base=np.indices(newdims)
        d = []
        d.append(base[0])
        d.append(base[1]/2)
        cd = np.array(d)
        array = bitimage[list(cd)]
        return array.reshape((nr, bytes_per_row * 8, 3))


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
                if s & 0x80:
                    array[y:y+8,x:x+8,:] = fh[c]
                elif s & 1:
                    array[y:y+8,x:x+8,:] = fm[c]
                elif s & 2:
                    array[y:y+8,x:x+8,:] = fc[c]
                else:
                    array[y:y+8,x:x+8,:] = f[c]
            x += 8
        y += 8
        e += bytes_per_row
    return array


class Mode2(object):
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



class BytePerPixelMemoryMap(object):
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
            if s & 0x80:
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
