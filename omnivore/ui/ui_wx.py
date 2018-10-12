#!/usr/bin/env python
"""wxPython wrapper around texture_canvas
"""
import sys
import ctypes
import numpy as np

import wx
from wx import glcanvas

from .texture_canvas import GLSLTextureCanvas, LegacyTextureCanvas

import logging
log = logging.getLogger(__name__)
#log.setLevel(logging.DEBUG)



class wxGLSLTextureCanvas(GLSLTextureCanvas, glcanvas.GLCanvas):
    def __init__(self, parent, initial_palette, *args, **kwargs):
        """create the canvas """
        kwargs['attribList'] = (glcanvas.WX_GL_RGBA,
                                glcanvas.WX_GL_DOUBLEBUFFER,
                                glcanvas.WX_GL_MIN_ALPHA, 8, )
        glcanvas.GLCanvas.__init__(self, parent, *args, **kwargs)
        GLSLTextureCanvas.__init__(self, initial_palette)

    def ui_init_context(self):
        self.context = glcanvas.GLContext(self)

    def ui_bind_events(self):
        # execute self.onPaint whenever the parent frame is repainted
        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_SIZE, self.on_size)

    def ui_set_current(self):
        self.SetCurrent(self.context)

    def ui_swap_buffers(self):
        self.SwapBuffers()

    def ui_get_window_size(self):
        w, h = self.GetClientSize()
        return w, h

    def on_paint(self, event):
        """called when window is repainted """
        # make sure we have a texture to draw
        if not self.finished_init:
            self.init_context()
        self.on_draw()


class wxLegacyTextureCanvas(LegacyTextureCanvas, wxGLSLTextureCanvas, glcanvas.GLCanvas):
    def __init__(self, *args, **kwargs):
        wxGLSLTextureCanvas.__init__(self, *args, **kwargs)


if __name__ == "__main__":
    from ..atari800.colors import NTSC

    logging.basicConfig(level=logging.DEBUG)

    def run():
        app = wx.App()
        fr = wx.Frame(None, size=(640, 480), title='wxPython OpenGL programmable pipeline demo')
        canv = wxGLSLTextureCanvas(fr, NTSC)
        fr.Show()
        app.MainLoop()
        return 0

    sys.exit(run())
