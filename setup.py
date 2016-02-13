from __future__ import with_statement

import sys

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

try:
    import atrcopy
    version = atrcopy.__version__
except RuntimeError, e:
    # If numpy isn't present, pull the version number from the error string
    version = str(e).split()[1]

classifiers = [
    "Programming Language :: Python :: 2",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: GNU General Public License (GPL)",
    "Topic :: Software Development :: Libraries",
    "Topic :: Utilities",
]

with open("README.rst", "r") as fp:
    long_description = fp.read()

if sys.platform.startswith("win"):
    scripts = ["scripts/atrcopy.bat"]
else:
    scripts = ["scripts/atrcopy"]

setup(name="atrcopy",
      version=version,
      author="Rob McMullen",
      author_email="feedback@playermissile.com>",
      url="https://github.com/robmcmullen/atrcopy",
      packages=["atrcopy"],
      scripts=scripts,
      description="Disk image utilities for Atari 8-bit emulators",
      long_description=long_description,
      license="GPL",
      classifiers=classifiers,
      install_requires = [
          'numpy',
          ],
      )
