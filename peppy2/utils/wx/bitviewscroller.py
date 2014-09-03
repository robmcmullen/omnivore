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
        self.zoom = 3
        self.crop = None
        
        # hacks
        self.just_scrolled = False
        
        # cursors
        self.default_cursor = wx.CURSOR_ARROW
        self.save_cursor = None
        
        self.Bind(wx.EVT_PAINT, self.OnPaint)

        # selectors and related storage
        self.use_selector = None
        self.selector = None
        self.selector_event_callback = None
        self.overlay = wx.Overlay()
        self.Bind(wx.EVT_MOUSE_EVENTS, self.OnMouseEvent)

    def zoomIn(self, zoom=1):
        self.zoom += zoom
        if self.zoom > self.max_zoom:
            self.zoom = self.max_zoom
        self.set_scale()
        
    def zoomOut(self, zoom=1):
        self.zoom -= zoom
        if self.zoom < self.min_zoom:
            self.zoom = self.min_zoom
        self.set_scale()

    def _clearBackground(self, dc, w, h):
        dc.SetBackground(wx.Brush(self.background_color))
        dc.Clear()

    def _drawBackground(self, dc, w, h):
        self._clearBackground(dc, w, h)

    def get_image(self, start_row, num_rows):
        print "Getting image: start=%d, num=%d" % (start_row, num_rows)
        start = start_row * self.bytes_per_row
        end = start + (num_rows * self.bytes_per_row)
        if end > self.bytes.size:
            end = self.bytes.size
            bytes = np.zeros((num_rows * self.bytes_per_row), dtype=np.uint8)
            bytes[0:end - start] = self.bytes[start_row * self.bytes_per_row:end]
        else:
            bytes = self.bytes[start_row * self.bytes_per_row:end]
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
            self.scaled_bmp = wx.EmptyBitmap(self.width, h)
            
            x, y = self.GetViewStart()
            print "x, y, w, h: ", x, y, w, h
            dc.SelectObject(self.scaled_bmp)
            dc.SetBackground(wx.Brush(self.background_color))
            dc.Clear()
            
            h2 = (h / self.bytes_per_row) * self.bytes_per_row
            bmp = self.get_image(y, h2 / self.zoom + 1)
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
        if self.selector:
            self.selector.recalc()
        self.Refresh()
    
    def set_data(self, byte_source):
        self.bytes = byte_source
        self.set_scale()

    def copyToClipboard(self):
        """Copies current image to clipboard.

        Copies the current image, including scaling, zooming, etc. to
        the clipboard.
        """
        img = self._getCroppedImage()
        w = int(img.GetWidth() * self.zoom)
        h = int(img.GetHeight() * self.zoom)
        clip = wx.BitmapFromImage(img.Scale(w, h))
        bmpdo = wx.BitmapDataObject(clip)
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(bmpdo)
            wx.TheClipboard.Close()

    def saveImage(self, filename):
        """Copies current image to clipboard.

        Copies the current image, including scaling, zooming, etc. to
        the clipboard.
        """
        handlers = {'.png': wx.BITMAP_TYPE_PNG,
                    '.jpg': wx.BITMAP_TYPE_JPEG,
                    }

        root, ext = os.path.splitext(filename)
        ext = ext.lower()
        if ext in handlers:
            try:
                status = self.scaled_bmp.SaveFile(filename, handlers[ext])
            except:
                status = False
            return status
        raise TypeError("Unknown image file extension %s" % ext)

    def convertEventCoords(self, ev):
        """Convert event coordinates to world coordinates.

        Convert the event coordinates to world coordinates by locating
        the offset of the scrolled window's viewport and adjusting the
        event coordinates.
        """
        xView, yView = self.GetViewStart()
        xDelta, yDelta = self.GetScrollPixelsPerUnit()
        x = ev.GetX() + (xView * xDelta)
        y = ev.GetY() + (yView * yDelta)
        return (x, y)

    def getBoundedCoords(self, x, y):
        """Return image coordinates clipped to boundary of image."""
        
        if x<0: x=0
        elif x>=self.img.GetWidth(): x=self.img.GetWidth()-1
        if y<0: y=0
        elif y>=self.img.GetHeight(): y=self.img.GetHeight()-1
        return (x, y)

    def getImageCoords(self, x, y, fixbounds = True):
        """Convert scrolled window coordinates to image coordinates.

        Convert from the scrolled window coordinates (where (0,0) is
        the upper left corner when the window is scrolled to the
        top-leftmost position) to the corresponding point on the
        original (i.e. unzoomed, unrotated, uncropped) image.
        """
        x = int(x / self.zoom)
        y = int(y / self.zoom)
        if fixbounds:
            return self.getBoundedCoords(x, y)
        else:
            return (x, y)

    def isInBounds(self, x, y):
        """Check if world coordinates are on the image.

        Return True if the world coordinates lie on the image.
        """
        if self.img is None or x<0 or y<0 or x>=self.width or y>=self.height:
            return False
        return True

    def isEventInClientArea(self, ev):
        """Check if event is in the viewport.

        Return True if the event is within the visible viewport of the
        scrolled window.
        """
        size = self.GetClientSizeTuple()
        x = ev.GetX()
        y = ev.GetY()
        if x < 0 or x >= size[0] or y < 0 or y >= size[1]:
            return False
        return True

    def setCursor(self, cursor):
        """Set cursor for the window.

        A mild enhancement of the wx standard SetCursor that takes an
        integer id as well as a wx.StockCursor instance.
        """
        if isinstance(cursor, int):
            cursor = wx.StockCursor(cursor)
        self.SetCursor(cursor)

    def blankCursor(self, ev, coords=None):
        """Turn off cursor.

        Some selectors, like the crosshair selector, work better when
        the mouse cursor isn't obscuring the image.  This method is
        called by the selector itself to blank the cursor when over
        the image.
        """
        #dprint()
        if coords is None:
            coords = self.convertEventCoords(ev)
        if self.isInBounds(*coords) and self.isEventInClientArea(ev):
            if not self.save_cursor:
                self.save_cursor = True
                self.setCursor(wx.StockCursor(wx.CURSOR_BLANK))
        else:
            if self.save_cursor:
                self.setCursor(self.use_selector.cursor)
                self.save_cursor = False

    def getSelectorCoordsOnImage(self, with_cropped_offset=True):
        if self.selector:
            x, y = self.getImageCoords(*self.selector.world_coords)
            if self.crop is not None and with_cropped_offset:
                x += self.crop[0]
                y += self.crop[1]
            return (x, y)
        return None
    
    def setSelector(self, selector):
        if self.selector:
            self.selector.cleanup()
            self.selector = None
        self.use_selector = selector
        self.setCursor(self.use_selector.cursor)
        self.save_cursor = None
    
    def startSelector(self, ev=None):
        self.selector = self.use_selector(self, ev)

    def getActiveSelector(self):
        """Returns the currently active selector."""
        return self.selector

    def endActiveSelector(self):
        if self.selector:
            self.selector.cleanup()
            self.selector = None
        if self.save_cursor:
            self.setCursor(self.use_selector.cursor)
            self.save_cursor = None

    def OnMouseEvent(self, ev):
        """Driver to process mouse events.

        This is the main driver to process all mouse events that
        happen on the BitmapScroller.  Once a selector is triggered by
        its event combination, it becomes the active selector and
        further mouse events are directed to its handler.
        """
        if self.img:
            inside = self.isEventInClientArea(ev)
            
            try:
                # First, process the event itself or start it up if it has
                # been triggered.
                if self.selector:
                    if not self.selector.processEvent(ev):
                        self.endActiveSelector()
                elif inside and self.use_selector.trigger(ev):
                    self.startSelector(ev)

                # Next, if we have a selector, process some user interface
                # side effects
                if self.selector:
                    if self.selector.want_autoscroll and not inside:
                        self.autoScroll(ev)
                    if self.selector.want_blank_cursor:
                        self.blankCursor(ev)
            except:
                # If something bad happens, make sure we return control of the
                # mouse pointer to the user
                if self.HasCapture():
                    self.ReleaseMouse()
                raise
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


