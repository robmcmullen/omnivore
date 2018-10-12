# Modified from http://pyopengl.sourceforge.net/context/tutorials/shader_1.html
# to use wxPython GLCanvas control

import numpy as np

import OpenGL
import OpenGL.GL as gl
from OpenGL.arrays import vbo
from OpenGL.GL import shaders
from OpenGL.GL.ARB.geometry_shader4 import *

OpenGL.ERROR_CHECKING = True
OpenGL.ERROR_LOGGING = True
OpenGL.FULL_LOGGING = True
OpenGL.ERROR_ON_COPY = True

import wx
from wx import glcanvas

class GLProgram(object):
    def __init__(self, vertex, fragment, geometry, bindings=[]):
        vertex_shader = self.compile(vertex, gl.GL_VERTEX_SHADER)
        fragment_shader = self.compile(fragment, gl.GL_FRAGMENT_SHADER)
        geometry_shader = self.compile(geometry, gl.GL_GEOMETRY_SHADER)
        self.prog = self.link([vertex_shader, geometry_shader, fragment_shader], bindings=bindings)
        #self.prog = self.link([vertex_shader, fragment_shader], bindings=bindings)

    def compile(self, src, shader_type):
        shader = gl.glCreateShader(shader_type)
        gl.glShaderSource(shader, src)
        gl.glCompileShader(shader)
        result = gl.glGetShaderiv(shader, gl.GL_COMPILE_STATUS)
        if not(result):
            # TODO: this will be wrong if the user has
            # disabled traditional unpacking array support.
            raise RuntimeError(
                """Shader compile failure (%s): %s"""%(
                    result,
                    gl.glGetShaderInfoLog(shader),
                ),
                src,
                shader_type,
            )
        return shader

    def link(self, shader_objs, bindings=[]):
        prog = gl.glCreateProgram()
        for shader in shader_objs:
            gl.glAttachShader(prog, shader)
        for index, name in bindings:
            gl.glBindAttribLocation(prog, index, name)
        glProgramParameteriARB(prog, GL_GEOMETRY_INPUT_TYPE_ARB, gl.GL_TRIANGLES)
        glProgramParameteriARB(prog, GL_GEOMETRY_OUTPUT_TYPE_ARB, gl.GL_TRIANGLE_STRIP)
        gl.glLinkProgram(prog)
        link_status = gl.glGetProgramiv(prog, gl.GL_LINK_STATUS)
        if link_status == gl.GL_FALSE:
            raise RuntimeError(
                """Link failure (%s): %s"""%(
                link_status,
                gl.glGetProgramInfoLog(prog),
            ))
        for shader in shader_objs:
            gl.glDeleteShader(shader)
        return prog

    def __enter__(self):
        gl.glUseProgram(self.prog)

    def __exit__(self, type, value, traceback):
        #gl.glBindVertexArray(0)
        gl.glUseProgram(0)


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
    geometry_shader_src = """
//GEOMETRY SHADER from https://www.khronos.org/opengl/wiki/Geometry_Shader_Examples
#version 120
#extension GL_ARB_geometry_shader4 : enable
///////////////////////

void main()
{
  //increment variable
  int i;
  vec4 vertex;
  /////////////////////////////////////////////////////////////
  //This example has two parts
  //   step a) draw the primitive pushed down the pipeline
  //            there are gl_VerticesIn # of vertices
  //            put the vertex value into gl_Position
  //            use EmitVertex => 'create' a new vertex
  //           use EndPrimitive to signal that you are done creating a primitive!
  //   step b) create a new piece of geometry
  //           I just do the same loop, but offset the x by a little bit
  //Pass-thru!
  for(i = 0; i < gl_VerticesIn; i++)
  {
    gl_Position = gl_PositionIn[i];
    EmitVertex();
  }
  EndPrimitive();
}
"""
#   //New piece of geometry!
#   for(i = 0; i < gl_VerticesIn; i++)
#   {
#     vertex = gl_PositionIn[i];
#     vertex.x = vertex.x + .1;
#     gl_Position = vertex;
#     EmitVertex();
#   }
#   EndPrimitive();
# }
# """

    def init_context(self):
        """init the texture - this has to happen after an OpenGL context
        has been created
        """

        # make the OpenGL context associated with this canvas the current one
        self.SetCurrent(self.context)

        self.shader_prog = GLProgram(self.vertex_shader_src, self.fragment_shader_src, self.geometry_shader_src)
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

        # With the geometry shader active, running into:
        #  Traceback (most recent call last):
        #   File "opengl-geomshader1.py", line 150, in onPaint
        #     self.onDraw()
        #   File "opengl-geomshader1.py", line 164, in onDraw
        #     gl.glDrawArrays(gl.GL_TRIANGLES, 0, 9)
        #   File "errorchecker.pyx", line 53, in OpenGL_accelerate.errorchecker._ErrorChecker.glCheckError (src/errorchecker.c:1218)
        # OpenGL.error.GLError: GLError(
        #         err = 1282,
        #         description = 'invalid operation',
        #         baseOperation = glDrawArrays,
        #         cArguments = (GL_TRIANGLES, 0, 9)
        # )
        #
        # which is pretty unclear. From http://stackoverflow.com/questions/12017175/what-can-cause-gldrawarrays-to-generate-a-gl-invalid-operation-error it seems like there are a few causes:
        #
        # 

        with self.shader_prog:
            self.vbo.bind()
            try:
                gl.glEnableClientState(gl.GL_VERTEX_ARRAY);
                gl.glVertexPointerf(self.vbo)
                gl.glDrawArrays(gl.GL_TRIANGLE_STRIP, 0, 9)
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

