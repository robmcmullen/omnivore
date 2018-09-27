
============
Omnivore 2.0
============



Abstract
========

Omnivore - the Atari 8-bit binary editor sponsored by the Player/Missile Podcast

Omnivore is a cross-platform app for modern hardware (running linux, MacOS and
Windows) to work with executables or disk images of Atari 8-bit and Apple ][+
machines.

Omnivore is a:

* binary editor
* disassembler
* miniassembler
* graphics editor
* map editor
* Jumpman level editor (Atari 8-bit platform only)

and soon will contain **a full emulator** for the Atari 8-bit and Apple ][+ machines with these features:

* rewind capability to return to previous point of emulation
* debugger able to step forward **and** backward
* change any portion of memory or processor state
* CPU history browser

A Tribute
---------

While producing the Player/Missile podcast, I have had many ideas about hacking
code on the 8-bits like I used to as a kid.  One of the tools I had was the
Omnimon system monitor board by CDY Consulting, an add-on board for the Atari
800 that provided a ROM-resident monitor similiar to what was available by
default on the Apple ][ series.  In fact, I originally named this program
Omnimon but felt that would be too confusing as there are people in the 8-bit
community who still use the original Omnimon hardware.  Using the prefix
"Omni-" is my tribute to all the fun I had with the Omnimon hardware.


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
    $ python installdeps.py
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

Should you change a cython file (e.g. omnivore8bit/arch/antic_speedups.pyx),
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


Disclaimer
==========

Omnivore, the Atari 8-bit binary editor sponsored by the Player/Missile Podcast
Copyright (c) 2014-2017 Rob McMullen (feedback@playermissile.com)

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


Enthought License
-----------------

Copyright (c) 2006-2014, Enthought, Inc.
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice, this
  list of conditions and the following disclaimer.
* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.
* Neither the name of Enthought, Inc. nor the names of its contributors may
  be used to endorse or promote products derived from this software without
  specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
