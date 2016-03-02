import numpy as np
import wx

import colors

# Font is a dict (easily serializable with JSON) with the following attributes:
#    data: string containing font data
#    name: human readable name
#    x_bits: number of bits to display
#    y_bytes: number of bytes per character
#
# template:
# Font = {
#    'data': ,
#    'name':"Default Atari Font",
#    'char_w': 8,
#    'char_h': 8,
#    }

A8DefaultFont = {
    'data': '\x00\x00\x00\x00\x00\x00\x00\x00\x00\x18\x18\x18\x18\x00\x18\x00\x00fff\x00\x00\x00\x00\x00f\xffff\xfff\x00\x18>`<\x06|\x18\x00\x00fl\x180fF\x00\x1c6\x1c8of;\x00\x00\x18\x18\x18\x00\x00\x00\x00\x00\x0e\x1c\x18\x18\x1c\x0e\x00\x00p8\x18\x188p\x00\x00f<\xff<f\x00\x00\x00\x18\x18~\x18\x18\x00\x00\x00\x00\x00\x00\x00\x18\x180\x00\x00\x00~\x00\x00\x00\x00\x00\x00\x00\x00\x00\x18\x18\x00\x00\x06\x0c\x180`@\x00\x00<fnvf<\x00\x00\x188\x18\x18\x18~\x00\x00<f\x0c\x180~\x00\x00~\x0c\x18\x0cf<\x00\x00\x0c\x1c<l~\x0c\x00\x00~`|\x06f<\x00\x00<`|ff<\x00\x00~\x06\x0c\x1800\x00\x00<f<ff<\x00\x00<f>\x06\x0c8\x00\x00\x00\x18\x18\x00\x18\x18\x00\x00\x00\x18\x18\x00\x18\x180\x06\x0c\x180\x18\x0c\x06\x00\x00\x00~\x00\x00~\x00\x00`0\x18\x0c\x180`\x00\x00<f\x0c\x18\x00\x18\x00\x00<fnn`>\x00\x00\x18<ff~f\x00\x00|f|ff|\x00\x00<f``f<\x00\x00xlfflx\x00\x00~`|``~\x00\x00~`|```\x00\x00>``nf>\x00\x00ff~fff\x00\x00~\x18\x18\x18\x18~\x00\x00\x06\x06\x06\x06f<\x00\x00flxxlf\x00\x00`````~\x00\x00cw\x7fkcc\x00\x00fv~~nf\x00\x00<ffff<\x00\x00|ff|``\x00\x00<fffl6\x00\x00|ff|lf\x00\x00<`<\x06\x06<\x00\x00~\x18\x18\x18\x18\x18\x00\x00fffff~\x00\x00ffff<\x18\x00\x00cck\x7fwc\x00\x00ff<<ff\x00\x00ff<\x18\x18\x18\x00\x00~\x0c\x180`~\x00\x00\x1e\x18\x18\x18\x18\x1e\x00\x00@`0\x18\x0c\x06\x00\x00x\x18\x18\x18\x18x\x00\x00\x08\x1c6c\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\x00\x006\x7f\x7f>\x1c\x08\x00\x18\x18\x18\x1f\x1f\x18\x18\x18\x03\x03\x03\x03\x03\x03\x03\x03\x18\x18\x18\xf8\xf8\x00\x00\x00\x18\x18\x18\xf8\xf8\x18\x18\x18\x00\x00\x00\xf8\xf8\x18\x18\x18\x03\x07\x0e\x1c8p\xe0\xc0\xc0\xe0p8\x1c\x0e\x07\x03\x01\x03\x07\x0f\x1f?\x7f\xff\x00\x00\x00\x00\x0f\x0f\x0f\x0f\x80\xc0\xe0\xf0\xf8\xfc\xfe\xff\x0f\x0f\x0f\x0f\x00\x00\x00\x00\xf0\xf0\xf0\xf0\x00\x00\x00\x00\xff\xff\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xff\x00\x00\x00\x00\xf0\xf0\xf0\xf0\x00\x1c\x1cww\x08\x1c\x00\x00\x00\x00\x1f\x1f\x18\x18\x18\x00\x00\x00\xff\xff\x00\x00\x00\x18\x18\x18\xff\xff\x18\x18\x18\x00\x00<~~~<\x00\x00\x00\x00\x00\xff\xff\xff\xff\xc0\xc0\xc0\xc0\xc0\xc0\xc0\xc0\x00\x00\x00\xff\xff\x18\x18\x18\x18\x18\x18\xff\xff\x00\x00\x00\xf0\xf0\xf0\xf0\xf0\xf0\xf0\xf0\x18\x18\x18\x1f\x1f\x00\x00\x00x`x`~\x18\x1e\x00\x00\x18<~\x18\x18\x18\x00\x00\x18\x18\x18~<\x18\x00\x00\x180~0\x18\x00\x00\x00\x18\x0c~\x0c\x18\x00\x00\x00\x18<~~<\x18\x00\x00\x00<\x06>f>\x00\x00``|ff|\x00\x00\x00<```<\x00\x00\x06\x06>ff>\x00\x00\x00<f~`<\x00\x00\x0e\x18>\x18\x18\x18\x00\x00\x00>ff>\x06|\x00``|fff\x00\x00\x18\x008\x18\x18<\x00\x00\x06\x00\x06\x06\x06\x06<\x00``lxlf\x00\x008\x18\x18\x18\x18<\x00\x00\x00f\x7f\x7fkc\x00\x00\x00|ffff\x00\x00\x00<fff<\x00\x00\x00|ff|``\x00\x00>ff>\x06\x06\x00\x00|f```\x00\x00\x00>`<\x06|\x00\x00\x18~\x18\x18\x18\x0e\x00\x00\x00ffff>\x00\x00\x00fff<\x18\x00\x00\x00ck\x7f>6\x00\x00\x00f<\x18<f\x00\x00\x00fff>\x0cx\x00\x00~\x0c\x180~\x00\x00\x18<~~\x18<\x00\x18\x18\x18\x18\x18\x18\x18\x18\x00~x|nf\x06\x00\x08\x188x8\x18\x08\x00\x10\x18\x1c\x1e\x1c\x18\x10\x00',
    'name': "Default Atari Font",
    'char_w': 8,
    'char_h': 8,
    }

