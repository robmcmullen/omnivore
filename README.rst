atrip
=======

Python library for hierarchical filesystem parsing on Atari 8-bit and Apple ][
disk images. The successor to `atrcopy <https://pypi.org/atrcopy>`_, this is
under heavy development and is not stable.

.. contents:: **Contents**

Prerequisites
=============

Python
------

Supported Python versions:

* Python 3.6 (and later)

Dependencies
------------

* numpy

It will be automatically installed when installing ``atrip`` with ``pip`` as
described below.

For development, pytest is used to run the test suite, but this is not required
for normal installation of ``atrip``.

Installation
============

``atrip`` is available in the `PyPI <https://pypi.org/atrip/>`_
and installable using ``pip``::

    pip install atrip

Linux and macOS note: if numpy needs to be installed on your system, it may be
compiled from source which can take several minutes.

Features
========

* list contents of disk images
* copy files to and from disk images
* delete files from disk images
* create new disk images
* concatenate binary data together into a file on the disk image
* compile assembly source into binary files if `pyatasm <https://pypi.org/pyatasm>`_ is installed


Supported Formats
=================

Supported Disk Image Types
--------------------------

* ``XFD``: XFormer images, basically raw disk dumps
* ``ATR``: Nick Kennedy's disk image format; includes 16 byte header
* ``DSK``: Apple ][ DOS 3.3 disk image; raw sector dump

Supported File System Formats
-----------------------------

+----------------+-------------+---------+-------+-------------------+
| File System    | Platform    | Read    | Write | Status            |
+================+=============+=========+=======+===================+
| DOS 2 (90K)    | Atari 8-bit | Yes     | Yes   | Fully supported   |
+----------------+-------------+---------+-------+-------------------+
| DOS 2 (180K)   | Atari 8-bit | Yes     | Yes   | Fully supported   |
+----------------+-------------+---------+-------+-------------------+
| DOS 2.5 (130K) | Atari 8-bit | Yes     | Yes   | Fully supported   |
+----------------+-------------+---------+-------+-------------------+
| DOS 3 (130K)   | Atari 8-bit | No      | No    | Unimplemented     |
+----------------+-------------+---------+-------+-------------------+
| SpartaDOS      | Atari 8-bit | No      | No    | Under development |
+----------------+-------------+---------+-------+-------------------+
| MyDOS          | Atari 8-bit | Partial | No    | Under development |
+----------------+-------------+---------+-------+-------------------+
| DOS 3.3        | Apple ][    | Yes     | Yes   | Fully supported   |
+----------------+-------------+---------+-------+-------------------+
| ProDOS 8       | Apple ][    | No      | No    | Unimplemented     |
+----------------+-------------+---------+-------+-------------------+


Other Supported Formats
-----------------------

+----------+----------------------------------+---------+-------+-----------------+
| Format   | Platform/description             | Read    | Write | Status          |
+==========+==================================+=========+=======+=================+
| ``.xex`` | Atari 8-bit executable files     | Yes     | Yes   | Fully supported |
+----------+----------------------------------+---------+-------+-----------------+
| KBoot    | Atari 8-bit ``xex`` in boot disk | Yes     | Yes   | Fully supported |
+----------+----------------------------------+---------+-------+-----------------+
| ``.car`` | Atari 8-bit cartridge images     | Yes     | No    | Read only       |
+----------+----------------------------------+---------+-------+-----------------+
| BSAVE    | Apple ][ ``BSAVE`` data          | Yes     | Yes   | Fully supported |
+----------+----------------------------------+---------+-------+-----------------+
| ``.zip`` | MAME ROM zipfiles                | Partial | No    | Experimental    |
+----------+----------------------------------+---------+-------+-----------------+

**Note:** Atari ROM cartridges are supported in both both plain binary and
atari800 ``.car`` format


Supported Compression/Container Formats
---------------------------------------

Compressed disk images are supported transparently, so any type of disk image
compressed with one of the supported container formats can be used directly,
without first decompressing it before running ``atrip``.

+--------------------+----------+------+-------+------------------------------+
| Container          | File Ext | Read | Write | Status                       |
+====================+==========+======+=======+==============================+
| gzip               | .gz      | Yes  | No    | Read only                    |
+--------------------+----------+------+-------+------------------------------+
| bzip2              | .bz2     | Yes  | No    | Read only                    |
+--------------------+----------+------+-------+------------------------------+
| lzma               | .xz      | Yes  | No    | Read only                    |
+--------------------+----------+------+-------+------------------------------+
| Disk Communicator  | .dcm     | No   | No    | Recognized but unimplemented |
+--------------------+----------+------+-------+------------------------------+


References
==========

* http://www.atariarchives.org/dere/chapt09.php
* http://atari.kensclassics.org/dos.htm
* http://www.crowcastle.net/preston/atari/
* http://www.atarimax.com/jindroush.atari.org/afmtatr.html
* https://archive.org/details/Beneath_Apple_DOS_OCR

Related Atari Projects
----------------------

* `atrcopy <http://pypi.org/atrcopy>`_: Precursor to ``atrip``; stable and includes command line utility to manipulate disk images.
* `franny <http://atari8.sourceforge.net/franny.html>`_: (C, macOS/linux) Command line program to manage Atari DOS 2 and SpartaDOS II image and file systems
* `dir2atr <http://www.horus.com/~hias/atari/>`_: (Win) Suite of command line programs to manage Atari disk images and DOS 2/MyDOS file systems
* `atadim <http://raster.infos.cz/atari/forpc/atadim.htm>`_: (Win) Graphical program to manage Atari disk images and DOS 2/MyDOS file systems

Related Apple Projects
----------------------

Turns out there are a ton of Apple ][ disk image viewers and editors! I was pointed to the list from the `diskii project <https://github.com/zellyn/diskii>`_, so I've included most of that list here.

* `a2disk <https://github.com/jtauber/a2disk>`_ (Python 3) DOS 3.3 reader and Applesoft BASIC detokenizer
* `cppo <https://github.com/RasppleII/a2server/blob/master/scripts/tools/cppo>`_ (Python) a script from the `a2server <http://ivanx.com/a2server/>`_ project to read DOS 3.3 and ProDOS disk images
* `Driv3rs <https://github.com/thecompu/Driv3rs>`_ (Python) Apple III SOS DSK image utility
* `c2d <https://github.com/datajerk/c2d>`_: (C, Win/macOS/linux) Command line program to create bootable Apple disk images (no file system)
* `Apple Commander <http://applecommander.sourceforge.net/>`_: (Java) Command line program to manage Apple disk images and file systems
* `Cider Press <http://a2ciderpress.com/>`_: (Win) Graphical program to manage Apple disk images and file systems
* `diskii <https://github.com/zellyn/diskii>`_: (Go) Command line tool, under development
* `Cadius <http://brutaldeluxe.fr/products/crossdevtools/cadius/index.html>`_ (Win) Brutal Deluxe's commandline tools
* `dsktool <https://github.com/cybernesto/dsktool.rb>`_ (Ruby)
* `Apple II Disk Tools <https://github.com/cmosher01/Apple-II-Disk-Tools>`_ (C)
* `libA2 <https://github.com/madsen/perl-libA2>`_ (Perl)
* `AppleSAWS <https://github.com/markdavidlong/AppleSAWS>`_ (Qt, Win/macOS/linux) very cool looking GUI
* `DiskBrowser <https://github.com/dmolony/DiskBrowser>`_ (Java) GUI tool that even displays Wizardry levels and VisiCalc files!
* `dos33fsprogs <https://github.com/deater/dos33fsprogs>`_ (C)
* `apple2-disk-util <https://github.com/slotek/apple2-disk-util>`_ (Ruby)
* `dsk2nib <https://github.com/slotek/dsk2nib>`_ (C)
* `standard-delivery <https://github.com/peterferrie/standard-delivery>`_ (6502 assembly) Apple II single-sector fast boot-loader
