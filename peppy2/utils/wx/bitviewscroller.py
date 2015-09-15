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
    
    def __init__(self, parent):
        wx.ScrolledWindow.__init__(self, parent, -1)

        # Settings
        self.background_color = wx.Colour(160, 160, 160)
        self.max_zoom = 16
        self.min_zoom = 1
        self.bytes_per_row = 1

        # internal storage
        self.bytes = None
        self.img = None
        self.scaled_bmp = None
        self.width = 0
        self.height = 0
        self.zoom = 5
        self.crop = None
        
        # hacks
        self.just_scrolled = False
        
        # cursors
        self.default_cursor = wx.CURSOR_ARROW
        self.save_cursor = None
        
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_MOUSE_EVENTS, self.OnMouseEvent)

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

    def get_image(self, start_row, num_rows):
        print "Getting image: start=%d, num=%d" % (start_row, num_rows)
        self.start_row = start_row
        self.num_rows = num_rows
        self.start_byte = start_row * self.bytes_per_row
        self.end_byte = self.start_byte + (num_rows * self.bytes_per_row)
        if self.end_byte > self.bytes.size:
            self.end_byte = self.bytes.size
            bytes = np.zeros((num_rows * self.bytes_per_row), dtype=np.uint8)
            bytes[0:self.end_byte - self.start_byte] = self.bytes[start_row * self.bytes_per_row:self.end_byte]
        else:
            bytes = self.bytes[start_row * self.bytes_per_row:self.end_byte]
        bits = np.unpackbits(bytes)
        bits = bits.reshape((-1, 8 * self.bytes_per_row))
        bits[bits==0]=255
        bits[bits==1]=0
        width = 8 * self.bytes_per_row
        array = np.zeros((num_rows, width, 3), dtype=np.uint8)
        array[:,:,0] = bits
        array[:,:,1] = bits
        array[:,:,2] = bits
        image = wx.EmptyImage(width, num_rows)
        image.SetData(array.tostring())
        image.Rescale(width * self.zoom, num_rows * self.zoom)
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

    def get_row_info(self):
        x, y = self.GetViewStart()
        w, h = self.GetClientSizeTuple()
        h2 = (h / self.bytes_per_row) * self.bytes_per_row
        start_row, num_rows = y, h2 / self.zoom + 1
        print "x, y, w, h, start, num: ", x, y, w, h, start_row, num_rows
        return start_row, num_rows

    def prepare_image(self):
        """Creates new image at specified zoom factor.

        Creates a new image that is to be used as the background of
        the scrolled bitmap.  Currently, actually creates the entire
        image, which could lead to memory problems if the image is
        really huge and the zoom factor is large.
        """
        if self.bytes is not None:
            rows = (self.bytes.size + self.bytes_per_row - 1) / self.bytes_per_row
            self.width = int(8 * self.bytes_per_row * self.zoom)
            self.height = int(rows * self.zoom)
            
            w, h = self.GetClientSizeTuple()
            dc = wx.MemoryDC()
            self.scaled_bmp = wx.EmptyBitmap(w, h)
            
            dc.SelectObject(self.scaled_bmp)
            dc.SetBackground(wx.Brush(self.background_color))
            dc.Clear()
            
            start_row, num_rows = self.get_row_info()
            bmp = self.get_image(start_row, num_rows)
            dc.DrawBitmap(bmp, 0, 0, True)

    def set_scale(self):
        """Creates new image at specified zoom factor.

        Creates a new image that is to be used as the background of
        the scrolled bitmap.  Currently, actually creates the entire
        image, which could lead to memory problems if the image is
        really huge and the zoom factor is large.
        """
        if self.bytes is not None:
            rows = (self.bytes.size + self.bytes_per_row - 1) / self.bytes_per_row
            self.width = int(8 * self.bytes_per_row * self.zoom)
            self.height = int(rows * self.zoom)
        else:
            self.width = 10
            self.height = 10
        print "set_scale: ", self.width, self.height
        self.SetVirtualSize((self.width, self.height))
        rate = int(self.zoom)
        if rate < 1:
            rate = 1
        self.SetScrollRate(rate, rate)
        self.Refresh()
    
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
        if x < 0 or xbyte >= self.bytes_per_row or y < 0 or y > (self.start_row + self.num_rows):
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
        x = ev.GetX()
        y = ev.GetY()
        byte, bit, inside = self.event_coords_to_byte(ev)
        print x, y, byte, bit, inside
        
        if ev.LeftIsDown() and inside:
            event = BitviewEvent(myEVT_BYTECLICKED, self.GetId(), byte, bit)
            self.GetEventHandler().ProcessEvent(event)
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
            
            #dc=wx.BufferedPaintDC(self, self.scaled_bmp, wx.BUFFER_CLIENT_AREA)
            dc=wx.PaintDC(self)
            dc.DrawBitmap(self.scaled_bmp, 0, 0)
            # Note that the drawing actually happens when the dc goes
            # out of scope and is destroyed.
            
#            # FIXME: This check for MSW is because it gets multiple onpaint
#            # events, so make sure it's only called once for consecutive
#            # repaints.  HACK!
#            if self.selector and (wx.Platform != '__WXMSW__' or not self.just_scrolled):
#                wx.CallAfter(self.selector.recalc_and_draw)
            #self.overlay.Reset()
        self.just_scrolled = False
        evt.Skip()