if __name__ == '__main__':
    app   = wx.PySimpleApp()
    frame = wx.Frame(None, -1, title='Test', size=(500,500))
    frame.CreateStatusBar()
    
    # Add a panel that the rubberband will work on.
    panel = BitviewScroller(frame)
    bytes = np.arange(256, dtype=np.uint8)
    panel.set_data(bytes)

#    # Add the callbacks
#    def crosshairCallback(ev):
#        x, y = ev.imageCoords
#        frame.SetStatusText("x=%d y=%d" % (x, y))
#    panel.Bind(EVT_CROSSHAIR_MOTION, crosshairCallback)
#    def rubberbandMotionCallback(ev):
#        x0, y0 = ev.upperLeftImageCoords
#        x1, y1 = ev.lowerRightImageCoords
#        frame.SetStatusText("moving rubberband: ul = (%d,%d) lr = (%d,%d)" % (x0, y0, x1, y1))
#    panel.Bind(EVT_RUBBERBAND_MOTION, rubberbandMotionCallback)
#    def rubberbandSizeCallback(ev):
#        x0, y0 = ev.upperLeftImageCoords
#        x1, y1 = ev.lowerRightImageCoords
#        frame.SetStatusText("sizing rubberband: ul = (%d,%d) lr = (%d,%d)" % (x0, y0, x1, y1))
#    panel.Bind(EVT_RUBBERBAND_SIZE, rubberbandSizeCallback)

    # Layout the frame
    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(panel,  1, wx.EXPAND | wx.ALL, 5)
    
    def buttonHandler(ev):
        id = ev.GetId()
        if id == 100:
            panel.zoomIn()
        elif id == 101:
            panel.zoomOut()
