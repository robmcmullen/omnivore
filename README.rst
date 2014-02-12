ABSTRACT
========

peppy - (ap)Proximated (X)Emacs Powered by Python

This is a multi-format editor written in and extensible through Python.  It
attempts to provide an XEmacs-like multi- window, multi-tabbed interface.  The
architectural goal is to provide a system with low coupling in order to reduce
the work required to extend the editor with new major modes, minor modes, and
sidebars.  It is a rewrite of the original peppy, now based on the Enthought
framework instead of my old custom framework.


PREREQUISITES
=============

python 2.7 (but not 3.x yet)
wxPython 2.9.x (but not 3.0 yet)

The Enthought framework is a custom build for peppy because I've enabled
current support for wx.  Enthought is transitioning to Qt is their primary GUI
toolkit and their wx support has been limited recently.  Fortunately Enthought
was designed to be toolkit agnostic and it was relatively easy to bring their
libraries up to date as compared to Qt.  My patches have not made it back to
Enthought yet, which is why I'm requiring the custom build.

cd ~/src/enthought
for name in traits; do echo $name; git clone https://github.com/enthought/$name.git; cd $name; python setup.py develop; cd ..; done
for name in pyface traitsui envisage; do echo $name; git clone https://github.com/robmcmullen/$name.git; cd $name; python setup.py develop; cd ..; done
for name in apptools enable; do echo $name; git clone https://github.com/enthought/$name.git; cd $name; python setup.py develop; cd ..; done


RUNNING THE PROGRAM
===================

This is still alpha software, so caveat emptor.  The only way to get it currently is to clone it from git:

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
