#!/usr/bin/env python
"""wxPython OpenGL programmable pipeline

Based on:

https://gist.githubusercontent.com/binarycrusader/5823716a1da5f0273504/raw/f8e03f4e7be917bdb4cb81a8182bdccc4c00b9d2/textured_tri.py

Texture Buffer Objects: https://www.khronos.org/opengl/wiki/Buffer_Texture
https://gist.github.com/roxlu/5090067#file-griddrawer-h-L6-L31
"""
import sys
import ctypes
import numpy as np

import OpenGL.GL as gl
from OpenGL import GLU
from OpenGL.GL import shaders
from OpenGL.arrays import vbo

import PIL
from PIL import Image

import wx
from wx import glcanvas


class GLProgram(object):
    def __init__(self, vertex, fragment, bindings=[]):
        vertex_shader = self.compile(vertex, gl.GL_VERTEX_SHADER)
        fragment_shader = self.compile(fragment, gl.GL_FRAGMENT_SHADER)
        self.prog = self.link([vertex_shader, fragment_shader], bindings=bindings)

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
        gl.glBindVertexArray(0)
        gl.glUseProgram(0)



vertexShader = """
#version 140

in vec2 position;
in vec2 in_tex_coords;

out vec2 theCoords;

void main()
{
    gl_Position = gl_ModelViewProjectionMatrix * vec4(position, 0, 1);
    theCoords = in_tex_coords;
}
"""

fragmentShader = """
#version 140

uniform samplerBuffer palette;
uniform sampler2D tex;

in vec2 theCoords;

out vec4 out_color;

void main()
{
    vec4 pcolor;

    out_color = texture(tex, theCoords.st);
    //out_color = vec4(theCoords.st, 0, 255);
    pcolor = normalize(texelFetch(palette, int(out_color.r * 255)));
    // for some reason, the output color is half as bright as it should be
    out_color = vec4(pcolor.r * 2, pcolor.g*2, pcolor.b*2, 1.0);
    //out_color = vec4(pcolor.r, pcolor.g, pcolor.b, 1.0);
}
"""

