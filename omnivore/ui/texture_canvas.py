#!/usr/bin/env python
"""OpenGL programmable pipeline

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

import logging
log = logging.getLogger(__name__)
#log.setLevel(logging.DEBUG)


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
        #gl.glBindVertexArray(0)
        gl.glUseProgram(0)



vertexShader = """
#version 120

void main()
{
    gl_TexCoord[0] = gl_MultiTexCoord0;
    gl_Position = ftransform();
}
"""

fragmentShader = """
#version 120

uniform sampler1D palette;
uniform sampler2D tex;

void main()
{
    vec4 source;
    vec4 pcolor;

    source = texture2D(tex, gl_TexCoord[0].st);
    //gl_FragColor = vec4(gl_TexCoord[0].st, 0, 255);
    pcolor = texture1D(palette, source.r);
    gl_FragColor = (pcolor * 0.5) + (source * 0.5);
    gl_FragColor = pcolor;
    //gl_FragColor = vec4(1,0,0,1) + (pcolor * 0.001);
    //gl_FragColor = vec4(gl_TexCoord[0].st,0,1) + (pcolor * 0.001);
}
"""


class GLSLTextureCanvas(object):
    def __init__(self, initial_palette):
        self.ui_init_context()
        self.init_attributes()
        self.ui_bind_events()
        self.set_palette_data(initial_palette)

    def ui_init_context(self):
        """Initialize the GL context from the UI toolkit"""
        raise NotImplementedError

    def ui_bind_events(self):
        """Bind any event handlers that the UI toolkit needs for repainting or
        updating the display."""
        raise NotImplementedError

    def ui_set_current(self):
        """Set the current GLContext using the UI toolkit-specific code, using
        the context created by ui_init_context"""
        raise NotImplementedError

    def ui_swap_buffers(self):
        """Swaps the OpenGL back and front buffers for double buffering"""
        raise NotImplementedError

    def ui_get_window_size(self):
        """Return the width and height of the drawable area (sometimes referred
        to as the client area) of the window"""
        raise NotImplementedError

    def init_attributes(self):
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
        self.ui_set_current()

        self.init_shader()

        # Core OpenGL requires that at least one OpenGL vertex array be bound
        #self.vao_id = gl.glGenVertexArrays(1)
        #gl.glBindVertexArray(self.vao_id)

        # Need self.vbo_id for triangle vertices and texture UV coordinates
        self.vbo_id = gl.glGenBuffers(1)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vbo_id)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, self.vertex_data.nbytes, self.vertex_data,
            gl.GL_STATIC_DRAW)

        # load texture and assign texture unit for shaders
        self.display_texture = self.load_texture()

        self.palette_texture = self.load_palette()
        # # load palette and assign texture unit for shaders
        # self.palette_id = gl.glGenBuffers(1)
        # gl.glBindBuffer(gl.GL_TEXTURE_BUFFER, self.palette_id)
        # gl.glBufferData(gl.GL_TEXTURE_BUFFER, NTSC.nbytes, NTSC,
        #     gl.GL_STATIC_DRAW)
        # gl.glTexBuffer(gl.GL_TEXTURE_BUFFER, gl.GL_RGBA8, self.palette_id)
        # self.palette_texture = gl.glGenTextures(1)

        #gl.glEnableVertexAttribArray(0)
        #gl.glEnableVertexAttribArray(1)
        #gl.glVertexAttribPointer(0, 2, gl.GL_FLOAT, gl.GL_FALSE, 16, None)
        # the last parameter is a pointer
        #gl.glVertexAttribPointer(1, 2, gl.GL_FLOAT, gl.GL_TRUE, 16, ctypes.c_void_p(8))

        # Finished
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, 0)
        #gl.glBindVertexArray(0)

        self.finished_init = True

    def get_color_indexed_texture_data(self, raw=None):
        if raw is None:
            w = 16
            h = 16
            raw = np.empty((256,), dtype=np.uint8)
            raw[:] = np.arange(256, dtype=np.uint8)
            raw = raw.reshape((h, w))
        return raw

    def get_rgba_texture_data(self, raw=None):
        raw = self.get_color_indexed_texture_data(raw)
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
            from PIL import Image
            filename = "flicky.png"
            image = Image.open(filename)
            ix = image.size[0]
            iy = image.size[1]
            log.debug("image: %s, %dx%d" % (filename, ix, iy))
            w, h = image.size
            rgba = 4
            data = image.tobytes("raw", "RGBX", 0, -1)
        else:
            data = self.get_rgba_texture_data(-1)
            h, w, rgba = data.shape

        # generate a texture id, make it current
        texture = gl.glGenTextures(1)
        gl.glBindTexture(gl.GL_TEXTURE_2D, texture)
        log.debug("load_texture: glGenTextures returns %d, shape=%s" % (texture, data.shape))
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
        log.debug("update_texture: texture=%d, shape=%s" % (texture, data.shape))
        # if True:
        #     return
        gl.glBindTexture(gl.GL_TEXTURE_2D, texture)
        h, w, rgba = data.shape
        gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, rgba, w, h, 0,
            gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, data)
        # gl.glTexSubImage2D(gl.GL_TEXTURE_2D, 0, 0, 0, w, h,
        #     gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, data)
        #gl.glBindTexture(gl.GL_TEXTURE_2D, 0)

    def set_palette_data(self, data):
        self.palette_data = data
        if self.finished_init:
            self.update_palette()

    def load_palette(self):
        # generate a texture id, make it current
        texture = gl.glGenTextures(1)
        gl.glBindTexture(gl.GL_TEXTURE_1D, texture)
        log.debug("load_palette: texture=%d, shape=%s" % (texture, self.palette_data.shape))
        if texture is None:
            sys.exit()
        entries, rgba = self.palette_data.shape

        # texture mode and parameters controlling wrapping and scaling
        gl.glTexEnvf(gl.GL_TEXTURE_ENV, gl.GL_TEXTURE_ENV_MODE, gl.GL_REPLACE)
        gl.glTexParameterf(
            gl.GL_TEXTURE_1D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP)
        gl.glTexParameterf(
            gl.GL_TEXTURE_1D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_NEAREST)
        gl.glTexParameterf(
            gl.GL_TEXTURE_1D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_NEAREST)
        gl.glTexImage1D(gl.GL_TEXTURE_1D, 0, rgba, entries, 0,
            gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, self.palette_data)
        return texture

    def update_palette(self):
        """Update the palette colors"""
        raise NotImplementedError

    def on_size(self, event):
        """called when window is repainted """
        self.set_aspect()

        if self.finished_init:
            self.on_draw()

    def set_aspect(self):
        if not self.finished_init:
            return
        w, h = self.ui_get_window_size()
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

    def on_draw(self):
        """draw function """

        # make the OpenGL context associated with this canvas the current one
        self.ui_set_current()

        self.render()

        # swap the front and back buffers so that the texture is visible
        self.ui_swap_buffers()

    def render(self):
        gl.glClearColor(0, 0, 0, 1)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        gl.glEnable(gl.GL_TEXTURE_1D)
        gl.glEnable(gl.GL_TEXTURE_2D)
        gl.glDisable(gl.GL_LIGHTING)
        gl.glDisable(gl.GL_CULL_FACE)
        gl.glColor(1.0, 1.0, 1.0, 1.0)

        with self.shader_prog:
            # Activate array
            #gl.glBindVertexArray(self.vao_id)

            # FIXME: Why does the following work? tex_uniform is 1,
            # palette_uniform is 0, but I have to set the uniform for
            # tex_uniform to 0 and the uniform for palette_uniform to 1.
            # Obviously I'm not understanding something.
            #
            # See: http://stackoverflow.com/questions/26622204
            # https://www.opengl.org/discussion_boards/showthread.php/174926-when-to-use-glActiveTexture

            # Activate texture
            #print self.tex_uniform, self.palette_uniform, self.display_texture, getattr(self, 'palette_id') if hasattr(self, 'palette_id') else "None"
            gl.glActiveTexture(gl.GL_TEXTURE0 + self.tex_uniform)
            gl.glBindTexture(gl.GL_TEXTURE_2D, self.display_texture)
            gl.glUniform1i(self.tex_uniform, 1)

            # Activate palette texture
            gl.glActiveTexture(gl.GL_TEXTURE0 + self.palette_uniform)
            if hasattr(self, 'palette_id'):
                gl.glBindTexture(gl.GL_TEXTURE_BUFFER, self.palette_texture)
                gl.glTexBuffer(gl.GL_TEXTURE_BUFFER, gl.GL_RGBA8, self.palette_id)
            else:
                gl.glBindTexture(gl.GL_TEXTURE_1D, self.palette_texture)

            gl.glUniform1i(self.palette_uniform, 0)

            # # Activate array
            # gl.glBindVertexArray(self.vao_id)
            #gl.glEnableClientState(gl.GL_VERTEX_ARRAY)  # FIXME: deprecated
            #gl.glVertexPointer(2, gl.GL_FLOAT, 0, None)  # FIXME: deprecated

            # draw triangle
            #gl.glDrawArrays(gl.GL_TRIANGLE_STRIP, 0, 4)
            gl.glBindTexture(gl.GL_TEXTURE_2D, self.display_texture)
            gl.glBegin(gl.GL_TRIANGLE_STRIP)
            for pt in self.vertex_data:
                gl.glTexCoord2f(pt[2], pt[3])
                gl.glVertex2f(pt[0], pt[1])
            gl.glEnd()


class LegacyTextureCanvas(GLSLTextureCanvas):
    def init_shader(self):
        pass

    def get_rgba_texture_data(self, raw):
        raise NotImplementedError("subclass must return shape (w,h,4) array")

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
            gl.glTexCoord2f(pt[2], pt[3])
            gl.glVertex2f(pt[0], pt[1])
        gl.glEnd()
