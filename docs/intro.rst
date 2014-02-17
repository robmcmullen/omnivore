************
Introduction
************

Peppy is an editor in the general sense -- even though it aims to be an
exemplary text editor, it allows you to edit lots of different types of data,
not *just* text.

It is designed in the spirit of Emacs and its concept of "major modes" --
editing modes that are tuned to edit a type of file using a specific user
interface.  Some major modes are very specific and only allow editing of
a certain type of file, while others are general and can be used to edit
different types of files.

Multiple views of the same document are permitted, and the views may be
different major modes.  A peppy window is organized into tabs, like the
Mozilla Firefox browser, and unlike Integrated Development Environments
(IDEs), multiple main windows can appear on the screen.

Target Audience
===============

Peppy is targeted at software developers and people who edit source code for
a living.  It is also designed to be extensible: if you program in the Python
language (and are so inclined), you can help improve the editor with new
functionality that you'd like to see in the editor.

Editing Source Code
-------------------

Source code editing is a major part of peppy.  The goal is to provide a
framework where new major modes can be added easily, and language support
beyond simple syntax highlighting can be shared among similar languages.  For
example, there is an auto indenting class based on regular expressions that
can be used to provide automatic indenting to many different languages simply
by changing the regex.  Many python based editors focus on editing python
code and hard-code too many aspects of the editor based on that goal.  Peppy
strives to be general and easy to extend.


Other Editing Modes
-------------------

The main difference between peppy and all the other python editors is the
concept of the major mode.  All other editors assume that you are going to
be editing text and make no provision for a different type of user interface.
Peppy provides many user interfaces depending on the type of file, and even
provides major modes that can edit more than one type of file, like HexEdit
major mode.


Cross Platform
==============

The ability to have the same user interface on multiple platforms is also a
goal of peppy.  Thanks to the wxPython toolkit, this is possible on the major
classes of platforms in existence today: unix/linux, Windows, and Mac OS X.
wxPython also provides a native look and feel, unlike Emacs which although can
be compiled on all platforms forces its own look on the platform.

In addition, because it is free, peppy can be taken with you to any computer.
Unlike proprietary editors like Wing IDE or TextMate that are either locked
to one computer by a license key or being platform specific, you are free to
use peppy wherever you want.


GPL Licensed
============

The main application code is licensed under the GPLv3, but peppy is actually
a combination of many licenses.  Most code is licensed under the GPLv2 or
the wxPython license, but because one component of the code (the virtual file
system) is under the GPLv3, the application as a whole must be licensed under
the GPLv3.  Parts of the code designed to be used as libraries are licensed
under the wxPython license so that they may be freely used with other wxPython
projects.