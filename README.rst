========
pyatasm
========

Python wrapper for ATasm, a mostly Mac/65 compatible 6502 cross-assembler


Summary
========

From the ATasm readme::

    ATasm is a 6502 command-line cross-assembler that is compatible with the
    original Mac/65 macroassembler released by OSS software.  Code
    development can now be performed using "modern" editors and compiles
    with lightning speed.

pyatasm is a python wrapper that uses the (slightly modified) C code from
ATasm. It provides the front end to the assembler and returns the bytes (and
other metadata) from the assembly.


Prerequisites
-------------

* python 2.7 (but not 3.x yet) capable of building C extensions

Installation
------------

pyatasm is available through PyPI::

    pip install pyatasm

or you can compile from source::

    git clone https://github.com/robmcmullen/pyatasm.git
    cd pyatasm
    python setup install

Your version of python must be able to build C extensions, which should be
automatic in most linux and on OS X. You may have to install the python
development packages on linux distributions like Ubuntu or Linux Mint.

Windows doesn't come with a C compiler, but happily, Microsoft provides a
cut-down version of their Visual Studio compiler just for compiling Python
extensions! Download and install it from
`here <https://www.microsoft.com/en-us/download/details.aspx?id=44266>`_.

Developers
----------

If you check out the pyatasm source from the git repository or you want to
modify pyatasm and change the .pyx file, you'll need Cython. The .pyx file is
compiled to C as a side effect of using the command::

    python setup.py sdist



Usage
=====

A simple example::

    #!/usr/bin/env python

    from pyatasm import Assemble

    asm = Assemble("tests/works.m65")

    if asm:
        print asm.segments
        print asm.equates
        print asm.labels
    else:
        print asm.errors

Because pyatasm is a very thin wrapper around ATasm (and very little ATasm code
was changed) it needs to creates files to do its work. These files will be
created in the same directory as the source file, so the directory must be
writeable.

The segments attribute will contain a list of 3-tuples, each tuple being the
start address, the end address, and the bytes for each segment of the assembly.
A segment is defined as a contiguous sequence of bytes. If there is change of
origin, a new segment will be created.



License
==========

pyatasm, python wrapper for ATasm

ATasm is Copyright (c) 1998-2014 Mark Schmelzenbach
pyatasm is Copyright (c) 2016 Rob McMullen (feedback@playermissile.com)

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

