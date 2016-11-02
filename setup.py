import sys
from setuptools import setup, find_packages, Extension
from Cython.Build import cythonize
from Cython.Distutils import build_ext

if sys.platform.startswith("win"):
    extra_compile_args = ["-DMSVC", "-D_CRT_SECURE_NO_WARNINGS"]
else:
    extra_compile_args = []

extensions = [
  Extension("pyatasm.pyatasm_mac65",
    sources = ["src/pyatasm_mac65.pyx",
               "src/asm.c",
               "src/symbol.c",
               "src/parser.c",
               "src/setparse.c",
               "src/inc_path.c",
               "src/crc32.c",
               "src/atasm_err.c",
               "src/cython_interface.c",
              ],
    extra_compile_args = extra_compile_args,
    include_dirs = ["src"],
    )
]

setup(
  name = "pyatasm",
  version = "1.0",
  ext_modules = cythonize(extensions),
  packages = ["pyatasm"],
)