A8ComputerFont = {
    'data': '\x00\x00\x00\x00\x00\x00\x00\x0088\x18\x18\x00\x18\x18\x00\xee\xeeDD\x00\x00\x00\x00f\xffff\xfff\x00\x00\x18>`<\x06|\x18\x00\x00fl\x180fF\x00\x1c6\x1c8of;\x00\x18\x18\x18\x00\x00\x00\x00\x00\x1e\x18\x18888>\x00x\x18\x18\x1c\x1c\x1c|\x00\x00f<\xff<f\x00\x00\x00\x18\x18~\x18\x18\x00\x00\x00\x00\x00\x00\x00\x18\x180\x00\x00\x00~\x00\x00\x00\x00\x00\x00\x00\x00\x00\x18\x18\x00\x03\x06\x0c\x180`@\x00\x7fccccc\x7f\x008\x18\x18\x18>>>\x00\x7f\x03\x03\x7f``\x7f\x00~\x06\x06\x7f\x07\x07\x7f\x00ppppw\x7f\x07\x00\x7f``\x7f\x03\x03\x7f\x00|l`\x7fcc\x7f\x00\x7f\x03\x03\x1f\x18\x18\x18\x00>66\x7fww\x7f\x00\x7fcc\x7f\x07\x07\x07\x00<<<\x00<<<\x00<<<\x00<<\x180\x06\x0c\x180\x18\x0c\x06\x00\x00~\x00\x00~\x00\x00\x00`0\x18\x0c\x180`\x00\x7fc\x03\x1f\x1c\x00\x1c\x00\x7fcooo`\x7f\x00?33\x7fsss\x00~ff\x7fgg\x7f\x00\x7fgg`cc\x7f\x00~ffwww\x7f\x00\x7f``\x7fpp\x7f\x00\x7f``\x7fppp\x00\x7fc`ogg\x7f\x00sss\x7fsss\x00\x7f\x1c\x1c\x1c\x1c\x1c\x7f\x00\x0c\x0c\x0c\x0e\x0en~\x00ffl\x7fggg\x00000ppp~\x00g\x7f\x7fwggg\x00gw\x7foggg\x00\x7fccggg\x7f\x00\x7fcc\x7fppp\x00\x7fccggg\x7f\x07~ff\x7fwww\x00\x7f`\x7f\x03ss\x7f\x00\x7f\x1c\x1c\x1c\x1c\x1c\x1c\x00gggggg\x7f\x00ggggo>\x1c\x00gggo\x7f\x7fg\x00sss>ggg\x00ggg\x7f\x1c\x1c\x1c\x00\x7ffl\x187g\x7f\x00\x1e\x18\x18\x18\x18\x18\x1e\x00@`0\x18\x0c\x06\x03\x00x\x18\x18\x18\x18\x18x\x00\x00\x08\x1c6c\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\x00\x006\x7f\x7f>\x1c\x08\x00\x18\x18\x18\x1f\x1f\x18\x18\x18\x03\x03\x03\x03\x03\x03\x03\x03\x18\x18\x18\xf8\xf8\x00\x00\x00\x18\x18\x18\xf8\xf8\x18\x18\x18\x00\x00\x00\xf8\xf8\x18\x18\x18\x03\x07\x0e\x1c8p\xe0\xc0\xc0\xe0p8\x1c\x0e\x07\x03\x01\x03\x07\x0f\x1f?\x7f\xff\x00\x00\x00\x00\x0f\x0f\x0f\x0f\x80\xc0\xe0\xf0\xf8\xfc\xfe\xff\x0f\x0f\x0f\x0f\x00\x00\x00\x00\xf0\xf0\xf0\xf0\x00\x00\x00\x00\xff\xff\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xff\x00\x00\x00\x00\xf0\xf0\xf0\xf0\x00\x1c\x1cww\x08\x1c\x00\x00\x00\x00\x1f\x1f\x18\x18\x18\x00\x00\x00\xff\xff\x00\x00\x00\x18\x18\x18\xff\xff\x18\x18\x18\x00\x00<~~~<\x00\x00\x00\x00\x00\xff\xff\xff\xff\xc0\xc0\xc0\xc0\xc0\xc0\xc0\xc0\x00\x00\x00\xff\xff\x18\x18\x18\x18\x18\x18\xff\xff\x00\x00\x00\xf0\xf0\xf0\xf0\xf0\xf0\xf0\xf0\x18\x18\x18\x1f\x1f\x00\x00\x00x`x`~\x18\x1e\x00\x00\x18<~\x18\x18\x18\x00\x00\x18\x18\x18~<\x18\x00\x00\x180~0\x18\x00\x00\x00\x18\x0c~\x0c\x18\x00\x00\x00\x18<~~<\x18\x00\x00\x00>\x02~v~\x00```~fn~\x00\x00\x00>20:>\x00\x06\x06\x06~fv~\x00\x00\x00~f~p~\x00\x00\x1e\x18>\x18\x1c\x1c\x00\x00\x00~fv~\x06~```~fvv\x00\x00\x18\x00\x18\x18\x1c\x1c\x00\x00\x0c\x00\x0c\x0c\x0e\x0e~\x00006|vw\x00\x00\x18\x18\x18\x1e\x1e\x1e\x00\x00\x00f\x7f\x7fkc\x00\x00\x00|fvvv\x00\x00\x00~fvv~\x00\x00\x00~fv~``\x00\x00~fn~\x06\x06\x00\x00>0888\x00\x00\x00> >\x0e~\x00\x00\x18~\x18\x1c\x1c\x1c\x00\x00\x00ffnn~\x00\x00\x00fnn>\x1c\x00\x00\x00ck\x7f>6\x00\x00\x00f>\x18>n\x00\x00\x00fff~\x0e~\x00\x00~\x1c\x186~\x00\x00\x18<~~\x18<\x00\x18\x18\x18\x18\x18\x18\x18\x18\x00~x|nf\x06\x00\x08\x188x8\x18\x08\x00\x10\x18\x1c\x1e\x1c\x18\x10\x00',
    'name': "Computer",
    'char_w': 8,
    'char_h': 8,
    }


