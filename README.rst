================================================
omni8bit
================================================

A unified front-end to several emulators that allow normal operation and
debugging operations. This is used as the basis for the emulation support in
Omnivore.

Currently available are:

* libatari800, an embedded port of the Atari800 emulator
* lib6502, a generic 6502 emulator based on David Buchanan's 6502-emu



Prerequisites
=============


* C compiler
* python 2.7 (but not 3.x yet) capable of building C extensions
* numpy

Optionally:

* Cython (only if you want to modify the .pyx files)

The wxPython front-end additionally requires:

* wxPython 4 (aka Phoenix; wxPython 3 is no longer supported)
* pyopengl


Installation
============

omni8bit is available through PyPI, so the easiest way to get the code is to
simply::

    pip install omni8bit

To compile from source::

    git clone https://github.com/robmcmullen/omni8bit.git
    cd omni8bit
    python setup.py sdist && python setup.py build_ext --inplace

Your version of python must be able to build C extensions, which should be
automatic in most linux and on OS X. You may have to install the python
development packages on linux distributions like Ubuntu or Linux Mint.

Windows doesn't come with a C compiler, but happily Microsoft provides a
command line version of their Visual Studio compiler just for compiling Python
extensions! Download and install it from `here
<https://www.microsoft.com/en-us/download/details.aspx?id=44266>`_.

Windows compatibility code was used in libatari800:

* Dirent (a windows port of dirent.h) from https://github.com/tronkko/dirent
  and licensed under the MIT license which is GPL compatible


License
==========

* atari800 is Copyright (c) 1995-1998 David Firth and Copyright (c) 1998-2018 Atari800 development team
* Dirent is Copyright (c) 2015 Toni Rönkkö
* libatari800 is Copyright (c) 2018 Rob McMullen (feedback@playermissile.com)
* 6502-emu is Copyright (c) 2017 David Buchanan (licensed under the MIT license)

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with this program; if not, write to the Free Software Foundation, Inc.,
51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

