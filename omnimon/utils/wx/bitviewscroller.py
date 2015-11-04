#-----------------------------------------------------------------------------
# Name:        bitviewscroller.py
# Purpose:     scrolling container for bit patterns
#
# Author:      Rob McMullen
#
# Created:     2014
# RCS-ID:      $Id: $
# Copyright:   (c) 2014 Rob McMullen
# License:     wxWidgets
#-----------------------------------------------------------------------------
"""BitviewScroller -- a container for viewing bit patterns

"""

import os
import time

import numpy as np
import wx
import wx.lib.newevent

import omnimon.utils.fonts as fonts
import omnimon.utils.colors as colors

try:
    import bitviewscroller_speedups as speedups
except ImportError:
    speedups = None

import logging
log = logging.getLogger(__name__)

class BitviewEvent(wx.PyCommandEvent):
    """Event sent when a LayerControl is changed."""

    def __init__(self, eventType, id, byte, bit):
        wx.PyCommandEvent.__init__(self, eventType, id)
        self.byte = byte
        self.bit = bit


class BitviewScroller(wx.ScrolledWindow):
    dbg_call_seq = 0
    
    def __init__(self, parent, task, **kwargs):
        wx.ScrolledWindow.__init__(self, parent, -1, **kwargs)

        # Settings
        self.task = task
        self.editor = None
        self.background_color = None
        self.max_zoom = 16
        self.min_zoom = 1
        self.bytes_per_row = 1

        # internal storage
        self.bytes = None
        self.start_addr = 0
        self.start_byte = None
        self.end_byte = None
        self.img = None
        self.scaled_bmp = None
        self.grid_width = 0
        self.grid_height = 0
        self.zoom = 5
        
        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_SIZE, self.on_resize)
        self.Bind(wx.EVT_MOUSEWHEEL, self.on_mouse_wheel)
        self.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
        self.Bind(wx.EVT_MOTION, self.on_motion)
        self.Bind(wx.EVT_RIGHT_DOWN, self.on_popup)
        self.Bind(wx.EVT_MENU, self.on_menu)
    
    def set_task(self, task):
        self.task = task
    
    def recalc_view(self):
        editor = self.task.active_editor
        if editor is not None:
            self.editor = editor
            self.bytes = editor.segment.data
            self.start_addr = editor.segment.start_addr
            self.background_color = self.editor.empty_color
            self.set_colors()
            self.set_font()
            self.set_scale()
    
    def set_colors(self):
        pass
    
    def set_font(self):
        pass

    def zoom_in(self, zoom=1):
        self.zoom += zoom
        if self.zoom > self.max_zoom:
            self.zoom = self.max_zoom
        self.set_scale()
        
    def zoom_out(self, zoom=1):
        self.zoom -= zoom
        if self.zoom < self.min_zoom:
            self.zoom = self.min_zoom
        self.set_scale()
    
    def get_zoom_factors(self):
        return self.zoom, self.zoom

    def get_image(self):
        log.debug("get_image: bit image: start=%d, num=%d" % (self.start_row, self.visible_rows))
        sr = self.start_row
        nr = self.visible_rows
        self.start_byte = sr * self.bytes_per_row
        self.end_byte = self.start_byte + (nr * self.bytes_per_row)
        if self.end_byte > self.bytes.size:
            self.end_byte = self.bytes.size
            count = self.end_byte - self.start_byte
            bytes = np.zeros((nr * self.bytes_per_row), dtype=np.uint8)
            bytes[0:count] = self.bytes[self.start_byte:self.end_byte]
        else:
            count = self.end_byte - self.start_byte
            bytes = self.bytes[self.start_byte:self.end_byte]
        bits = np.unpackbits(bytes)
        bits = bits.reshape((-1, 8 * self.bytes_per_row))
        bits[bits==0]=255
        bits[bits==1]=0
        width = 8 * self.bytes_per_row
        array = np.zeros((nr, width, 3), dtype=np.uint8)
        array[:,:,0] = bits
        array[:,:,1] = bits
        array[:,:,2] = bits
        e = self.editor
        if e.anchor_start_index != e.anchor_end_index:
            start_index, end_index = e.anchor_start_index, e.anchor_end_index
            if start_index > end_index:
                start_index, end_index = end_index, start_index
            start_highlight = max(start_index - self.start_byte, 0)
            end_highlight = min(end_index - self.start_byte, count)
            log.debug("highlight %d-%d" % (start_highlight, end_highlight))
            if start_highlight < count and end_highlight >= 0:
                # change all white pixels to the highlight color.  The mask
                # must be collapsed on the color axis to result in one entry
                # per row so it can be applied to the array.
                mask = array[start_highlight:end_highlight,:,:] == (255, 255, 255)
                mask = np.all(mask, axis=2)
                array[start_highlight:end_highlight,:,:][mask] = self.editor.highlight_color
        return array

    def copy_to_clipboard(self):
        """Copies current image to clipboard.

        Copies the current image, including scaling, zooming, etc. to
        the clipboard.
        """
        bmpdo = wx.BitmapDataObject(self.scaled_bmp)
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(bmpdo)
            wx.TheClipboard.Close()

    def prepare_image(self):
        """Creates new image at specified zoom factor.

        Creates a new image that is to be used as the background of
        the scrolled bitmap.  Currently, actually creates the entire
        image, which could lead to memory problems if the image is
        really huge and the zoom factor is large.
        """
        if self.bytes is not None:
            self.calc_image_size()
            
            w, h = self.GetClientSizeTuple()
            dc = wx.MemoryDC()
            self.scaled_bmp = wx.EmptyBitmap(w, h)
            
            dc.SelectObject(self.scaled_bmp)
            dc.SetBackground(wx.Brush(self.background_color))
            dc.Clear()
            
            array = self.get_image()
            width = array.shape[1]
            height = array.shape[0]
            if width > 0 and height > 0:
                image = wx.EmptyImage(width, height)
                image.SetData(array.tostring())
                zw, zh = self.get_zoom_factors()
                image.Rescale(width * zw, height * zh)
                bmp = wx.BitmapFromImage(image)
                dc.DrawBitmap(bmp, 0, 0)
    
    def calc_image_size(self):
        x, y = self.GetViewStart()
        w, h = self.GetClientSizeTuple()
        self.start_row = y
        
        # For proper buffered paiting, the visible_rows must include the
        # (possibly) partially obscured last row.  fully_visible_rows
        # indicates the number of rows without that last partially obscured
        # row (if it exists).
        self.fully_visible_rows = h / self.zoom
        self.visible_rows = ((h + self.zoom - 1) / self.zoom)
        log.debug("x, y, w, h, start, num: %s" % str([x, y, w, h, self.start_row, self.visible_rows]))

    def set_scale(self):
        """Creates new image at specified zoom factor.

        Creates a new image that is to be used as the background of
        the scrolled bitmap.  Currently, actually creates the entire
        image, which could lead to memory problems if the image is
        really huge and the zoom factor is large.
        """
        if self.bytes is not None:
            self.calc_scale_from_bytes()
        else:
            self.grid_width = 10
            self.grid_height = 10
        log.debug("set_scale: %s" % str([self.grid_width, self.grid_height]))
        self.calc_scroll_params()
        self.Refresh()
    
    def calc_scale_from_bytes(self):
        self.total_rows = (self.bytes.size + self.bytes_per_row - 1) / self.bytes_per_row
        self.grid_width = int(8 * self.bytes_per_row)
        self.grid_height = int(self.total_rows)
    
    def calc_scroll_params(self):
        self.SetVirtualSize((self.grid_width * self.zoom, self.grid_height * self.zoom))
        rate = int(self.zoom)
        if rate < 1:
            rate = 1
        self.SetScrollRate(rate, rate)

    def event_coords_to_byte(self, evt):
        """Convert event coordinates to world coordinates.

        Convert the event coordinates to world coordinates by locating
        the offset of the scrolled window's viewport and adjusting the
        event coordinates.
        """
        if self.end_byte is None:  # end_byte is a proxy for the image being loaded
            return 0, 0, False
        
        inside = True

        x, y = self.GetViewStart()
        x = (evt.GetX() // self.zoom) + x
        y = (evt.GetY() // self.zoom) + y
        xbyte = (x // 8)
        if x < 0 or xbyte >= self.bytes_per_row or y < 0 or y > (self.start_row + self.visible_rows):
            inside = False
        byte = (self.bytes_per_row * y) + xbyte
        if byte > self.end_byte:
            inside = False
        bit = 7 - (x & 7)
        return byte, bit, inside
    
    def byte_to_row_col(self, addr):
        r = addr // self.bytes_per_row
        c = addr - (r * self.bytes_per_row)
        return r, c
    
    def select_index(self, rel_pos):
        r, c = self.byte_to_row_col(rel_pos)
#        print "r, c, start, vis", r, c, self.start_row, self.fully_visible_rows
        last_row = self.start_row + self.fully_visible_rows - 1
        if r < self.start_row:
            # above current view
            self.Scroll(c, r)
        elif r >= self.start_row and r < last_row:
            # row is already visible, but column may not be
            self.Scroll(c, self.start_row)
        elif r >= last_row:
            last_scroll_row = self.total_rows - self.fully_visible_rows
            if r >= last_scroll_row:
                self.Scroll(c, last_scroll_row)
            elif r >= self.fully_visible_rows:
                self.Scroll(c, r - self.fully_visible_rows + 1)
#        x, y = self.GetViewStart()
#        print "new row start:", y
        self.Refresh()
    
    def select_addr(self, addr):
        rel_pos = addr - self.start_addr
        self.select_index(rel_pos)

    def on_mouse_wheel(self, evt):
        """Driver to process mouse events.

        This is the main driver to process all mouse events that
        happen on the BitmapScroller.  Once a selector is triggered by
        its event combination, it becomes the active selector and
        further mouse events are directed to its handler.
        """
        if self.end_byte is None:  # end_byte is a proxy for the image being loaded
            return
        
        w = evt.GetWheelRotation()
        if evt.ControlDown():
            if w < 0:
                self.zoom_out()
            elif w > 0:
                self.zoom_in()

        evt.Skip()

    def on_left_down(self, evt):
        byte, bit, inside = self.event_coords_to_byte(evt)
        if inside:
            e = self.editor
            e.anchor_start_index = e.anchor_initial_start_index = byte
            e.anchor_end_index = e.anchor_initial_end_index = byte + 1
            wx.CallAfter(self.task.active_editor.index_clicked, e.anchor_start_index, bit, self)
            wx.CallAfter(self.Refresh)
        evt.Skip()
 
    def on_motion(self, evt):
        e = self.editor
        if e is not None and evt.LeftIsDown():
            byte, bit, inside = self.event_coords_to_byte(evt)
            if inside:
                index1 = byte
                index2 = byte + 1
#                print index1, index2, e.anchor_start_index, e.anchor_end_index
                update = False
                if e.anchor_start_index <= index1:
                    if index2 != e.anchor_end_index:
                        e.anchor_start_index = e.anchor_initial_start_index
                        e.anchor_end_index = index2
                        update = True
                else:
                    if index1 != e.anchor_end_index:
                        e.anchor_start_index = e.anchor_initial_end_index
                        e.anchor_end_index = index1
                        update = True
                if update:
                    wx.CallAfter(self.task.active_editor.index_clicked, e.anchor_end_index, bit, self)
                    wx.CallAfter(self.Refresh)
#                print "motion: byte, start, end", byte, e.anchor_start_index, e.anchor_end_index
        evt.Skip()

    def on_paint(self, evt):
        self.dbg_call_seq += 1
        log.debug("In on_paint %d" % self.dbg_call_seq)
        self.prepare_image()
        if self.scaled_bmp is not None:
            dc = wx.BufferedPaintDC(self, self.scaled_bmp, wx.BUFFER_CLIENT_AREA)
        evt.Skip()
    
    def on_resize(self, evt):
        self.calc_image_size()
    
    def on_popup(self, evt):
        pass
    
    def on_menu(self, evt):
        pass


class FontMapScroller(BitviewScroller):
    font_width_extra_zoom = [0, 0, 1, 0, 1, 1, 2, 2, 2, 2]
    font_height_extra_zoom = [0, 0, 1, 0, 1, 2, 1, 2, 1, 2]
    
    font_to_atascii_mapping = np.hstack([np.arange(64, 96, dtype=np.uint8),np.arange(64, dtype=np.uint8),np.arange(96, 128, dtype=np.uint8)])
    font_to_atascii_mapping = np.hstack([font_to_atascii_mapping, font_to_atascii_mapping + 128])
    font_mappings = [
        (wx.NewId(), "Internal Character Codes", np.arange(256, dtype=np.uint8)),
        (wx.NewId(), "ATASCII Characters", font_to_atascii_mapping),
        ]
    
    def __init__(self, parent, task, **kwargs):
        BitviewScroller.__init__(self, parent, task, **kwargs)
        self.bytes_per_row = 8
        self.zoom = 2
        self.font_mode = 2
        self.set_font_mapping(1)
    
    def calc_scale_from_bytes(self):
        self.total_rows = (self.bytes.size + self.bytes_per_row - 1) / self.bytes_per_row
        self.grid_width = int(8 * self.bytes_per_row)
        self.grid_height = int(8 * self.total_rows)
    
    def get_zoom_factors(self):
        zw = self.font_width_extra_zoom[self.font_mode]
        zh = self.font_height_extra_zoom[self.font_mode]
        return zw * self.zoom, zh * self.zoom
    
    def calc_scroll_params(self):
        zw, zh = self.get_zoom_factors()
        self.SetVirtualSize((self.grid_width * zw, self.grid_height * zh))
        self.SetScrollRate(8 * zw, 8 * zh)
    
    def calc_font_mode_sizes(self, font_mode):
        self.font_mode = font_mode
        if self.font_mode == 2:
            self.bits_to_font = self.bits_to_gr0
        elif self.font_mode < 6:
            self.bits_to_font = self.bits_to_antic4
        else:
            self.bits_to_font = self.bits_to_gr1
            
        self.calc_scroll_params()
    
    def calc_image_size(self):
        x, y = self.GetViewStart()
        w, h = self.GetClientSizeTuple()
        self.start_row = y
        
        # For proper buffered paiting, the visible_rows must include the
        # (possibly) partially obscured last row.  fully_visible_rows
        # indicates the number of rows without that last partially obscured
        # row (if it exists).
        zw, zh = self.get_zoom_factors()
        zoom_factor = 8 * zh
        self.fully_visible_rows = h / zoom_factor
        self.visible_rows = (h + zoom_factor - 1) / zoom_factor
        zoom_factor = 8 * zw
        self.start_col, self.num_cols = x, (w + zoom_factor - 1) / zoom_factor
        log.debug("fontmap: x, y, w, h, row start, num: %s" % str([x, y, w, h, self.start_row, self.visible_rows, "col start, num:", self.start_col, self.num_cols]))
    
    def set_colors(self):
        pfcolors = list(self.editor.playfield_colors)
        self.normal_colors = []
        self.highlight_colors = []
        for c in pfcolors:
            self.normal_colors.append(colors.atari_color_to_rgb(c))
            self.highlight_colors.append(colors.atari_color_to_rgb(c))
        self.highlight_colors[-1] = self.editor.highlight_color

        fg, bg = colors.gr0_colors(pfcolors)
        fg = colors.atari_color_to_rgb(fg)
        bg = colors.atari_color_to_rgb(bg)
        self.normal_gr0_colors = [fg, bg]
        self.highlight_gr0_colors = [fg, self.editor.highlight_color]

    def set_font(self):
        font = self.editor.antic_font
        self.char_pixel_width = font['char_w']
        self.char_pixel_height = font['char_h']
        bytes = np.fromstring(font['data'], dtype=np.uint8)
#        print "numpy font:", bytes)
#        print bytes[1]
        bits = np.unpackbits(bytes)
        bits = bits.reshape((-1, 8, 8))
#        print bits[1]
        
        self.calc_font_mode_sizes(self.editor.font_mode)
        self.normal_font = self.bits_to_font(bits, self.normal_colors, self.normal_gr0_colors)
        self.highlight_font = self.bits_to_font(bits, self.highlight_colors, self.highlight_gr0_colors)
#        log.debug(self.font)
    
    def set_font_mapping(self, index):
        self.font_mapping_index = index
        self.font_mapping = self.font_mappings[self.font_mapping_index][2]
        
    def bits_to_gr0(self, bits, colors, gr0_colors):
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
        
    def bits_to_gr1(self, bits, colors, gr0_colors):
        bg = colors[4]
        if self.font_mode == 6 or self.font_mode == 7:
            half = bits[0:64,:,:]
        else:
            half = bits[64:128,:,:]
        r = np.empty(half.shape, dtype=np.uint8)
        g = np.empty(half.shape, dtype=np.uint8)
        b = np.empty(half.shape, dtype=np.uint8)
        font = np.zeros((256, 8, 8, 3), dtype=np.uint8)

        start_char = 0
        for i in range(4):
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
        
    def bits_to_antic4(self, bits, colors, gr0_colors):
        """
        
        http://www.atarimagazines.com/compute/issue49/419_1_Graphics_0_Text_In_Four_Colors.php
        
        There are four possible combinations of two bits: 00, 01, 10, 11. Each combination represents a different color. The color corresponding to the bit-pair 00 is stored at location 712; the color for the bit-pair 01 is at location 708; the color for bit-pair 10 is at 709; the color for bit-pair 11 is at 710.
        """
        pf0, pf1, pf2, pf3, bak = colors
        r = np.empty(bits.shape, dtype=np.uint8)
        g = np.empty(bits.shape, dtype=np.uint8)
        b = np.empty(bits.shape, dtype=np.uint8)
        
        c = np.empty((128, 8, 4), dtype=np.uint8)
        c[:,:,0] = bits[:,:,0]*2 + bits[:,:,1]
        c[:,:,1] = bits[:,:,2]*2 + bits[:,:,3]
        c[:,:,2] = bits[:,:,4]*2 + bits[:,:,5]
        c[:,:,3] = bits[:,:,6]*2 + bits[:,:,7]
        
        bits[:,:,0] = c[:,:,0]
        bits[:,:,1] = c[:,:,0]
        bits[:,:,2] = c[:,:,1]
        bits[:,:,3] = c[:,:,1]
        bits[:,:,4] = c[:,:,2]
        bits[:,:,5] = c[:,:,2]
        bits[:,:,6] = c[:,:,3]
        bits[:,:,7] = c[:,:,3]
        
        r[bits==0] = bak[0]
        r[bits==1] = pf0[0]
        r[bits==2] = pf1[0]
        r[bits==3] = pf2[0]
        g[bits==0] = bak[1]
        g[bits==1] = pf0[1]
        g[bits==2] = pf1[1]
        g[bits==3] = pf2[1]
        b[bits==0] = bak[2]
        b[bits==1] = pf0[2]
        b[bits==2] = pf1[2]
        b[bits==3] = pf2[2]
        
        font = np.zeros((256, 8, 8, 3), dtype=np.uint8)
        font[0:128,:,:,0] = r
        font[0:128,:,:,1] = g
        font[0:128,:,:,2] = b
        
        # Inverse characters use pf3 in place of pf2
        r[bits==3] = pf3[0]
        g[bits==3] = pf3[1]
        b[bits==3] = pf3[2]
        font[128:256,:,:,0] = r
        font[128:256,:,:,1] = g
        font[128:256,:,:,2] = b
        return font
    
    bits_to_font = bits_to_gr0

    def get_image(self):
        log.debug("get_image: fontmap: start=%d, num=%d" % (self.start_row, self.visible_rows))
        sr = self.start_row
        nr = self.visible_rows
        self.start_byte = sr * self.bytes_per_row
        self.end_byte = self.start_byte + (nr * self.bytes_per_row)
        if self.end_byte > self.bytes.size:
            self.end_byte = self.bytes.size
            bytes = np.zeros((nr * self.bytes_per_row), dtype=np.uint8)
            bytes[0:self.end_byte - self.start_byte] = self.bytes[sr * self.bytes_per_row:self.end_byte]
        else:
            bytes = self.bytes[sr * self.bytes_per_row:self.end_byte]
        num_rows_with_data = (self.end_byte - self.start_byte + self.bytes_per_row - 1) / self.bytes_per_row
        
        sc = self.start_col
        nc = self.num_cols
        bytes = bytes.reshape((nr, -1))
        #log.debug("get_image: bytes", bytes)
        
        width = int(self.char_pixel_width * self.bytes_per_row)
        height = int(nr * self.char_pixel_height)
        
        log.debug("pixel width: %dx%d, zoom=%d, rows with data=%d" % (width, height, self.zoom, num_rows_with_data))
        array = np.zeros((height, width, 3), dtype=np.uint8)
        array[:,:] = self.background_color
        
        log.debug(str([self.end_byte, self.start_byte, (self.end_byte - self.start_byte) / self.bytes_per_row]))
        er = min(num_rows_with_data, nr)
        ec = min(self.bytes_per_row, sc + self.bytes_per_row)
        log.debug("bytes: %s" % str([nr, er, sc, nc, ec, bytes.shape]))
        zx = self.font_width_extra_zoom[self.font_mode]
        zy = self.font_height_extra_zoom[self.font_mode]
        y = 0
        e = self.start_byte
        f = self.normal_font
        fh = self.highlight_font
        anchor_start, anchor_end = self.editor.anchor_start_index, self.editor.anchor_end_index
        if anchor_start > anchor_end:
            anchor_start, anchor_end = anchor_end, anchor_start
        for j in range(er):
            x = 0
            for i in range(sc, ec):
                if e + i >= self.end_byte:
                    break
                c = self.font_mapping[bytes[j, i]]
                if anchor_start <= e + i < anchor_end:
                    array[y:y+8,x:x+8,:] = fh[c]
                else:
                    array[y:y+8,x:x+8,:] = f[c]
                x += 8
            y += 8
            e += self.bytes_per_row
        return array

    def event_coords_to_byte(self, evt):
        """Convert event coordinates to world coordinates.

        Convert the event coordinates to world coordinates by locating
        the offset of the scrolled window's viewport and adjusting the
        event coordinates.
        """
        inside = True

        zw, zh = self.get_zoom_factors()
        x, y = self.GetViewStart()
        x = (evt.GetX() // zw // 8) + x
        y = (evt.GetY() // zh // 8) + y
        if x < 0 or x >= self.bytes_per_row or y < 0 or y > (self.start_row + self.visible_rows):
            inside = False
        byte = (self.bytes_per_row * y) + x
        if byte > self.end_byte:
            inside = False
        bit = 7 - (y & 7)
        return byte, bit, inside
    
    def on_menu(self, event):
        if event.GetId() == self.width_id:
            
            dlg = wx.TextEntryDialog(
                    self, 'Enter new map width in bytes',
                    'Set Map Width', str(self.bytes_per_row))

            if dlg.ShowModal() == wx.ID_OK:
                try:
                    self.bytes_per_row = int(dlg.GetValue())
                except ValueError:
                    log.debug("Bad value: %s" % dlg.GetValue())

            dlg.Destroy()
            self.set_scale()
        else:
            for i, (id, name, mapping) in enumerate(self.font_mappings):
                if event.GetId() == id:
                    self.set_font_mapping(i)
                    wx.CallAfter(self.Refresh)
                    break

    def on_popup(self, event):
        popup = wx.Menu()
        self.width_id = wx.NewId()
        popup.Append(self.width_id, "Set Map Width")
        popup.AppendSeparator()
        for i, (id, name, mapping) in enumerate(self.font_mappings):
            popup.Append(id, "View as %s" % name)
            if self.font_mapping_index == i:
                popup.Enable(id, False)
        self.PopupMenu(popup, event.GetPosition())


class MemoryMapScroller(BitviewScroller):
    def __init__(self, parent, task, **kwargs):
        BitviewScroller.__init__(self, parent, task, **kwargs)
        self.bytes_per_row = 256
        self.zoom = 2
    
    def calc_scale_from_bytes(self):
        self.total_rows = (self.bytes.size + self.bytes_per_row - 1) / self.bytes_per_row
        self.grid_width = int(self.bytes_per_row)
        self.grid_height = int(self.total_rows)
    
    def calc_scroll_params(self):
        z = self.zoom
        self.SetVirtualSize((self.grid_width * z, self.grid_height * z))
        self.SetScrollRate(z, z)
    
    def calc_image_size(self):
        x, y = self.GetViewStart()
        w, h = self.GetClientSizeTuple()
        self.start_row = y
        
        # For proper buffered paiting, the visible_rows must include the
        # (possibly) partially obscured last row.  fully_visible_rows
        # indicates the number of rows without that last partially obscured
        # row (if it exists).
        z = self.zoom
        self.fully_visible_rows = h / z
        self.visible_rows = (h + z - 1) / z
        self.start_col, self.num_cols = x, (w + z - 1) / z
        log.debug("memory map: x, y, w, h, row start, num: %s" % str([x, y, w, h, self.start_row, self.visible_rows, "col start, num:", self.start_col, self.num_cols]))

    def get_image(self):
        log.debug("get_image: memory map: start=%d, num=%d" % (self.start_row, self.visible_rows))
        t0 = time.clock()
        sr = self.start_row
        nr = self.visible_rows
        self.start_byte = sr * self.bytes_per_row
        self.end_byte = self.start_byte + (nr * self.bytes_per_row)
        if self.end_byte > self.bytes.size:
            self.end_byte = self.bytes.size
            bytes = np.zeros((nr * self.bytes_per_row), dtype=np.uint8)
            bytes[0:self.end_byte - self.start_byte] = self.bytes[sr * self.bytes_per_row:self.end_byte]
        else:
            bytes = self.bytes[sr * self.bytes_per_row:self.end_byte]
        bytes = bytes.reshape((nr, -1))
        #log.debug("get_image: bytes", bytes)
        
        e = self.editor
        anchor_start, anchor_end = e.anchor_start_index, e.anchor_end_index
        if anchor_start > anchor_end:
            anchor_start, anchor_end = anchor_end, anchor_start
        if speedups is not None:
            array = speedups.get_numpy_memory_map_image(bytes, self.start_byte, self.end_byte, self.bytes_per_row, nr, self.start_col, self.num_cols, self.background_color, anchor_start, anchor_end, e.highlight_color)
        else:
            array = self.get_numpy_memory_map_image(bytes, self.start_byte, self.end_byte, self.bytes_per_row, nr, self.start_col, self.num_cols, self.background_color, anchor_start, anchor_end, e.highlight_color)
        log.debug(array.shape)
        t = time.clock()
        log.debug("get_image: time %f" % (t - t0))
        return array

    def get_numpy_memory_map_image(self, bytes, start_byte, end_byte, bytes_per_row, num_rows, start_col, num_cols, background_color, anchor_start, anchor_end, selected_color):
        log.debug("SLOW VERSION OF get_numpy_memory_map_image!!!")
        num_rows_with_data = (end_byte - start_byte + bytes_per_row - 1) / bytes_per_row
        
        log.debug(str([end_byte, start_byte, (end_byte - start_byte) / bytes_per_row]))
        end_row = min(num_rows_with_data, num_rows)
        end_col = min(bytes_per_row, start_col + num_cols)
        
        width = end_col - start_col
        height = num_rows_with_data
        log.debug("memory map size: %dx%d, zoom=%d, rows with data=%d, rows %d, cols %d-%d" % (width, height, self.zoom, num_rows_with_data, num_rows, start_col, start_col + width - 1))
        array = np.empty((height, width, 3), dtype=np.uint8)
        array[:,:] = background_color
        
        y = 0
        e = start_byte
        for j in range(end_row):
            x = 0
            for i in range(start_col, end_col):
                if e + i >= end_byte:
                    break
                c = bytes[j, i] ^ 0xff
                if anchor_start <= e + i < anchor_end:
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

    def event_coords_to_byte(self, evt):
        """Convert event coordinates to world coordinates.

        Convert the event coordinates to world coordinates by locating
        the offset of the scrolled window's viewport and adjusting the
        event coordinates.
        """
        inside = True

        z = self.zoom
        x, y = self.GetViewStart()
        x = (evt.GetX() // z) + x
        y = (evt.GetY() // z) + y
        if x < 0 or x >= self.bytes_per_row or y < 0 or y > (self.start_row + self.visible_rows):
            inside = False
        byte = (self.bytes_per_row * y) + x
        if byte > self.end_byte:
            inside = False
        return byte, 0, inside


if __name__ == '__main__':
    app   = wx.PySimpleApp()
    frame = wx.Frame(None, -1, title='Test', size=(500,500))
    frame.CreateStatusBar()
    
    panel = BitviewScroller(frame)
    bytes = np.arange(256, dtype=np.uint8)
    panel.set_data(bytes)

    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(panel,  1, wx.EXPAND | wx.ALL, 5)
    
    def buttonHandler(evt):
        id = evt.GetId()
        if id == 100:
            panel.zoom_in()
        elif id == 101:
            panel.zoom_out()
        elif id == 200:
            wildcard="*"
            dlg = wx.FileDialog(
                frame, message="Open File",
                defaultFile="", wildcard=wildcard, style=wx.OPEN)

            # Show the dialog and retrieve the user response. If it is the
            # OK response, process the data.
            if dlg.ShowModal() == wx.ID_OK:
                # This returns a Python list of files that were selected.
                paths = dlg.GetPaths()

                for path in paths:
                    dprint("open file %s:" % path)
                    fh = open(path, 'rb')
                    img = wx.EmptyImage()
                    if img.LoadStream(fh):
                        panel.setImage(img)
                    else:
                        dprint("Invalid image: %s" % path)
            # Destroy the dialog. Don't do this until you are done with it!
            # BAD things can happen otherwise!
            dlg.Destroy()
        elif id == 201:
            pass
        elif id == 202:
            panel.copy_to_clipboard()
    buttonsizer = wx.BoxSizer(wx.HORIZONTAL)
    sizer.Add(buttonsizer, 0, wx.EXPAND | wx.ALL, 5)
    button = wx.Button(frame, 100, 'Zoom In')
    frame.Bind(wx.EVT_BUTTON, buttonHandler, button)
    buttonsizer.Add(button, 0, wx.EXPAND, 0)
    button = wx.Button(frame, 101, 'Zoom Out')
    frame.Bind(wx.EVT_BUTTON, buttonHandler, button)
    buttonsizer.Add(button, 0, wx.EXPAND, 0)
    button = wx.Button(frame, 200, 'Load')
    frame.Bind(wx.EVT_BUTTON, buttonHandler, button)
    buttonsizer.Add(button, 0, wx.EXPAND, 0)
    button = wx.Button(frame, 202, 'Copy to Clipboard')
    frame.Bind(wx.EVT_BUTTON, buttonHandler, button)
    buttonsizer.Add(button, 0, wx.EXPAND, 0)

    frame.SetAutoLayout(1)
    frame.SetSizer(sizer)
    frame.Show(1)
    app.MainLoop()
