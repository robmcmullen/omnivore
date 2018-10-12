import sys
from setuptools import setup, find_packages, Extension

if sys.platform.startswith("win"):
    extra_compile_args = ["-DMSVC", "-D_CRT_SECURE_NO_WARNINGS"]
else:
    extra_compile_args = ["-g"]

extensions = [
  Extension("memtest.memtest",
    sources = ["memtest/memtest.c",
    "src/main.c",
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
            cythonize(["memtest/memtest.pyx"], gdb_debug=True)
            _sdist.run(self)
    cmdclass["sdist"] = sdist

setup(
  name = "memtest",
  cmdclass = cmdclass,
  ext_modules = extensions,
  packages = ["memtest"],
)