NTSC = np.array([
(15, 15, 15, 255), (31, 31, 31, 255), (47, 47, 47, 255), (63, 63, 63, 255), (79, 79, 79, 255), (95, 95, 95, 255), (111, 111, 111, 255), (127, 127, 127, 255), (143, 143, 143, 255), (159, 159, 159, 255), (175, 175, 175, 255), (191, 191, 191, 255), (207, 207, 207, 255), (223, 223, 223, 255), (239, 239, 239, 255), (255, 255, 255, 255), (20, 36, 0, 255), (36, 52, 0, 255), (52, 68, 0, 255), (68, 84, 0, 255), (84, 100, 0, 255), (100, 116, 0, 255), (116, 132, 0, 255), (132, 148, 4, 255), (148, 164, 20, 255), (164, 180, 36, 255), (180, 196, 52, 255), (196, 212, 68, 255), (212, 228, 84, 255), (228, 244, 100, 255), (244, 255, 116, 255), (255, 255, 132, 255), (58, 12, 0, 255), (74, 28, 0, 255), (90, 44, 0, 255), (106, 60, 0, 255), (122, 76, 0, 255), (138, 92, 0, 255), (154, 108, 10, 255), (170, 124, 26, 255), (186, 140, 42, 255), (202, 156, 58, 255), (218, 172, 74, 255), (234, 188, 90, 255), (250, 204, 106, 255), (255, 220, 122, 255), (255, 236, 138, 255), (255, 252, 154, 255), (79, 0, 0, 255), (95, 8, 0, 255), (111, 24, 0, 255), (127, 40, 8, 255), (143, 56, 24, 255), (159, 72, 40, 255), (175, 88, 56, 255), (191, 104, 72, 255), (207, 120, 88, 255), (223, 136, 104, 255), (239, 152, 120, 255), (255, 168, 136, 255), (255, 184, 152, 255), (255, 200, 168, 255), (255, 216, 184, 255), (255, 232, 200, 255), (87, 0, 6, 255), (103, 0, 22, 255), (119, 11, 38, 255), (135, 27, 54, 255), (151, 43, 70, 255), (167, 59, 86, 255), (183, 75, 102, 255), (199, 91, 118, 255), (215, 107, 134, 255), (231, 123, 150, 255), (247, 139, 166, 255), (255, 155, 182, 255), (255, 171, 198, 255), (255, 187, 214, 255), (255, 203, 230, 255), (255, 219, 246, 255), (77, 0, 75, 255), (93, 0, 91, 255), (109, 3, 107, 255), (125, 19, 123, 255), (141, 35, 139, 255), (157, 51, 155, 255), (173, 67, 171, 255), (189, 83, 187, 255), (205, 99, 203, 255), (221, 115, 219, 255), (237, 131, 235, 255), (253, 147, 251, 255), (255, 163, 255, 255), (255, 179, 255, 255), (255, 195, 255, 255), (255, 211, 255, 255), (57, 0, 110, 255), (73, 0, 126, 255), (89, 7, 142, 255), (105, 23, 158, 255), (121, 39, 174, 255), (137, 55, 190, 255), (153, 71, 206, 255), (169, 87, 222, 255), (185, 103, 238, 255), (201, 119, 254, 255), (217, 135, 255, 255), (233, 151, 255, 255), (249, 167, 255, 255), (255, 183, 255, 255), (255, 199, 255, 255), (255, 215, 255, 255), (29, 0, 118, 255), (45, 3, 134, 255), (61, 19, 150, 255), (77, 35, 166, 255), (93, 51, 182, 255), (109, 67, 198, 255), (125, 83, 214, 255), (141, 99, 230, 255), (157, 115, 246, 255), (173, 131, 255, 255), (189, 147, 255, 255), (205, 163, 255, 255), (221, 179, 255, 255), (237, 195, 255, 255), (253, 211, 255, 255), (255, 227, 255, 255), (2, 2, 112, 255), (18, 18, 128, 255), (34, 34, 144, 255), (50, 50, 160, 255), (66, 66, 176, 255), (82, 82, 192, 255), (98, 98, 208, 255), (114, 114, 224, 255), (130, 130, 240, 255), (146, 146, 255, 255), (162, 162, 255, 255), (178, 178, 255, 255), (194, 194, 255, 255), (210, 210, 255, 255), (226, 226, 255, 255), (242, 242, 255, 255), (0, 17, 93, 255), (0, 33, 109, 255), (12, 49, 125, 255), (28, 65, 141, 255), (44, 81, 157, 255), (60, 97, 173, 255), (76, 113, 189, 255), (92, 129, 205, 255), (108, 145, 221, 255), (124, 161, 237, 255), (140, 177, 253, 255), (156, 193, 255, 255), (172, 209, 255, 255), (188, 225, 255, 255), (204, 241, 255, 255), (220, 255, 255, 255), (0, 30, 54, 255), (0, 46, 70, 255), (0, 62, 86, 255), (16, 78, 102, 255), (32, 94, 118, 255), (48, 110, 134, 255), (64, 126, 150, 255), (80, 142, 166, 255), (96, 158, 182, 255), (112, 174, 198, 255), (128, 190, 214, 255), (144, 206, 230, 255), (160, 222, 246, 255), (176, 238, 255, 255), (192, 254, 255, 255), (208, 255, 255, 255), (0, 40, 9, 255), (0, 56, 25, 255), (0, 72, 41, 255), (14, 88, 57, 255), (30, 104, 73, 255), (46, 120, 89, 255), (62, 136, 105, 255), (78, 152, 121, 255), (94, 168, 137, 255), (110, 184, 153, 255), (126, 200, 169, 255), (142, 216, 185, 255), (158, 232, 201, 255), (174, 248, 217, 255), (190, 255, 233, 255), (206, 255, 249, 255), (0, 44, 0, 255), (0, 60, 0, 255), (6, 76, 1, 255), (22, 92, 17, 255), (38, 108, 33, 255), (54, 124, 49, 255), (70, 140, 65, 255), (86, 156, 81, 255), (102, 172, 97, 255), (118, 188, 113, 255), (134, 204, 129, 255), (150, 220, 145, 255), (166, 236, 161, 255), (182, 252, 177, 255), (198, 255, 193, 255), (214, 255, 209, 255), (0, 40, 0, 255), (7, 56, 0, 255), (23, 72, 0, 255), (39, 88, 0, 255), (55, 104, 8, 255), (71, 120, 24, 255), (87, 136, 40, 255), (103, 152, 56, 255), (119, 168, 72, 255), (135, 184, 88, 255), (151, 200, 104, 255), (167, 216, 120, 255), (183, 232, 136, 255), (199, 248, 152, 255), (215, 255, 168, 255), (231, 255, 184, 255), (12, 30, 0, 255), (28, 46, 0, 255), (44, 62, 0, 255), (60, 78, 0, 255), (76, 94, 4, 255), (92, 110, 20, 255), (108, 126, 36, 255), (124, 142, 52, 255), (140, 158, 68, 255), (156, 174, 84, 255), (172, 190, 100, 255), (188, 206, 116, 255), (204, 222, 132, 255), (220, 238, 148, 255), (236, 254, 164, 255), (252, 255, 180, 255), (31, 21, 0, 255), (47, 37, 0, 255), (63, 53, 0, 255), (79, 69, 0, 255), (95, 85, 5, 255), (111, 101, 21, 255), (127, 117, 37, 255), (143, 133, 53, 255), (159, 149, 69, 255), (175, 165, 85, 255), (191, 181, 101, 255), (207, 197, 117, 255), (223, 213, 133, 255), (239, 229, 149, 255), (255, 245, 165, 255), (255, 255, 181, 255), ], dtype=np.uint8)
#NTSC /= 255.0
print NTSC