class AnticFont(object):
    font_width_scale = [0, 0, 1, 0, 1, 1, 2, 2, 2, 2]
    font_height_scale = [0, 0, 1, 0, 1, 2, 1, 2, 1, 2]
    
    def __init__(self, machine, font_data, font_mode, playfield_colors):
        self.char_w = font_data['char_w']
        self.char_h = font_data['char_h']
        self.scale_w = self.font_width_scale[font_mode]
        self.scale_h = self.font_height_scale[font_mode]
        
        self.set_colors(machine, playfield_colors)
        self.set_fonts(machine, font_data, font_mode)
    
    def set_colors(self, machine, playfield_colors):
        fg, bg = colors.gr0_colors(playfield_colors)
        conv = machine.get_color_converter()
        fg = conv(fg)
        bg = conv(bg)
        self.normal_gr0_colors = [fg, bg]
        self.highlight_gr0_colors = machine.get_blended_color_registers(self.normal_gr0_colors, machine.highlight_color)
        self.match_gr0_colors = machine.get_blended_color_registers(self.normal_gr0_colors, machine.match_background_color)
        self.comment_gr0_colors = machine.get_blended_color_registers(self.normal_gr0_colors, machine.comment_background_color)
    
    def set_fonts(self, machine, font_data, font_mode):
        if 'np_data' in font_data:
            bytes = font_data['np_data']
        else:
            bytes = np.fromstring(font_data['data'], dtype=np.uint8)
        bits = np.unpackbits(bytes)
        bits = bits.reshape((-1, 8, 8))
        
        bits_to_font = self.get_bits_to_font_function(font_mode)
        self.normal_font = bits_to_font(bits, font_mode, machine.color_registers, self.normal_gr0_colors)
        self.highlight_font = bits_to_font(bits, font_mode, machine.color_registers_highlight, self.highlight_gr0_colors)
        self.match_font = bits_to_font(bits, font_mode, machine.color_registers_match, self.match_gr0_colors)
        self.comment_font = bits_to_font(bits, font_mode, machine.color_registers_comment, self.comment_gr0_colors)
    
    def get_bits_to_font_function(self, font_mode):
        if font_mode == 2:
            return self.bits_to_gr0
        elif font_mode < 6:
            return self.bits_to_antic4
        else:
            return self.bits_to_gr1
        
    def bits_to_gr0(self, bits, font_mode, colors, gr0_colors):
        fg, bg = gr0_colors
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
        font[0:128,:,:,0] = r
        font[0:128,:,:,1] = g
        font[0:128,:,:,2] = b
        
        # Inverse characters when high bit set
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
        
    def bits_to_gr1(self, bits, font_mode, colors, gr0_colors):
        bg = colors[8]
        if font_mode == 6 or font_mode == 7:
            half = bits[0:64,:,:]
        else:
            half = bits[64:128,:,:]
        r = np.empty(half.shape, dtype=np.uint8)
        g = np.empty(half.shape, dtype=np.uint8)
        b = np.empty(half.shape, dtype=np.uint8)
        font = np.zeros((256, 8, 8, 3), dtype=np.uint8)

        start_char = 0
        for i in range(4, 8):
            end_char = start_char + 64
            fg = colors[i]
            r[half==0] = bg[0]
            r[half==1] = fg[0]
            g[half==0] = bg[1]
            g[half==1] = fg[1]
            b[half==0] = bg[2]
            b[half==1] = fg[2]
            font[start_char:end_char,:,:,0] = r
            font[start_char:end_char,:,:,1] = g
            font[start_char:end_char,:,:,2] = b
            start_char = end_char
        return font
        
    def bits_to_antic4(self, bits, font_mode, colors, gr0_colors):
        """ http://www.atarimagazines.com/compute/issue49/419_1_Graphics_0_Text_In_Four_Colors.php
        
        There are four possible combinations of two bits: 00, 01, 10, 11. Each combination represents a different color. The color corresponding to the bit-pair 00 is stored at location 712; the color for the bit-pair 01 is at location 708; the color for bit-pair 10 is at 709; the color for bit-pair 11 is at 710.
        """
        _, _, _, _, pf0, pf1, pf2, pf3, bak = colors
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
        newdims = np.asarray((256, 8, 8))
        base=np.indices(newdims)
        d = []
        d.append(base[0])
        d.append(base[1])
        d.append(base[2]/2)
        cd = np.array(d)
        array = font[list(cd)]
        return array
    
    def get_height(self, zoom):
        return self.char_h * self.scale_h * zoom
    
    def get_image(self, char_index, zoom, highlight=False):
        f = self.highlight_font if highlight else self.normal_font
        array = f[char_index]
        w = self.char_w
        h = self.char_h
        image = wx.EmptyImage(w, h)
        image.SetData(array.tostring())
        w *= self.scale_w * zoom
        h *= self.scale_h * zoom
        image.Rescale(w, h)
        bmp = wx.BitmapFromImage(image)
        return bmp
