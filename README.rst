======
Peppy2
======



ABSTRACT
========

peppy - (ap)Proximated (X)Emacs Powered by Python

This is a multi-format editor written in and extensible through Python.  It
attempts to provide an XEmacs-like multi- window, multi-tabbed interface.  The
architectural goal is to provide a system with low coupling in order to reduce
the work required to extend the editor with new major modes, minor modes, and
sidebars.  It is a rewrite of the original peppy, now based on the Enthought
framework instead of my old custom framework.


GOAL FOR REWRITE
================

Why a rewrite of the original peppy_ (which I'll call peppy1 even though it
never got to a 1.0 release)?

.. _peppy: http://peppy.flipturn.org

* **Simplify the code.**
  Peppy1 had the ability to have any major mode in any window, but this needed
  a lot of code to support minor modes switching in and out as tabs changed.
  I got it to work and all, but the code was quite convoluted.  Peppy2 only
  allows similar major modes in a window, and different major modes require
  a new window.  Not a huge inconvenience but saves a considerable amount of
  coding, so I'm happy with this tradeoff.  It allows me to use the Enthought
  Tasks framework pretty much as-is.

* **Make it easier for others to contribute.**
  Peppy1 was using my own framework which had a steep learning curve.
  Hopefully by moving to Enthought's framework, it will have a broader appeal.

* **Leverage other people's code.**
  I wrote a lot of custom code for stuff that I needed at the time, but now
  there are similar packages that others support and maintain.  For example,
  I wrote a virtual file system implementation that worked, but was a whole
  project in itself.  In the intervening years, PyFilesystem_ was written,
  removing the need for me to use my own code.

.. _PyFilesystem: http://packages.python.org/fs/index.html


PREREQUISITES
=============

python 2.7 (but not 3.x yet)
wxPython 2.9.x (but not 3.0 yet)

The Enthought framework is a custom build for peppy because I've enabled
current support for wx.  Enthought is transitioning to Qt is their primary GUI
toolkit and their wx support has been limited recently.  Fortunately Enthought
was designed to be toolkit agnostic and it was relatively easy to bring their
libraries up to date as compared to Qt.  My patches have not made it back to
Enthought yet, which is why I'm requiring the custom build::

    cd ~/src/enthought
    for name in traits; do echo $name; git clone https://github.com/enthought/$name.git; cd $name; python setup.py develop; cd ..; done
    for name in pyface traitsui; do echo $name; git clone https://github.com/robmcmullen/$name.git; cd $name; python setup.py develop; cd ..; done
    for name in apptools; do echo $name; git clone https://github.com/enthought/$name.git; cd $name; python setup.py develop; cd ..; done
    for name in envisage; do echo $name; git clone https://github.com/robmcmullen/$name.git; cd $name; python setup.py develop; cd ..; done


RUNNING THE PROGRAM
===================

This is still alpha software, so caveat emptor.  The only way to get it currently is to clone it from git::

    $ git clone https://github.com/robmcmullen/peppy2.git
    $ cd peppy2
    $ python run.py


DISCLAIMER
==========

peppy, (ap)Proximated (X)Emacs Powered by Python
Copyright (c) 2006-2014 Rob McMullen (robm@users.sourceforge.net)

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
