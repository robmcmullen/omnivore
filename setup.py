import sys
from setuptools import setup, find_packages, Extension

if sys.platform.startswith("win"):
    extra_compile_args = ["-DMSVC", "-D_CRT_SECURE_NO_WARNINGS"]
else:
    extra_compile_args = []

extensions = [
  Extension("pyatasm.pyatasm_mac65",
    sources = ["pyatasm/pyatasm_mac65.c",
               "pyatasm/cython_interface.c",
               "src/asm.c",
               "src/symbol.c",
               "src/parser.c",
               "src/setparse.c",
               "src/inc_path.c",
               "src/crc32.c",
               "src/atasm_err.c",
              ],
    extra_compile_args = extra_compile_args,
    include_dirs = ["src"],
    )
]

cmdclass = dict()

# Cython is only used when creating a source distribution. Users don't need
# to install Cython unless they are modifying the .pyx files themselves.
if "sdist" in sys.argv:
    from distutils.command.sdist import sdist as _sdist

    class sdist(_sdist):
        def run(self):
            from Cython.Build import cythonize
            cythonize(["pyatasm/pyatasm_mac65.pyx"])
            _sdist.run(self)
    cmdclass["sdist"] = sdist

execfile('pyatasm/_metadata.py')

setup(
  name = "pyatasm",
  version = __version__,
  author = __author__,
  author_email = __author_email__,
  url = __url__,
  classifiers = [c.strip() for c in """\
    Development Status :: 5 - Production/Stable
    Intended Audience :: Developers
    License :: OSI Approved :: GNU General Public License (GPL)
    Operating System :: MacOS
    Operating System :: Microsoft :: Windows
    Operating System :: OS Independent
    Operating System :: POSIX
    Operating System :: Unix
    Programming Language :: Python
    Topic :: Utilities
    Topic :: Software Development :: Assemblers
    """.splitlines() if len(c.strip()) > 0],
  description = "Python wrapper for ATasm, a 6502 cross-assembler using MAC/65 syntax",
  long_description = open('README.rst').read(),
  cmdclass = cmdclass,
  ext_modules = extensions,
  packages = ["pyatasm"],
)
