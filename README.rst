================================================
omni8bit
================================================

A unified front-end to several 8-bit CPU and system emulators to provide a
common set of control methods for both normal operation and debugging
purposes. This is used as the basis for the emulation support in Omnivore.

Currently available are:

* libatari800, an embedded port of the Atari800 emulator
* lib6502, a generic 6502 emulator based on David Buchanan's 6502-emu
* crabapple, a thin layer atop of lib6502 that provides some (tiny, small amount of) Apple ][+ compatibily


Other features include:

* ATasm; a 6502 cross-assembler based on MAC/65 syntax


Prerequisites
=============


* C compiler
* python 3.6 (or above) capable of building C extensions
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
    git submodule init
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


ATasm
=========

Omni8bit provides a python front-end to the usage of ATasm, meaning you can
compile 6502 code right from your python program.

From the ATasm readme::

    ATasm is a 6502 command-line cross-assembler that is compatible with the
    original Mac/65 macroassembler released by OSS software.  Code
    development can now be performed using "modern" editors and compiles
    with lightning speed.

A simple example::

    #!/usr/bin/env python

    from omni8bit.pyatasm import Assemble

    asm = Assemble("tests/works.m65")

    if asm:
        print(asm.segments)
        print(asm.equates)
        print(asm.labels)
    else:
        print(asm.errors)

Because omni8bit is a very thin wrapper around ATasm (and very little ATasm
code was changed) it needs to creates files to do its work. These files will be
created in the same directory as the source file, so the directory must be
writeable.

The segments attribute will contain a list of 3-tuples, each tuple being the
start address, the end address, and the bytes for each segment of the assembly.
A segment is defined as a contiguous sequence of bytes. If there is change of
origin, a new segment will be created.



License
==========

* atari800 is Copyright (c) 1995-1998 David Firth and Copyright (c) 1998-2018 Atari800 development team
* Dirent is Copyright (c) 2015 Toni Rönkkö
* libatari800 is Copyright (c) 2018 Rob McMullen (feedback@playermissile.com)
* 6502-emu is Copyright (c) 2017 David Buchanan (licensed under the MIT license)
* ATasm is Copyright (c) 1998-2014 Mark Schmelzenbach

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

