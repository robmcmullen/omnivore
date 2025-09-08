from setuptools import Extension, setup
from Cython.Build import cythonize
import numpy

extensions = [
    Extension("omnivore.libimgui",
        sources=[
            "libimgui/imgui/imgui.cpp",
            "libimgui/imgui/imgui_demo.cpp",
            "libimgui/imgui/imgui_draw.cpp",
            "libimgui/imgui/imgui_tables.cpp",
            "libimgui/imgui/imgui_widgets.cpp",
            "libimgui/imgui/backends/imgui_impl_sdl2.cpp",
            "libimgui/imgui/backends/imgui_impl_opengl3.cpp",
            "libimgui/drawframe.cpp",
            "libimgui/mainloop.cpp",
            "libimgui/cython_mainloop.pyx",
        ],
        depends=[
            "libimgui/imgui_drawframe.h",
            "libimgui/imgui_mainloop.h",
            "libimgui/imgui/imconfig.h",
            "libimgui/imgui/imgui.h",
            "libimgui/imgui/imgui_internal.h",
            # "libimgui/imgui/imstb_rectpack.h",
            # "libimgui/imgui/imstb_textedit.h",
            # "libimgui/imgui/imstb_truetype.h",
            "libimgui/drawframe.h",
            "libimgui/mainloop.h",
        ],
        include_dirs=[
            numpy.get_include(),
            "libimgui/imgui",
            "libimgui/imgui/backends",
            "/usr/include/SDL2",
        ],
        libraries=['GL', 'SDL2'],
    ),
]
setup(
    name="Imgui Test From Cython",
    ext_modules=cythonize(extensions),
)
