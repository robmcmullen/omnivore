import numpy as np

try:
    import antic_speedups as speedups
except ImportError:
    speedups = None

import logging
log = logging.getLogger(__name__)


class ModeF(object):
    name = "Antic F (Gr 8, 1bpp)"
    
    def get_image(self, m, bytes_per_row, border_width, visible_rows, byte_count, bytes, style):
        if bytes_per_row == 1:
            array = self.get_image_1(m, bytes_per_row, border_width, visible_rows, byte_count, bytes, style)
        else:
            array = self.get_image_multi(m, bytes_per_row, border_width, visible_rows, byte_count, bytes, style)
        return array

    def get_image_1(self, m, bytes_per_row, border_width, nr, count, bytes, style):
        bits = np.unpackbits(bytes)
        bits = bits.reshape((-1, 8 * bytes_per_row))
        bits[bits==0]=255
        bits[bits==1]=0
        bitwidth = 8 * bytes_per_row
        border = border_width
        width = bitwidth + 2 * border
        
        array = np.empty((nr, width, 3), dtype=np.uint8)
        array[:,border:border + bitwidth,0] = bits
        array[:,border:border + bitwidth,1] = bits
        array[:,border:border + bitwidth,2] = bits
        array[:,0:border,:] = m.empty_color
        array[:,border + bitwidth:width,:] = m.empty_color
        array[count:,border:border + bitwidth,:] = m.empty_color
        
        mask = array == (255, 255, 255)
        mask = np.all(mask, axis=2)
        
        # highlight any comments
        match = style & 0x2
        style_mask = match==0x2
        # This doesn't do anything! A mask of a mask apparently doesn't work
        # array[style_mask,:,:][mask[style_mask]] = m.comment_background_color
        s = np.tile(style_mask, (mask.shape[1], 1)).T
        m2 = np.logical_and(mask, s)
        array[m2] = m.comment_background_color
        array[style_mask,0:border,:] = m.comment_background_color
        array[style_mask,border + bitwidth:width,:] = m.comment_background_color
        
        # highlight any matches
        match = style & 0x1
        style_mask = match==0x1
        s = np.tile(style_mask, (mask.shape[1], 1)).T
        m2 = np.logical_and(mask, s)
        array[m2] = m.match_background_color
        array[style_mask,0:border,:] = m.match_background_color
        array[style_mask,border + bitwidth:width,:] = m.match_background_color
        
        # highlight selection
        match = style & 0x80
        style_mask = match==0x80
        s = np.tile(style_mask, (mask.shape[1], 1)).T
        m2 = np.logical_and(mask, s)
        array[m2] = m.highlight_color
        array[style_mask,0:border,:] = m.highlight_color
        array[style_mask,border + bitwidth:width,:] = m.highlight_color

        return array
    
    def get_image_multi(self, m, bytes_per_row, border_width, nr, count, bytes, style):
        bits = np.unpackbits(bytes)
        bits = bits.reshape((-1, 8 * bytes_per_row))
        bits[bits==0]=255
        bits[bits==1]=0
        width = 8 * bytes_per_row
        bitimage = np.empty((nr, width, 3), dtype=np.uint8)
        bitimage[:,:,0] = bits
        bitimage[:,:,1] = bits
        bitimage[:,:,2] = bits
        
        array = bitimage.reshape((-1, 8, 3))
        array[count:,:,:] = m.empty_color

        mask = array == (255, 255, 255)
        mask = np.all(mask, axis=2)
        
        # highlight any comments
        match = style & 0x2
        style_mask = match==0x2
        # This doesn't do anything! A mask of a mask apparently doesn't work
        # array[style_mask,:,:][mask[style_mask]] = m.comment_background_color
        s = np.tile(style_mask, (mask.shape[1], 1)).T
        m2 = np.logical_and(mask, s)
        array[m2] = m.comment_background_color
        
        # highlight any matches
        match = style & 0x1
        style_mask = match==0x1
        s = np.tile(style_mask, (mask.shape[1], 1)).T
        m2 = np.logical_and(mask, s)
        array[m2] = m.match_background_color
        
        # highlight selection
        match = style & 0x80
        style_mask = match==0x80
        s = np.tile(style_mask, (mask.shape[1], 1)).T
        m2 = np.logical_and(mask, s)
        array[m2] = m.highlight_color

        return bitimage


class ModeE(object):
    name = "Antic E (Gr 7+, 2bpp)"
    
    def get_image(self, m, bytes_per_row, border_width, nr, count, bytes, style):
        bits = np.unpackbits(bytes)
        bits = bits.reshape((-1, 8))
        pixels = np.empty((nr * bytes_per_row, 4), dtype=np.uint8)
        pixels[:,0] = bits[:,0] * 2 + bits[:,1]
        pixels[:,1] = bits[:,2] * 2 + bits[:,3]
        pixels[:,2] = bits[:,4] * 2 + bits[:,5]
        pixels[:,3] = bits[:,6] * 2 + bits[:,7]
        
        bitimage = np.empty((nr * bytes_per_row, 4, 3), dtype=np.uint8)
        background = np.where(pixels==0)
        bitimage[background] = m.color_registers[4]
        color1 = np.where(pixels==1)
        bitimage[color1] = m.color_registers[0]
        color2 = np.where(pixels==2)
        bitimage[color2] = m.color_registers[1]
        color3 = np.where(pixels==3)
        bitimage[color3] = m.color_registers[2]
        bitimage[count:,:,:] = m.empty_color

        array = bitimage.reshape((-1, 4, 3))
        array[count:,:,:] = m.empty_color
        mask = array == m.color_registers[4]
        mask = np.all(mask, axis=2)
        
        # highlight any comments
        match = style & 0x2
        style_mask = match==0x2
        # This doesn't do anything! A mask of a mask apparently doesn't work
        # array[style_mask,:,:][mask[style_mask]] = m.comment_background_color
        s = np.tile(style_mask, (mask.shape[1], 1)).T
        m2 = np.logical_and(mask, s)
        array[m2] = m.comment_background_color
        
        # highlight any matches
        match = style & 0x1
        style_mask = match==0x1
        s = np.tile(style_mask, (mask.shape[1], 1)).T
        m2 = np.logical_and(mask, s)
        array[m2] = m.match_background_color
        
        # highlight selection
        match = style & 0x80
        style_mask = match==0x80
        s = np.tile(style_mask, (mask.shape[1], 1)).T
        m2 = np.logical_and(mask, s)
        array[m2] = m.highlight_color

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
