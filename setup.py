import sys
import glob
from setuptools import setup, find_packages, Extension

if sys.platform.startswith("win"):
    extra_compile_args = ["-DMSVC", "-D_CRT_SECURE_NO_WARNINGS"]
else:
    extra_compile_args = []

import numpy

extensions = []
for parser in glob.glob("hardcoded_parse_*.c"):
    print parser
    cpu = parser.replace("hardcoded_parse_", "").replace(".c", "")
    mod_name = "disasm_speedups_%s" % cpu
    mod_file = "%s.c" % mod_name
    with open("disasm_speedups.c", "r") as fh:
        src = fh.read()
        src = src.replace("disasm_speedups", mod_name)
        with open(mod_file, "w") as wfh:
            wfh.write(src)
    e = Extension(mod_name,
    sources = [mod_file,
               "hardcoded_parse_%s.c" % cpu,
              ],
    extra_compile_args = extra_compile_args,
    include_dirs = [numpy.get_include()],
    )
    extensions.append(e)

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

setup(
    name = "udis",
    ext_modules = extensions,
)