#        elif id == 102:
#            panel.setSelector(Crosshair)
#        elif id == 103:
#            panel.setSelector(RubberBand)
#        elif id == 104:
#            selector = panel.getActiveSelector()
#            dprint("selector = %s" % selector)
#            if isinstance(selector, RubberBand):
#                box = selector.getSelectedBox()
#                dprint("selected box = %s" % str(box))
#                panel.setCrop(box)
#        elif id == 105:
#            panel.setCrop(None)
#        elif id == 106:
#            panel.setSelector(RubberBand)
#            panel.startSelector()
#            selector = panel.getActiveSelector()
#            img = panel.orig_img
#            selector.setSelection(0,0, img.GetWidth()/2, img.GetHeight()/2)
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
            panel.copyToClipboard()
    buttonsizer = wx.BoxSizer(wx.HORIZONTAL)
    sizer.Add(buttonsizer, 0, wx.EXPAND | wx.ALL, 5)
    button = wx.Button(frame, 100, 'Zoom In')
    frame.Bind(wx.EVT_BUTTON, buttonHandler, button)
    buttonsizer.Add(button, 0, wx.EXPAND, 0)
    button = wx.Button(frame, 101, 'Zoom Out')
    frame.Bind(wx.EVT_BUTTON, buttonHandler, button)
    buttonsizer.Add(button, 0, wx.EXPAND, 0)
    button = wx.Button(frame, 102, 'Crosshair')
    frame.Bind(wx.EVT_BUTTON, buttonHandler, button)
    buttonsizer.Add(button, 0, wx.EXPAND, 0)
    button = wx.Button(frame, 103, 'Select')
    frame.Bind(wx.EVT_BUTTON, buttonHandler, button)
    buttonsizer.Add(button, 0, wx.EXPAND, 0)
    
    buttonsizer = wx.BoxSizer(wx.HORIZONTAL)
    sizer.Add(buttonsizer, 0, wx.EXPAND | wx.ALL, 5)
    button = wx.Button(frame, 104, 'Crop')
    frame.Bind(wx.EVT_BUTTON, buttonHandler, button)
    buttonsizer.Add(button, 0, wx.EXPAND, 0)
    button = wx.Button(frame, 105, 'Uncrop')
    frame.Bind(wx.EVT_BUTTON, buttonHandler, button)
    buttonsizer.Add(button, 0, wx.EXPAND, 0)
    button = wx.Button(frame, 106, 'Select half')
    frame.Bind(wx.EVT_BUTTON, buttonHandler, button)
    buttonsizer.Add(button, 0, wx.EXPAND, 0)

    buttonsizer = wx.BoxSizer(wx.HORIZONTAL)
    sizer.Add(buttonsizer, 0, wx.EXPAND | wx.ALL, 5)
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
