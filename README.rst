=======
ATRip
=======

Python library for hierarchical filesystem parsing on Atari 8-bit and Apple ][
disk images. The successor to atrcopy, this is under heavy development and is
still in a beta state. It is the basis for disk image support in `Omnivore 2
<https://github.com/robmcmullen/omnivore>`_.

Pronounced "uh-trip", the name is a happy coincidence that a dictionary word
exists that is the quasi-portmanteau of "ATR" (the Atari 8 bit disk image
container) & "rip" (extracting stuff from images). The actual word is a
nautical term: "atrip" as in "the anchor is atrip", meaning the ship's anchor
is off the bottom. I have no particular affinity for ships, but that I had some
justification in the portmanteau is enough for me.

.. contents:: **Contents**

Prerequisites
=============

Python
------

Supported Python versions:

* Python 3.6 (and later)

Runtime Dependencies
---------------------

* numpy
* jsonpickle
* lz4

It will be automatically installed when installing with ``pip`` as described
below.

Development Dependencies
------------------------

* pytest
* pytest-cov (optional)

The test suite uses pytest and pytest-cov, but these are not required for
normal installation.

Installation
============

``ATRip`` is available in the `PyPI <https://pypi.org/atrip/>`_
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
* ``DCM``: Disk Communicator images, Bob Puff's compression format for Atari disk images
* ``CAS``: Atari cassette images
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

**Note:** Atari ROM cartridges are supported in both both plain binary and
atari800 ``.car`` format


Archives
-----------------

Archives containing multiple disk images are supported, where each disk image
within the archive will be given a disk number and is addressable using that
prefix.

+---------------------+----------+------+-------+------------------------------+
| Container           | File Ext | Read | Write | Status                       |
+=====================+==========+======+=======+==============================+
| Zip File            | .zip     | Yes  | Yes   | Fully supported              |
+---------------------+----------+------+-------+------------------------------+
| Tar File            | .tar     | Yes  | Yes   | Fully supported              |
+---------------------+----------+------+-------+------------------------------+

Archives may also be compressed with any of the general purpose compression
formats listed below.


Supported Compression Formats
---------------------------------------

Compression is supported transparently, so any type of disk image compressed
with any of the following formats can be used directly, without first
decompressing it before running ``ATRip``.

Chaining is supported to an arbitrary depth, meaning that one compression
algorithm can be applied to the output of another. This is not practical except
in limited cases, as in a Disk Communicator image that is subsequently gzipped
(image.dcm.gz). But cases that actually make compression worse will be handled
as well, like image.gz.bz2.xz.bz2.gz.gz.gz.


+---------------------+------------+------+-------+------------------------------+
| Compression Format  | File Ext   | Read | Write | Status                       |
+=====================+============+======+=======+==============================+
| gzip                | .gz        | Yes  | Yes   | Fully supported              |
+---------------------+------------+------+-------+------------------------------+
| bzip2               | .bz2       | Yes  | Yes   | Fully supported              |
+---------------------+------------+------+-------+------------------------------+
| lzma                | .xz, .lzma | Yes  | Yes   | Fully supported              |
+---------------------+------------+------+-------+------------------------------+
| lzw (Unix compress) | .Z         | Yes  | No    | Read only [#]_               |
+---------------------+------------+------+-------+------------------------------+
| lz4                 | .lz4       | Yes  | Yes   | Fully supported              |
+---------------------+------------+------+-------+------------------------------+
| Disk Communicator   | .dcm       | Yes  | Yes   | Atari images only [#]_       |
+---------------------+------------+------+-------+------------------------------+

.. [#] Contains code from the
   `BSD-licensed python implementation <https://github.com/umeat/unlzw>`_
   of Mark Adler's reference C implementation of unlzw. See LICENSE.unlzw in the
   source distribution for more details.

.. [#] Not general purpose compression; Atari 720 or 1040 sector disk images only.
   Contains my own python reimplementation of the DCM algorithms based on the
   `GPL code in acvt <http://ftp.pigwa.net/stuff/collections/holmes%20cd/Holmes%202/PC%20Atari%20Programming%20Utils/Acvt%20v1.04/index.html>`_


Segment Structure
==================

::

    Collection:      example.atr: plain file
    Container:          D1: 92176 bytes, compression=none
    Header:                 ATR Header (16 bytes)
    DiskImage:              Atari SD (90K) Floppy Disk Image, size=92160, filesystem=Atari DOS 2
    BootSegment:                Boot Sectors (384 bytes)
    Segment:                        Boot Header (6 bytes)
    Segment:                        Boot Code (378 bytes @ 0006)
    VTOC:                       DOS2 SD VTOC (128 bytes)
    Directory:                  Directory (1024 bytes)
    Dirent:                         File #0  (.2.u. ) 004 DOS     SYS  035
    FileType:                           DOS.SYS (4375 bytes) Unknown file type
    Dirent:                         File #1  (.2.u. ) 039 DUP     SYS  054
    AtariObjectFile:                    DUP.SYS (6708 bytes) Atari 8-bit Object File
    ObjSegment:                             Segment #1 (6706 bytes)
    Segment:                                    [$2949-$4376] (6702 bytes)



References
==========

* http://www.atariarchives.org/dere/chapt09.php
* http://atari.kensclassics.org/dos.htm
* http://www.crowcastle.net/preston/atari/
* http://www.atarimax.com/jindroush.atari.org/afmtatr.html
* https://archive.org/details/Beneath_Apple_DOS_OCR

Related Atari Projects
----------------------

* `atrcopy <http://pypi.org/atrcopy>`_: Precursor to ``ATRip``; stable and includes command line utility to manipulate disk images.
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
