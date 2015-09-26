from __future__ import with_statement

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

import atrcopy

classifiers = [
    "Programming Language :: Python :: 2",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: GNU General Public License (GPL)",
    "Topic :: Software Development :: Libraries",
    "Topic :: Utilities",
]

with open("README.rst", "r") as fp:
    long_description = fp.read()

setup(name="atrcopy",
      version=atrcopy.__version__,
      author="Rob McMullen",
      author_email="feedback@playermissile.com>",
      url="https://github.com/robmcmullen/atrcopy",
      py_modules=["atrcopy"],
      description="Disk image utilities for Atari 8-bit emulators",
      long_description=long_description,
      license="GPL",
      classifiers=classifiers,
      )
