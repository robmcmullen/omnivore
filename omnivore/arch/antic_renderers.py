import numpy as np

class ModeF(object):
    name = "Antic Mode F (Graphics 8, 1bpp)"
    
    def __init__(self, machine):
        self.machine = machine
    
    def get_image(self, bytes_per_row, border_width, visible_rows, byte_count, bytes, style):
        if bytes_per_row == 1:
            array = self.get_image_1(self.machine, bytes_per_row, border_width, visible_rows, byte_count, bytes, style)
        else:
            array = self.get_image_multi(self.machine, bytes_per_row, border_width, visible_rows, byte_count, bytes, style)
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