default_font = '\x00\x00\x00\x00\x00\x00\x00\x00\x00\x18\x18\x18\x18\x00\x18\x00\x00fff\x00\x00\x00\x00\x00f\xffff\xfff\x00\x18>`<\x06|\x18\x00\x00fl\x180fF\x00\x1c6\x1c8of;\x00\x00\x18\x18\x18\x00\x00\x00\x00\x00\x0e\x1c\x18\x18\x1c\x0e\x00\x00p8\x18\x188p\x00\x00f<\xff<f\x00\x00\x00\x18\x18~\x18\x18\x00\x00\x00\x00\x00\x00\x00\x18\x180\x00\x00\x00~\x00\x00\x00\x00\x00\x00\x00\x00\x00\x18\x18\x00\x00\x06\x0c\x180`@\x00\x00<fnvf<\x00\x00\x188\x18\x18\x18~\x00\x00<f\x0c\x180~\x00\x00~\x0c\x18\x0cf<\x00\x00\x0c\x1c<l~\x0c\x00\x00~`|\x06f<\x00\x00<`|ff<\x00\x00~\x06\x0c\x1800\x00\x00<f<ff<\x00\x00<f>\x06\x0c8\x00\x00\x00\x18\x18\x00\x18\x18\x00\x00\x00\x18\x18\x00\x18\x180\x06\x0c\x180\x18\x0c\x06\x00\x00\x00~\x00\x00~\x00\x00`0\x18\x0c\x180`\x00\x00<f\x0c\x18\x00\x18\x00\x00<fnn`>\x00\x00\x18<ff~f\x00\x00|f|ff|\x00\x00<f``f<\x00\x00xlfflx\x00\x00~`|``~\x00\x00~`|```\x00\x00>``nf>\x00\x00ff~fff\x00\x00~\x18\x18\x18\x18~\x00\x00\x06\x06\x06\x06f<\x00\x00flxxlf\x00\x00`````~\x00\x00cw\x7fkcc\x00\x00fv~~nf\x00\x00<ffff<\x00\x00|ff|``\x00\x00<fffl6\x00\x00|ff|lf\x00\x00<`<\x06\x06<\x00\x00~\x18\x18\x18\x18\x18\x00\x00fffff~\x00\x00ffff<\x18\x00\x00cck\x7fwc\x00\x00ff<<ff\x00\x00ff<\x18\x18\x18\x00\x00~\x0c\x180`~\x00\x00\x1e\x18\x18\x18\x18\x1e\x00\x00@`0\x18\x0c\x06\x00\x00x\x18\x18\x18\x18x\x00\x00\x08\x1c6c\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\x00\x006\x7f\x7f>\x1c\x08\x00\x18\x18\x18\x1f\x1f\x18\x18\x18\x03\x03\x03\x03\x03\x03\x03\x03\x18\x18\x18\xf8\xf8\x00\x00\x00\x18\x18\x18\xf8\xf8\x18\x18\x18\x00\x00\x00\xf8\xf8\x18\x18\x18\x03\x07\x0e\x1c8p\xe0\xc0\xc0\xe0p8\x1c\x0e\x07\x03\x01\x03\x07\x0f\x1f?\x7f\xff\x00\x00\x00\x00\x0f\x0f\x0f\x0f\x80\xc0\xe0\xf0\xf8\xfc\xfe\xff\x0f\x0f\x0f\x0f\x00\x00\x00\x00\xf0\xf0\xf0\xf0\x00\x00\x00\x00\xff\xff\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xff\x00\x00\x00\x00\xf0\xf0\xf0\xf0\x00\x1c\x1cww\x08\x1c\x00\x00\x00\x00\x1f\x1f\x18\x18\x18\x00\x00\x00\xff\xff\x00\x00\x00\x18\x18\x18\xff\xff\x18\x18\x18\x00\x00<~~~<\x00\x00\x00\x00\x00\xff\xff\xff\xff\xc0\xc0\xc0\xc0\xc0\xc0\xc0\xc0\x00\x00\x00\xff\xff\x18\x18\x18\x18\x18\x18\xff\xff\x00\x00\x00\xf0\xf0\xf0\xf0\xf0\xf0\xf0\xf0\x18\x18\x18\x1f\x1f\x00\x00\x00x`x`~\x18\x1e\x00\x00\x18<~\x18\x18\x18\x00\x00\x18\x18\x18~<\x18\x00\x00\x180~0\x18\x00\x00\x00\x18\x0c~\x0c\x18\x00\x00\x00\x18<~~<\x18\x00\x00\x00<\x06>f>\x00\x00``|ff|\x00\x00\x00<```<\x00\x00\x06\x06>ff>\x00\x00\x00<f~`<\x00\x00\x0e\x18>\x18\x18\x18\x00\x00\x00>ff>\x06|\x00``|fff\x00\x00\x18\x008\x18\x18<\x00\x00\x06\x00\x06\x06\x06\x06<\x00``lxlf\x00\x008\x18\x18\x18\x18<\x00\x00\x00f\x7f\x7fkc\x00\x00\x00|ffff\x00\x00\x00<fff<\x00\x00\x00|ff|``\x00\x00>ff>\x06\x06\x00\x00|f```\x00\x00\x00>`<\x06|\x00\x00\x18~\x18\x18\x18\x0e\x00\x00\x00ffff>\x00\x00\x00fff<\x18\x00\x00\x00ck\x7f>6\x00\x00\x00f<\x18<f\x00\x00\x00fff>\x0cx\x00\x00~\x0c\x180~\x00\x00\x18<~~\x18<\x00\x18\x18\x18\x18\x18\x18\x18\x18\x00~x|nf\x06\x00\x08\x188x8\x18\x08\x00\x10\x18\x1c\x1e\x1c\x18\x10\x00'


class FontMapScroller(BitviewScroller):
    def __init__(self, parent, font=None):
        BitviewScroller.__init__(self, parent)
        self.bytes_per_row = 8
        self.zoom = 2
        
        if font is None:
            font = default_font
        self.font = font



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
