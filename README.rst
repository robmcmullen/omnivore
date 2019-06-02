
=========================================================
Omnivore 2.0 (pre-release, very very alpha version)
=========================================================



Abstract
========

Omnivore - the retrocomputing reverse engineering toolbox

Omnivore is a cross-platform app for modern hardware (running linux, MacOS and
Windows) to work with executables or media images of Atari 8-bit, Apple ][+, and other retrocomputer machines and game consoles.

Features include (in various states of operation at the moment):

* emulator with debugger (see below)
* binary editor
* disassembler (6502, 65C02, 6809, and many other 8-bit CPU architectures)
* 6502 cross-assembler (ATasm, uses MAC/65 syntox)
* graphics editor
* map editor
* Jumpman level editor (Atari 8-bit platform only)

Emulator
---------

Omnivore provides unified front-end to several 8-bit CPU and system emulators
to provide a common set of control methods for both normal operation and
debugging purposes. This is used as the basis for the emulation support in
Omnivore.

Currently available are:

* libatari800, an embedded port of the `atari800 emulator <https://atari800.github.io/>`_
* lib6502, a generic 6502 emulator based on `David Buchanan's 6502-emu <https://github.com/DavidBuchanan314/6502-emu>`_
* crabapple, a thin layer atop of lib6502 that provides some (tiny, small amount of) Apple ][+ compatibility

The debugger includes:

* rewind capability to return to previous point of emulation
* debugger able to step forward (**and**, soon, backward)
* change any portion of memory or processor state
* CPU instruction history browser
* memory access visualizer
* memory map labels, used for disassembler
* customizable memory viewer using labels and data types




A Tribute
---------

While producing the Player/Missile podcast, I have had many ideas about hacking
code on the 8-bits like I used to as a kid. One of the tools I had was the
Omnimon system monitor board by CDY Consulting, an add-on board for the Atari
800 that provided a ROM-resident monitor similar to what was provided in the Apple ][+ hardware.  In fact, I originally named this program Omnimon but felt
that would be too confusing as there are people in the 8-bit community who
still use the original Omnimon hardware.  Using the prefix "Omni-" is my
tribute to all the fun I had with the Omnimon hardware.


How To Run Omnivore
===================

Omnivore 2.0 is still under heavy development. When it gets to a more stable
state, I will create binaries for Windows and MacOS. These instructions will be
for that time.


Windows & MacOS
---------------

Binaries are available for Windows 7 and later (64-bit
only) and Mac OS X 10.9 and later and at the `home page
<http://playermissile.com/omnivore/>`_ or directly through the `github
releases <https://github.com/robmcmullen/omnivore/releases>`_ page.

Linux (or Using a Virtual Environment)
--------------------------------------

Binaries for linux are not currently available, although I would like to
provide packages for Ubuntu, Linux Mint and Gentoo at some point.

To run on linux, you'll have to have a Python 3.6 environment set up. How to do
this will depend on your distribution, but there's a good chance that if it is
not installed already, your package manager will be able to install it for you.

I'd recommend using a virtual environment so you don't clutter up the system
python, but if you're willing to risk it, the virtualenv step is optional::

    virtualenv /some/path/to/your/virtualenv
    source /some/path/to/your/virtualenv/bin/activate

Then, install with::

    pip install omnivore

On some distributions, you will need development libraries to install wxPython
4 because pip needs to compile it from source. On ubuntu this is::

    sudo apt-get install libgstreamer1.0-dev libgtk-3-dev libwebkit2gtk-4.0-dev

And on Gentoo this is::

    emerge -av net-libs/webkit-gtk

Installing From Source
======================

If you're interested in hacking on the code or making bug fixes or
improvements, you can install and run the source distribution.

Prerequisites
-------------

* Python 3.6 and above, capable of building C extensions
* git

Note: Python 2 is not supported.

Your version of python must be able to build C extensions, which should be
automatic in most linux and on OS X. You may have to install the python
development packages on linux distributions like Ubuntu or Linux Mint.

Windows doesn't come with a C compiler, but happily, Microsoft provides a
cut-down version of their Visual Studio compiler just for compiling Python
extensions! Download and install it from
`here <https://www.microsoft.com/en-us/download/details.aspx?id=44266>`_.

Virtualenv Setup
----------------

I'd recommend using a different virtualenv than the one used above because it's possible that python packages that the git source depends on may be at different versions than the current published version::

    python -m venv /some/path/to/your/development/virtualenv
    source /some/path/to/your/development/virtualenv/bin/activate

Get the source from cloning it from github::

    $ git clone https://github.com/robmcmullen/omnivore.git
    $ cd omnivore
    $ git submodule init
    $ git submodule update
    $ python setup.py build_ext --inplace


Running the Program
-------------------

Once the C modules are built (the Enthought library requires a C module and
Omnivore has those several Cython modules for graphic speedups), you can run
the program from the main source directory using::

    $ python run.py


Development
===========

Graphics Speedups
-----------------

The Cython extension is used to speed up some of the time-critical code (like
repainting all the character graphics), but it is only required if you were
going to debug or recompile those specific .pyx files.  Cython is not needed
for hacking on the python code.

Should you change a cython file (e.g. omnivore/arch/antic_speedups.pyx),
use the command ``python setup-cython.py`` to turn that into a C extension,
then use ``python setup.py build_ext --inplace`` to regenerate the dynamic
libraries.

Plugins
-------

Omnivore will be able to be extended using plugins based on the
`Enthought Framework`__ which are discovered automatically at runtime
using setuptools plugins.

__ http://docs.enthought.com/envisage/envisage_core_documentation/index.html

The plugin architecture is documented by Enthought, but is not terribly easy to
understand.  I intend to produce some sample plugins to provide some examples
in case others would like to provide more functionality to Omnivore.


Usage
=======

In addition to the Omnivore program itself, this module can be used in other
projects. For example, Omnivore supplies a python front-end to the cross
assembler ATasm, meaning you can compile 6502 code right from your python
program.

ATasm Example
-----------------

From the ATasm readme::

    ATasm is a 6502 command-line cross-assembler that is compatible with the
    original Mac/65 macroassembler released by OSS software.  Code
    development can now be performed using "modern" editors and compiles
    with lightning speed.

A simple example::

    #!/usr/bin/env python

    from omnivore.assembler import find_assembler

    assembler_cls = find_assembler("atasm")
    assembler = assembler_cls()

    asm = assembler.assemble("libatasm/atasm/tests/works.m65")

    if asm:
        print(asm.segments)
        print(asm.equates)
        print(asm.labels)
    else:
        print(asm.errors)

Because omnivore provides a very thin wrapper around ATasm (and very little
ATasm code was changed) it needs to creates files to do its work. These files
will be created in the same directory as the source file, so the directory must
be writeable.

The segments attribute will contain a list of 3-tuples, each tuple being the
start address, the end address, and the bytes for each segment of the assembly.
A segment is defined as a contiguous sequence of bytes. If there is change of
origin, a new segment will be created.



Disclaimer
==========

No warranty is expressed or implied. Do not taunt Happy Fun Ball.


Licenses
========

Omnivore, the 8-bit binary editor, emulator, and debugger
Copyright (c) 2014-2018 Rob McMullen (feedback@playermissile.com)

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with this program; if not, write to the Free Software Foundation, Inc.,
51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.


Other Licenses
---------------

* `dirent.h <https://github.com/tronkko/dirent>`_ is Copyright (c) 2015 Toni Rönkkö. It is Windows compatibility code used in libatari800 and licensed under the MIT license which is GPL compatible. See the file LICENSE.MIT in the source distribution.

* atari800 is Copyright (c) 1995-1998 David Firth and Copyright (c) 1998-2018 Atari800 development team, licensed under the GPL, same as Omnivore itself.

* `6502-emu <https://github.com/DavidBuchanan314/6502-emu>`_ is Copyright (c) 2017 David Buchanan and licensed under the MIT license. See the file LICENSE.MIT in the source distribution.

* `udis <https://github.com/jefftranter/udis>`_ is Copyright (c) Jeff Tranter. It is the basis for libudis, my fast C disassembler. It is licensed under the Apache 2.0 license. See the file LICENSE.apache in the source distribution.

* `ATasm <http://atari.miribilist.com/atasm/>`_ is Copyright (c) 1998-2014 Mark Schmelzenbach and licensed under the GPL, the same as Omnivore itself.

* `tinycthread <https://tinycthread.github.io/>`_ is Copyright (c) 2012 Marcus Geelnard and Copyright (c) 2013-2016 Evan Nemerson, licensed under the zlib/libpng license. See the file LICENSE.tinycthread in the source distribution.

