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

import numpy as np
import wx
import wx.lib.newevent

import peppy2.utils.fonts as fonts

myEVT_BYTECLICKED = wx.NewEventType()

EVT_BYTECLICKED = wx.PyEventBinder(myEVT_BYTECLICKED, 1)

class BitviewEvent(wx.PyCommandEvent):
    """Event sent when a LayerControl is changed."""

    def __init__(self, eventType, id, byte, bit):
        wx.PyCommandEvent.__init__(self, eventType, id)
        self.byte = byte
        self.bit = bit


class BitviewScroller(wx.ScrolledWindow):
    dbg_call_seq = 0
    
    def __init__(self, parent, task):
        wx.ScrolledWindow.__init__(self, parent, -1)

        # Settings
        self.task = task
        self.background_color = (160, 160, 160)
        self.wx_background_color = wx.Colour(*self.background_color)
        self.max_zoom = 16
        self.min_zoom = 1
        self.bytes_per_row = 1

        # internal storage
        self.bytes = None
        self.start_byte = None
        self.end_byte = None
        self.img = None
        self.scaled_bmp = None
        self.grid_width = 0
        self.grid_height = 0
        self.zoom = 5
        self.crop = None
        
        # hacks
        
        # cursors
        self.default_cursor = wx.CURSOR_ARROW
        self.save_cursor = None
        
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_SIZE, self.on_resize)
        self.Bind(wx.EVT_MOUSE_EVENTS, self.OnMouseEvent)
        self.Bind(wx.EVT_RIGHT_DOWN, self.on_popup)
        self.Bind(wx.EVT_MENU, self.on_menu)
    
    def set_task(self, task):
        self.task = task

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

    def get_image(self):
        print "Getting image: start=%d, num=%d" % (self.start_row, self.visible_rows)
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
        bits = np.unpackbits(bytes)
        bits = bits.reshape((-1, 8 * self.bytes_per_row))
        bits[bits==0]=255
        bits[bits==1]=0
        width = 8 * self.bytes_per_row
        array = np.zeros((nr, width, 3), dtype=np.uint8)
        array[:,:,0] = bits
        array[:,:,1] = bits
        array[:,:,2] = bits
        image = wx.EmptyImage(width, nr)
        image.SetData(array.tostring())
        image.Rescale(width * self.zoom, nr * self.zoom)
        bmp = wx.BitmapFromImage(image)
        return bmp

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
            dc.SetBackground(wx.Brush(self.wx_background_color))
            dc.Clear()
            
            bmp = self.get_image()
            dc.DrawBitmap(bmp, 0, 0)
    
    def calc_image_size(self):
        x, y = self.GetViewStart()
        w, h = self.GetClientSizeTuple()
        self.start_row = y
        
        # For proper buffered paiting, the visible rows must include the
        # (possibly) partially obscured last row
        self.visible_rows = ((h + self.zoom - 1) / self.zoom)
        print "x, y, w, h, start, num: ", x, y, w, h, self.start_row, self.visible_rows

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
        print "set_scale: ", self.grid_width, self.grid_height
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
    
    def set_data(self, byte_source):
        self.bytes = byte_source
        self.set_scale()

    def event_coords_to_byte(self, ev):
        """Convert event coordinates to world coordinates.

        Convert the event coordinates to world coordinates by locating
        the offset of the scrolled window's viewport and adjusting the
        event coordinates.
        """
        inside = True

        x, y = self.GetViewStart()
        x = (ev.GetX() // self.zoom) + x
        y = (ev.GetY() // self.zoom) + y
        xbyte = (x // 8)
        if x < 0 or xbyte >= self.bytes_per_row or y < 0 or y > (self.start_row + self.visible_rows):
            inside = False
        byte = (self.bytes_per_row * y) + xbyte
        if byte > self.end_byte:
            inside = False
        bit = 7 - (x & 7)
        return byte, bit, inside

    def OnMouseEvent(self, ev):
        """Driver to process mouse events.

        This is the main driver to process all mouse events that
        happen on the BitmapScroller.  Once a selector is triggered by
        its event combination, it becomes the active selector and
        further mouse events are directed to its handler.
        """
        if self.end_byte is None:  # end_byte is a proxy for the image being loaded
            return
        
        x = ev.GetX()
        y = ev.GetY()
        byte, bit, inside = self.event_coords_to_byte(ev)
        #print x, y, byte, bit, inside
        
        if ev.LeftIsDown() and inside:
            wx.CallAfter(self.task.active_editor.byte_clicked, byte, bit)
        w = ev.GetWheelRotation()
        if ev.ControlDown():
            if w < 0:
                self.zoom_out()
            elif w > 0:
                self.zoom_in()

        ev.Skip()

    def OnPaint(self, evt):
        self.dbg_call_seq += 1
        print("In OnPaint %d" % self.dbg_call_seq)
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
    font_width_extra_zoom = [0, 0, 1, 0, 1, 1, 2, 2]
    font_height_extra_zoom = [0, 0, 1, 0, 1, 2, 1, 2]
    
    def __init__(self, parent, task, font=None, font_mode=2):
        BitviewScroller.__init__(self, parent, task)
        self.bytes_per_row = 8
        self.zoom = 2
        self.font_mode = font_mode
        
        if font is None:
            font = fonts.A8DefaultFont
        self.set_font(font)
    
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
    
    def set_font_mode(self, font_mode):
        self.font_mode = font_mode
        self.calc_scroll_params()
        self.Refresh()
    
    def calc_image_size(self):
        x, y = self.GetViewStart()
        w, h = self.GetClientSizeTuple()
        self.start_row = y
        
        # For proper buffered paiting, the visible rows must include the
        # (possibly) partially obscured last row
        zw, zh = self.get_zoom_factors()
        zoom_factor = 8 * zh
        self.visible_rows = (h + zoom_factor - 1) / zoom_factor
        zoom_factor = 8 * zw
        self.start_col, self.num_cols = x, (w + zoom_factor - 1) / zoom_factor
        print "fontmap: x, y, w, h, row start, num: ", x, y, w, h, self.start_row, self.visible_rows, "col start, num:", self.start_col, self.num_cols

    def set_font(self, font):
        self.char_pixel_width = font['char_w']
        self.char_pixel_height = font['char_h']
        bytes = np.fromstring(font['data'], dtype=np.uint8)
        print "numpy font:", bytes
        print bytes[1]
        bits = np.unpackbits(bytes)
        bits = bits.reshape((-1, 8, 8))
        print bits[1]
        
        bits[bits==0]=255
        bits[bits==1]=0
        font = np.zeros((256, 8, 8, 3), dtype=np.uint8)
        font[0:128,:,:,0] = bits
        font[0:128,:,:,1] = bits
        font[0:128,:,:,2] = bits
        
        # Inverse characters when high bit set
        font[128:256,:,:,0] = 255 - bits
        font[128:256,:,:,1] = 255 - bits
        font[128:256,:,:,2] = 255 - bits
        print font[1]
        
        self.font = font

    def get_image(self):
        print "Getting fontmap: start=%d, num=%d" % (self.start_row, self.visible_rows)
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
        #print "get_image: bytes", bytes
        
        width = int(self.char_pixel_width * self.bytes_per_row)
        height = int(nr * self.char_pixel_height)
        
        print "pixel width:", width, height, "zoom", self.zoom, "rows with data", num_rows_with_data
        array = np.zeros((height, width, 3), dtype=np.uint8)
        array[:,:] = self.background_color
        
        print self.end_byte, self.start_byte, (self.end_byte - self.start_byte) / self.bytes_per_row
        er = min(num_rows_with_data, nr)
        ec = min(self.bytes_per_row, sc + self.bytes_per_row)
        print "bytes:", nr, er, sc, nc, ec, bytes.shape
        zx = self.font_width_extra_zoom[self.font_mode]
        zy = self.font_height_extra_zoom[self.font_mode]
        y = 0
        e = self.start_byte
        for j in range(er):
            x = 0
            for i in range(sc, ec):
                if e + i >= self.end_byte:
                    break
                c = bytes[j, i]
                array[y:y+8,x:x+8,:] = self.font[c]
                x += 8
            y += 8
            e += self.bytes_per_row
        print array.shape
        image = wx.EmptyImage(width, height)
        image.SetData(array.tostring())
        zw, zh = self.get_zoom_factors()
        image.Rescale(width * zw, height * zh)
        bmp = wx.BitmapFromImage(image)
        return bmp

    def event_coords_to_byte(self, ev):
        """Convert event coordinates to world coordinates.

        Convert the event coordinates to world coordinates by locating
        the offset of the scrolled window's viewport and adjusting the
        event coordinates.
        """
        inside = True

        zw, zh = self.get_zoom_factors()
        x, y = self.GetViewStart()
        x = (ev.GetX() // zw // 8) + x
        y = (ev.GetY() // zh // 8) + y
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
                    print "Bad value: %s" % dlg.GetValue()

            dlg.Destroy()
            self.set_scale()

    def on_popup(self, event):
        popup = wx.Menu()
        self.width_id = wx.NewId()
        popup.Append(self.width_id, "Set Map Width")
        self.PopupMenu(popup, event.GetPosition())


if __name__ == '__main__':
    app   = wx.PySimpleApp()
    frame = wx.Frame(None, -1, title='Test', size=(500,500))
    frame.CreateStatusBar()
    
    panel = BitviewScroller(frame)
    bytes = np.arange(256, dtype=np.uint8)
    panel.set_data(bytes)

    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(panel,  1, wx.EXPAND | wx.ALL, 5)
    
    def buttonHandler(ev):
        id = ev.GetId()
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
