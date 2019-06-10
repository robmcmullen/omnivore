import os
import sys
import time
import wx
import wx.lib.newevent
try:
    import wx.glcanvas as glcanvas
    import OpenGL.GL as gl
    HAS_OPENGL = True
except ImportError:
    HAS_OPENGL = False

import numpy as np

from sawx.ui.compactgrid import MultiCaretHandler

from ..emulator.atari8bit.colors import NTSC
from .intscale import intscale
from .ui_wx import wxGLSLTextureCanvas, wxLegacyTextureCanvas

import logging
logging.basicConfig(level=logging.WARNING)
log = logging.getLogger(__name__)
#log.setLevel(logging.DEBUG)


class EmulatorScreenBase(object):
    def __init__(self, emulator):
        self.emulator = emulator

        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_KEY_DOWN, self.on_key_down)
        self.Bind(wx.EVT_KEY_UP, self.on_key_up)

        self.on_size(None)
        if self.IsDoubleBuffered():
            self.Bind(wx.EVT_PAINT, self.on_paint)
        else:
            self.Bind(wx.EVT_PAINT, self.on_paint_double_buffer)

        self.caret_handler = MultiCaretHandler()

    def DoGetBestSize(self):
        """ Base class virtual method for sizer use to get the best size
        """
        best = wx.Size(self.emulator.width, self.emulator.height)

        # Cache the best size so it doesn't need to be calculated again,
        # at least until some properties of the window change
        self.CacheBestSize(best)

        return best

    def on_size(self,evt):
        if not self.IsDoubleBuffered():
            # make new background buffer
            size  = self.GetClientSize()
            self._buffer = wx.Bitmap(size)

    def show_frame(self, frame_number=-1):
        raise NotImplementedError

    def on_key_down(self, evt):
        keycode = evt.GetKeyCode()
        log.debug(f"key down: {keycode}")
        if not self.emulator.process_key_down(evt, keycode):
            evt.Skip()

    def on_key_up(self, evt):
        keycode = evt.GetKeyCode()
        log.debug(f"key up: {keycode}")
        if not self.emulator.process_key_up(evt, keycode):
            evt.Skip()


class BitmapScreen(wx.Panel, EmulatorScreenBase):
    def __init__(self, parent, emulator):
        wx.Panel.__init__(self, parent, -1, size=(emulator.width, emulator.height))
        EmulatorScreenBase.__init__(self, emulator)
        self.scaled_frame = None
        self.image = None
        self.set_scale(1)

    def get_bitmap_slow(self, frame):
        scaled = self.scale_frame(frame)
        h, w, _ = scaled.shape
        image = wx.ImageFromData(w, h, scaled.tostring())
        bmp = wx.BitmapFromImage(image)
        return bmp

    def get_bitmap_fast(self, frame):
        # Slightly improved speed over converting the array to a string
        # slow x 1000: 0.261524
        # fast x 1000: 0.206890
        self.scale_frame(frame)
        # the image data has already been updated because the unterlying
        # numpy array has been changed
        bmp = wx.Bitmap(self.image)
        return bmp

    get_bitmap = get_bitmap_fast

    def bitmap_benchmark(self):
        import time
        t0 = time.clock()
        for i in range(1000):
            self.get_bitmap_slow(frame)
        print("slow x 1000: %f" % (time.clock() - t0))
        t0 = time.clock()
        for i in range(1000):
            self.get_bitmap_fast(frame)
        print("fast x 1000: %f" % (time.clock() - t0))

    def set_scale(self, scale):
        """Scale a numpy array by an integer factor

        This turns out to be too slow to be used by the screen display. OpenGL
        displays don't use this at all because the display hardware scales
        automatically.
        """
        self.screen_scale = scale
        h = self.emulator.height
        w = self.emulator.width
        if scale > 1:
            self.scaled_frame = np.empty((h * scale, w * scale, 3), dtype=np.uint8)
            self.image = wx.ImageFromBuffer(w * scale, h * scale, self.scaled_frame)
        else:
            self.scaled_frame = None
            self.image = wx.ImageFromBuffer(w, h, self.emulator.screen_rgb)

        # self.delay = 5 * scale * scale
        # self.stop_timer()
        # self.start_timer(True)

    def scale_frame(self, frame):
        if self.screen_scale == 1:
            return frame
        scaled = intscale(frame, self.screen_scale, self.scaled_frame)
        log.debug("panel scale: %d, %s" % (self.screen_scale, scaled.shape))
        return scaled

    def show_frame(self, frame_number=-1, force=False):
        if force or frame_number >= 0:
            dc = wx.ClientDC(self)
            self.updateDrawing(dc, frame_number)
        else:
            #self.updateDrawing()
            self.Refresh()

    def updateDrawing(self, dc, frame_number=-1):
        #dc=wx.BufferedDC(wx.ClientDC(self), self._buffer)
        frame = self.emulator.get_frame_rgb(frame_number)
        bmp = self.get_bitmap(frame)
        dc.DrawBitmap(bmp, 0,0, True)

    def on_paint(self, evt):
        dc=wx.PaintDC(self)
        self.updateDrawing(dc)
        self.refreshed=True

    def on_paint_double_buffer(self, evt):
        dc=wx.BufferedPaintDC(self,self._buffer)
        self.updateDrawing(dc)
        self.refreshed=True


class OpenGLEmulatorMixin(object):
    def get_raw_texture_data(self, frame_number=-1):
        raw = self.emulator.get_frame_rgba_opengl(frame_number)
        return raw

    def show_frame(self, frame_number=-1):
        if not self.finished_init:
            return
        frame = self.get_rgba_texture_data(frame_number)
        try:
            self.update_texture(self.display_texture, frame)
        except Exception as e:
            import traceback

            print(traceback.format_exc())
            sys.exit()
        self.on_draw()

    def on_paint(self, evt):
        if not self.finished_init:
            self.init_context()
        self.show_frame()

    on_paint_double_buffer = on_paint


class OpenGLScreen(OpenGLEmulatorMixin, wxLegacyTextureCanvas, EmulatorScreenBase):
    def __init__(self, parent, emulator):
        wxLegacyTextureCanvas.__init__(self, parent, NTSC, -1, size=(3*emulator.width, 3*emulator.height))
        EmulatorScreenBase.__init__(self, emulator)

    def get_rgba_texture_data(self, frame_number=-1):
        raw = self.emulator.get_frame_rgba_opengl(frame_number)
        log.debug("raw data for legacy version: %s" % str(raw.shape))
        return raw


class GLSLScreen(OpenGLEmulatorMixin, wxGLSLTextureCanvas, EmulatorScreenBase):
    def __init__(self, parent, emulator):
        wxGLSLTextureCanvas.__init__(self, parent, NTSC, -1, size=(3*emulator.width, 3*emulator.height))
        EmulatorScreenBase.__init__(self, emulator)

    def get_color_indexed_texture_data(self, frame_number=-1):
        raw = np.flipud(self.emulator.get_color_indexed_screen(frame_number))
        log.debug("raw data for GLSL version: %s" % str(raw.shape))
        return raw
