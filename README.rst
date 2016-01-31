
========
Omnivore
========



Abstract
========

Omnivore - the Atari 8-bit binary editor sponsored by the Player/Missile Podcast

While producing the Player/Missile podcast, I have had many ideas about hacking
code on the 8-bits like I used to as a kid.  One of the tools I had was the
Omnimon system monitor board by CDY Consulting, an add-on board for the Atari
800 that provided a ROM-resident monitor similiar to what was available by
default on the Apple ][ series.  In fact, I originally named this program
Omnimon but felt that would be too confusing as there are people in the 8-bit
community who still use the original Omnimon hardware.  Using the prefix
"Omni-" is my tribute to all the fun I had with the Omnimon hardware.

Omnivore is a cross-platform app for modern hardware (running linux, OS X and
Windows) to work with executables or disk images of Atari 8-bit machines.  (I
have long- term goals to support editing MAME ROMS and disk images of other
8-bit machines like the C64 and Apple ][.)

Omnivore is more than an Atari binary editor.  It can also create and edit maps
using character-based graphic tiles.  For instance: many games use the 5-color
ANTIC modes 4 or 5 to provide a complex scrolling background while using much
less memory than the multi-color bit-mapped modes.

In addition to supporting more platforms, I also intend to add support for
editing character sets and player-missile graphic shapes.


How To Run Omnivore
===================

Note that this is still beta-level software, so caveat emptor.

Binaries are available for Windows (64-bit) and Mac OS X 10.9 and up at the
`downloads <http://playermissile.com/omnivore/downloads>`_ page.

Binaries for linux are not currently available, although I would like to
provide packages for Ubuntu, Linux Mint and Gentoo at some point.  To run
on linux, you'll have to install it from source.  It's not that complicated;
apart from wxPython, everything can be installed from the `Python Package
Index <https://pypi.python.org/pypi>`_ using pip.


Installing From Source
======================

If you're running linux (like me!) or are interested in hacking on the code or making bug fixes or improvements, I'd recommend that you set up a python virtual environment with all the dependencies you need in there, rather than cluttering up your system's python. I've tested this on linux and OS X.

I do not develop this way on Windows; rather, I have a virtual machine dedicated to Omnivore development and install everything in the system python in that VM.

Prerequisites
-------------

* python 2.7 (but not 3.x yet)
* wxPython 3.0.x

The Enthought framework is a custom build for omnivore because I've enabled
current support for wx.  Enthought is transitioning to Qt is their primary GUI
toolkit and their wx support has been limited recently.  Fortunately Enthought
was designed to be toolkit agnostic and it was relatively easy to bring their
libraries up to date as compared to Qt.  My patches have not made it back
to Enthought yet, which is why I have included my versions of the Enthought
libraries in the Omnivore distribution.


Virtualenv Setup
----------------

First: download the `wxPython 3.0.2.0 <http://downloads.sourceforge.net/wxpython/wxPython-src-3.0.2.0.tar.bz2>`_ source.

Next, setup the virtual environment::

    virtualenv /data/virtualenv/wx3
    source $VIRTUAL_ENV/bin/activate
    mkdir src
    cd src
    tar xvf ~/Downloads/wxPython-src-3.0.2.0.tar.bz2 
    cd wxPython-src-3.0.2.0/
    ./configure --prefix=$VIRTUAL_ENV
    make -j 8
    make install
    cd wxPython
    python setup.py install

The ``activate`` script needs to be modified in order for the dynamic libraries to be discovered correctly. You can do this with a simple multi-line shell command::

    cat <<EOF >> $VIRTUAL_ENV/bin/activate
    LD_LIBRARY_PATH="$VIRTUAL_ENV/lib:$LD_LIBRARY_PATH"
    export LD_LIBRARY_PATH
    EOF

Running The Program
-------------------

Get the source from cloning it from github::

    $ git clone https://github.com/robmcmullen/omnivore.git
    $ cd omnivore
    $ python setup.py build_ext --inplace
    $ python run.py

You'll need the git package on your system, which is available through your
package manager.


Development
===========

Plugins
-------

Omnivore is extended by plugins.  Plugins are based on the `Enthought Framework`__
and are discovered using setuptools plugins.

__ http://docs.enthought.com/envisage/envisage_core_documentation/index.html

The plugin architecture is documented by Enthought, but is not terribly easy to
understand.  I intend to produce some sample plugins to provide some examples
in case others would like to provide more functionality to Omnivore.


Some Boring History
===================

Omnivore provides an XEmacs-like multi-window/multi-tabbed user interface and
is written in and extensible through Python.  It is built around the emacs
concept of major modes -- different views are presented to the user depending
on the type of data being edited.

It is a rewrite of peppy (my previous editor framework), but now it's based on
the Enthought Tasks framework instead of my old custom framework.  (Note that
even though Enthought has moved mostly toward Qt as the supported GUI toolkit,
I have forked Enthought's code and extended it with better wxPython support.
Only wxPython is supported as a GUI backend for Omnivore).  The architectural
goal is to provide a system with low coupling in order to reduce the work
required to extend the editor with new major modes, minor modes, and sidebars.

Why a rewrite of the original peppy_ editor?

.. _peppy: http://peppy.flipturn.org

* **Simplify the code.**
  Peppy had the ability to have any major mode in any window, but this needed
  a lot of code to support minor modes switching in and out as tabs changed.
  I got it to work and all, but the code was quite convoluted.  Omnivore only
  allows similar major modes in a window, and different major modes require
  a new window.  Not a huge inconvenience but saves a considerable amount of
  coding, so I'm happy with this tradeoff.  It allows me to use the Enthought
  Tasks framework pretty much as-is.

* **Make it easier for others to contribute.**
  Peppy was using my own framework which had a steep learning curve.
  Hopefully by moving to Enthought's framework, it will have a broader appeal.

* **Leverage other people's code.**
  I wrote a lot of custom code for stuff that I needed at the time, but now
  there are similar packages that others support and maintain.  For example,
  I wrote a virtual file system implementation that worked, but was a whole
  project in itself.  In the intervening years, PyFilesystem_ was written,
  removing the need for me to use my own code.

.. _PyFilesystem: http://packages.python.org/fs/index.html


Disclaimer
==========

Omnivore, the Atari 8-bit binary editor sponsored by the Player/Missile Podcast
Copyright (c) 2014-2016 Rob McMullen (feedback@playermissile.com)

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
