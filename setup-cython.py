# Cython setup file.  The compiled C extension is shipped with the sdist bundle
# so normal users will not need Cython.  If you make any changes to the cython
# .pyx files, rerun this file to regenerate the C extensions, and then use the
# regular setup.py to build the dynamic libraries.

import os
import sys
import shutil
import glob
import subprocess
from setuptools import find_packages
from distutils.core import setup
from distutils.extension import Extension
from Cython.Distutils import build_ext

# Numpy required before the call to setup if generating the C file using
# cython, but this shouldn't be a problem for normal users because the C
# files will be distributed with the source.
import numpy

# Cython needs some replacements for default build commands
cmdclass = {
    "build_ext": build_ext,
    }

ext_modules = [
    Extension("omnivore8bit.arch.antic_speedups",
              sources=["omnivore8bit/arch/antic_speedups.pyx"],
              include_dirs=[numpy.get_include()],
              )
    ]

packages = find_packages()

sys.argv.extend(["build_ext", "--inplace"])

setup(
    name = 'Omnivore',
    cmdclass = cmdclass,
    ext_modules = ext_modules,
    setup_requires = ["numpy"],
    license = "BSD",
    packages = packages,
    zip_safe = False,
    )