class GLSLTextureCanvas(glcanvas.GLCanvas):
    def __init__(self, parent, *args, **kwargs):
        """create the canvas """
        kwargs['attribList'] = (glcanvas.WX_GL_RGBA,
                                glcanvas.WX_GL_DOUBLEBUFFER,
                                glcanvas.WX_GL_MIN_ALPHA, 8, )
        glcanvas.GLCanvas.__init__(self, parent, *args, **kwargs)
        self.context = glcanvas.GLContext(self)

        self.vertex_data = np.array([
            # X,  Y,   U, V
            (-1, -1,   0, 0),
            ( 1, -1,   1, 0),
            (-1,  1,   0, 1),
            ( 1,  1,   1, 1)
        ], dtype=np.float32)
        self.shader_prog = None
        self.vao_id = None
        self.vbo_id = None
        self.display_texture = None
        self.tex_uniform = None

        self.finished_init = False
        self.bind_events()

    def bind_events(self):
        # execute self.onPaint whenever the parent frame is repainted
        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_SIZE, self.on_size)

    def init_shader(self):
        self.shader_prog = GLProgram(vertexShader, fragmentShader, [(0, "position"), (1, "in_tex_coords")])

        # load texture and assign texture unit for shaders
        self.tex_uniform = gl.glGetUniformLocation(self.shader_prog.prog, 'tex')
        self.palette_uniform = gl.glGetUniformLocation(self.shader_prog.prog, 'palette')

        # # load texture and assign texture unit for shaders
        # self.tex_uniform = gl.glGetUniformLocation(self.shader_prog.prog, 'tex')
        # self.palette_uniform = gl.glGetUniformLocation(self.shader_prog.prog, 'palette')

    def init_context(self):
        """init the texture - this has to happen after an OpenGL context
        has been created
        """

        # make the OpenGL context associated with this canvas the current one
        self.SetCurrent(self.context)

        self.init_shader()

        # Core OpenGL requires that at least one OpenGL vertex array be bound
        self.vao_id = gl.glGenVertexArrays(1)
        gl.glBindVertexArray(self.vao_id)

        # Need self.vbo_id for triangle vertices and texture UV coordinates
        self.vbo_id = gl.glGenBuffers(1)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vbo_id)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, self.vertex_data.nbytes, self.vertex_data,
            gl.GL_STATIC_DRAW)

        # load texture and assign texture unit for shaders
        self.display_texture = self.load_texture()

        # load palette and assign texture unit for shaders
        self.palette_id = gl.glGenBuffers(1)
        gl.glBindBuffer(gl.GL_TEXTURE_BUFFER, self.palette_id)
        gl.glBufferData(gl.GL_TEXTURE_BUFFER, NTSC.nbytes, NTSC,
            gl.GL_STATIC_DRAW)
        gl.glTexBuffer(gl.GL_TEXTURE_BUFFER, gl.GL_RGBA8, self.palette_id)
        self.palette_texture = gl.glGenTextures(1)

        gl.glEnableVertexAttribArray(0)
        gl.glEnableVertexAttribArray(1)
        gl.glVertexAttribPointer(0, 2, gl.GL_FLOAT, gl.GL_FALSE, 16, None)
        # the last parameter is a pointer
        gl.glVertexAttribPointer(1, 2, gl.GL_FLOAT, gl.GL_TRUE, 16, ctypes.c_void_p(8))

        # Finished
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, 0)
        gl.glBindVertexArray(0)

        self.finished_init = True

    def get_raw_texture_data(self, raw=None):
        if raw is None:
            w = 16
            h = 16
            raw = np.empty((256,), dtype=np.uint8)
            raw[:] = np.arange(256, dtype=np.uint8)
            raw = raw.reshape((h, w))
        return raw

    def calc_texture_data(self, raw=None):
        raw = self.get_raw_texture_data(raw)
        h, w = raw.shape
        data = np.empty((h * w, 4), dtype=np.uint8)
        src = raw.reshape((h * w))
        data[:,0] = src[:]
        data[:,1] = src[:]
        data[:,2] = src[:]
        data[:,3] = 255
        return data.reshape((h, w, 4))

    def load_texture(self, filename=None):
        if filename is not None or False:
            filename = "flicky.png"
            image = Image.open(filename)
            ix = image.size[0]
            iy = image.size[1]
            print ix, iy
            w, h = image.size
            rgba = 4
            data = image.tobytes("raw", "RGBX", 0, -1)
        else:
            data = self.calc_texture_data()
            h, w, rgba = data.shape

        # generate a texture id, make it current
        texture = gl.glGenTextures(1)
        gl.glBindTexture(gl.GL_TEXTURE_2D, texture)
        print "IN LOAD TEXTURE", texture, data.shape
        if texture is None:
            sys.exit()

        # texture mode and parameters controlling wrapping and scaling
        gl.glTexEnvf(gl.GL_TEXTURE_ENV, gl.GL_TEXTURE_ENV_MODE, gl.GL_REPLACE)
        gl.glTexParameterf(
            gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_REPEAT)
        gl.glTexParameterf(
            gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_REPEAT)
        gl.glTexParameterf(
            gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_NEAREST)
        gl.glTexParameterf(
            gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_NEAREST)
        gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, rgba, w, h, 0,
            gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, data)
        # gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, 0, 0, w, h,
        #                 gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, data)

        self.update_texture(texture, data)
        return texture

    def update_texture(self, texture, data):
        # map the image data to the texture. note that if the input
        # type is GL_FLOAT, the values must be in the range [0..1]
        print texture, data.shape
        # if True:
        #     return
        gl.glBindTexture(gl.GL_TEXTURE_2D, texture)
        h, w, rgba = data.shape
        gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, rgba, w, h, 0,
            gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, data)
        # gl.glTexSubImage2D(gl.GL_TEXTURE_2D, 0, 0, 0, w, h,
        #     gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, data)
        #gl.glBindTexture(gl.GL_TEXTURE_2D, 0)

    def on_size(self, event):
        """called when window is repainted """
        self.set_aspect()

        if self.finished_init:
            self.on_draw()

    def set_aspect(self):
        w, h = self.GetClientSizeTuple()
        a = (240.0 / 336.0) * w / h
        xspan = 1
        yspan = 1
        if a > 1:
            xspan *= a
        else:
            yspan = xspan/a

        gl.glViewport(0, 0, w, h);
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        gl.glOrtho(-1*xspan, xspan, -1*yspan, yspan, -1, 1)
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glLoadIdentity()

    def on_paint(self, event):
        """called when window is repainted """
        # make sure we have a texture to draw
        if not self.finished_init:
            self.init_context()
        self.on_draw()

    def on_draw(self):
        """draw function """

        # make the OpenGL context associated with this canvas the current one
        self.SetCurrent(self.context)

        self.render()

        # swap the front and back buffers so that the texture is visible
        self.SwapBuffers()

    def render(self):
        gl.glClearColor(0, 0, 0, 1)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)

        with self.shader_prog:
            # Activate array
            gl.glBindVertexArray(self.vao_id)

            # FIXME: Why does the following work? tex_uniform is 1,
            # palette_uniform is 0, but I have to set the uniform for
            # tex_uniform to 0 and the uniform for palette_uniform to 1.
            # Obviously I'm not understanding something.
            #
            # See: http://stackoverflow.com/questions/26622204
            # https://www.opengl.org/discussion_boards/showthread.php/174926-when-to-use-glActiveTexture

            # Activate texture
            print self.tex_uniform, self.palette_uniform, self.display_texture, self.palette_id
            gl.glActiveTexture(gl.GL_TEXTURE0 + self.tex_uniform)
            gl.glBindTexture(gl.GL_TEXTURE_2D, self.display_texture)
            gl.glUniform1i(self.tex_uniform, 0)

            # Activate palette texture
            gl.glActiveTexture(gl.GL_TEXTURE0 + self.palette_uniform)
            gl.glBindTexture(gl.GL_TEXTURE_BUFFER, self.palette_texture)
            gl.glTexBuffer(gl.GL_TEXTURE_BUFFER, gl.GL_RGBA8, self.palette_id)
            gl.glUniform1i(self.palette_uniform, 1)

            # # Activate array
            # gl.glBindVertexArray(self.vao_id)

            # draw triangle
            gl.glDrawArrays(gl.GL_TRIANGLE_STRIP, 0, 4)


class LegacyTextureCanvas(GLSLTextureCanvas):
    def init_shader(self):
        pass

    def calc_texture_data(self, raw=None):
        raw = self.get_raw_texture_data(raw)
        return raw

    def render(self):
        gl.glClearColor(0, 0, 0, 1)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)

        self.set_aspect()

        gl.glDisable(gl.GL_LIGHTING)
        # Don't cull polygons that are wound the wrong way.
        gl.glDisable(gl.GL_CULL_FACE)

        gl.glEnable(gl.GL_TEXTURE_2D)
        gl.glColor(1.0, 1.0, 1.0, 1.0)

        gl.glBindTexture(gl.GL_TEXTURE_2D, self.display_texture)
        gl.glBegin(gl.GL_TRIANGLE_STRIP)
        for pt in self.vertex_data:
            print pt
            gl.glTexCoord2f(pt[2], pt[3])
            gl.glVertex2f(pt[0], pt[1])
        gl.glEnd()


def run():
    app = wx.App()
    fr = wx.Frame(None, size=(640, 480), title='wxPython OpenGL programmable pipeline demo')
    canv = GLSLTextureCanvas(fr)
    fr.Show()
    app.MainLoop()
    return 0

if __name__ == "__main__":
    sys.exit(run())
