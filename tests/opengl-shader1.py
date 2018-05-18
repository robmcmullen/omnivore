# Modified from http://pyopengl.sourceforge.net/context/tutorials/shader_1.html
# to use wxPython GLCanvas control

import numpy as np

import OpenGL.GL as gl
from OpenGL.arrays import vbo
from OpenGL.GL import shaders

import wx
from wx import glcanvas

class GLProgram(object):
    def __init__(self, vertex, fragment):
        self.vertex_shader = self.compile(vertex, gl.GL_VERTEX_SHADER)
        self.fragment_shader = self.compile(fragment, gl.GL_FRAGMENT_SHADER)
        self.prog = self.link(self.vertex_shader, self.fragment_shader)

    def compile(self, src, type):
        try:
            shader = shaders.compileShader(src, type)
        except (gl.GLError, RuntimeError) as err:
            print('shader compile error', err)
        return shader

    def link(self, *shader_objs):
        try:
            prog = shaders.compileProgram(*shader_objs)
        except (gl.GLError, RuntimeError) as err:
            print('shader link error', err)
        return prog

    def __enter__(self):
        shaders.glUseProgram(self.prog)

    def __exit__(self, type, value, traceback):
        shaders.glUseProgram(0)


class Canvas(glcanvas.GLCanvas):

    def __init__(self, parent):
        """create the canvas """
        super(Canvas, self).__init__(parent)
        self.context = glcanvas.GLContext(self)
        self.texture = None
        self.vbo = vbo.VBO(np.array( [ [ 0, 1, 0 ], [ -1,-1, 0 ], [ 1,-1, 0 ], [ 2,-1, 0 ], [ 4,-1, 0 ], [ 4, 1, 0 ], [ 2,-1, 0 ], [ 4, 1, 0 ], [ 2, 1, 0 ], ], dtype=np.float32))

        self.shader_prog = None
        # execute self.onPaint whenever the parent frame is repainted
        self.Bind(wx.EVT_PAINT, self.onPaint)

    vertex_shader_src = """
#version 120
void main() {
    gl_Position = gl_ModelViewProjectionMatrix * gl_Vertex;
}
"""
    fragment_shader_src = """
#version 120
void main() {
   gl_FragColor = vec4( 0, 1, 0, 1 );
}
"""

    def init_context(self):
        """init the texture - this has to happen after an OpenGL context
        has been created
        """

        # make the OpenGL context associated with this canvas the current one
        self.SetCurrent(self.context)

        self.shader_prog = GLProgram(self.vertex_shader_src, self.fragment_shader_src)
        gl.glClearColor(0,0,0,0)

    def onPaint(self, event):
        """called when window is repainted """
        # make sure we have a texture to draw
        if not self.texture:
            self.init_context()
        self.onDraw()

    def onDraw(self):
        """draw function """

        # make the OpenGL context associated with this canvas the current one
        self.SetCurrent(self.context)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)

        with self.shader_prog:
            self.vbo.bind()
            try:
                gl.glEnableClientState(gl.GL_VERTEX_ARRAY);
                gl.glVertexPointerf(self.vbo)
                gl.glDrawArrays(gl.GL_TRIANGLES, 0, 9)
            finally:
                self.vbo.unbind()
                gl.glDisableClientState(gl.GL_VERTEX_ARRAY);

        # swap the front and back buffers so that the texture is visible
        self.SwapBuffers()


def run():
    app = wx.App()
    fr = wx.Frame(None, size=(512, 512), title='wxPython OpenGL programmable pipeline demo')
    canv = Canvas(fr)
    fr.Show()
    app.MainLoop()

if __name__ == "__main__":
    run()

