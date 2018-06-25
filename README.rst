atrcopy
=======

Python command line utility to manage file systems on Atari 8-bit and Apple ][
disk images.

.. contents:: **Contents**

Prerequisites
=============

Python
------

Starting with ``atrcopy`` 7.0, Python 3.6 is **required**. Python 2 support has
been dropped. Python 3.7 and beyond will be supported when they are released,
but 3.6 will probably remain the minimum version. From what I know now of
future Python versions, I don't plan on requiring any language features beyond
3.6.

Supported Python versions:

* Python 3.6 (and later)

If you need Python 2 support, ``atrcopy`` 6.5 and earlier supports:

* Python 2.7
* Python 3.5
* Python 3.6

Dependencies
------------

* numpy

It will be automatically installed when installing ``atrcopy`` with ``pip`` as
described below.

For development, pytest is used to run the test suite, but this is not required
for normal installation of ``atrcopy``.

Installation
============

``atrcopy`` is available in the `PyPI <https://pypi.python.org/pypi/atrcopy/>`_
and installable using ``pip``::

    pip install atrcopy

Linux and macOS note: if numpy needs to be installed on your system, it may be
compiled from source which can take several minutes.

Features
========

* list contents of disk images
* copy files to and from disk images
* delete files from disk images
* create new disk images
* concatenate binary data together into a file on the disk image
* compile assembly source into binary files if `pyatasm <https://pypi.python.org/pypi/pyatasm>`_ is installed

**Note:** The command line argument structure was changed starting with
``atrcopy`` 4.0 -- it is now based on subcommands, much like ``git`` uses ``git
pull``, ``git clone``, ``git branch``, etc. Upgrading from a version prior to
4.0 will require modification of scripts that use ``atrcopy`` 3.x-style command
line arguments.


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

Starting with ``atrcopy`` 8.0, compressed disk images are supported
transparently, so any type of disk image compressed with one of the supported
container formats can be used directly, without first decompressing it before
running ``atrcopy``.

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


Usage
=====

::

    atrcopy DISK_IMAGE <global options> COMMAND <command options>

where the available commands include:

* ``list``: list files on the disk image. This is the default if no command is specified
* ``create``: create a new disk image
* ``add``: add files to a disk image
* ``extract``: copy files from the disk image to the local file system
* ``assemble``: create a binary file from ATasm source, optionally including segments containing raw binary data
* ``boot``: create a boot disk using various binary data as input
* ``delete``: delete files from the disk image
* ``vtoc``: show and manipulate the VTOC for images that support it

Except when using the ``--help`` option, the ``DISK_IMAGE`` is always required
which points to the path on your local file system of the disk image.
``COMMAND`` is one of the commands listed above, and the commands may be
abbreviated as shown here::

    $ atrcopy --help
    usage: atrcopy DISK_IMAGE [-h] [-v] [--dry-run] COMMAND ...

    Manipulate files on several types of 8-bit computer disk images. Type 'atrcopy
    DISK_IMAGE COMMAND --help' for list of options available for each command.

    positional arguments:
      COMMAND
        list (t,ls,dir,catalog)
                            List files on the disk image. This is the default if
                            no command is specified
        crc                 List files on the disk image and the CRC32 value in
                            format suitable for parsing
        extract (x)         Copy files from the disk image to the local filesystem
        add (a)             Add files to the disk image
        create (c)          Create a new disk image
        assemble (s,asm)    Create a new binary file in the disk image
        boot (b)            Create a bootable disk image
        delete (rm,del)     Delete files from the disk image
        vtoc (v)            Show a formatted display of sectors free in the disk
                            image
        segments            Show the list of parsed segments in the disk image

    optional arguments:
      -h, --help            show this help message and exit
      -v, --verbose
      --dry-run             don't perform operation, just show what would have
                            happened


Help for available options for each command is available without specifying a
disk image, using a command line like::

    atrcopy COMMAND --help

so for example, the help for assembling a binary file is::

    $ atrcopy asm --help
    usage: atrcopy DISK_IMAGE assemble [-h] [-f] [-s [ASM [ASM ...]]]
                                       [-d [DATA [DATA ...]]] [-r RUN_ADDR] -o
                                       OUTPUT

    optional arguments:
      -h, --help            show this help message and exit
      -f, --force           allow file overwrites in the disk image
      -s [ASM [ASM ...]], --asm [ASM [ASM ...]]
                            source file(s) to assemble using pyatasm
      -d [DATA [DATA ...]], -b [DATA [DATA ...]], --data [DATA [DATA ...]]
                            binary data file(s) to add to assembly, specify as
                            file@addr. Only a portion of the file may be included;
                            specify the subset using standard python slice
                            notation: file[subset]@addr
      -r RUN_ADDR, --run-addr RUN_ADDR, --brun RUN_ADDR
                            run address of binary file if not the first byte of
                            the first segment
      -o OUTPUT, --output OUTPUT
                            output file name in disk image



Examples
========

List all files on a disk image::

    $ atrcopy DOS_25.ATR 
    DOS_25.ATR: ATR Disk Image (size=133120 (1040x128B), crc=0 flags=0 unused=0) Atari DOS Format: 1010 usable sectors (739 free), 6 files
    File #0  (.2.u.*) 004 DOS     SYS  037
    File #1  (.2.u.*) 041 DUP     SYS  042
    File #2  (.2.u.*) 083 RAMDISK COM  009
    File #3  (.2.u.*) 092 SETUP   COM  070
    File #4  (.2.u.*) 162 COPY32  COM  056
    File #5  (.2.u.*) 218 DISKFIX COM  057

Extract a file::

    $ atrcopy DOS_25.ATR extract SETUP.COM
    DOS_25.ATR: ATR Disk Image (size=133120 (1040x128B), crc=0 flags=0 unused=0) Atari DOS Format: 1010 usable sectors (739 free), 6 files
    extracting SETUP.COM -> SETUP.COM

Extract all files::

    $ atrcopy DOS_25.ATR extract --all
    DOS_25.ATR: ATR Disk Image (size=133120 (1040x128B), crc=0 flags=0 unused=0) Atari DOS Format: 1010 usable sectors (739 free), 6 files
    extracting File #0  (.2.u.*) 004 DOS     SYS  037 -> DOS.SYS
    extracting File #1  (.2.u.*) 041 DUP     SYS  042 -> DUP.SYS
    extracting File #2  (.2.u.*) 083 RAMDISK COM  009 -> RAMDISK.COM
    extracting File #3  (.2.u.*) 092 SETUP   COM  070 -> SETUP.COM
    extracting File #4  (.2.u.*) 162 COPY32  COM  056 -> COPY32.COM
    extracting File #5  (.2.u.*) 218 DISKFIX COM  057 -> DISKFIX.COM

Extract all, using the abbreviated command and converting to lower case on the
host file system::

    $ atrcopy DOS_25.ATR x --all -l
    DOS_25.ATR: ATR Disk Image (size=133120 (1040x128B), crc=0 flags=0 unused=0) Atari DOS Format: 1010 usable sectors (739 free), 6 files
    extracting File #0  (.2.u.*) 004 DOS     SYS  037 -> dos.sys
    extracting File #1  (.2.u.*) 041 DUP     SYS  042 -> dup.sys
    extracting File #2  (.2.u.*) 083 RAMDISK COM  009 -> ramdisk.com
    extracting File #3  (.2.u.*) 092 SETUP   COM  070 -> setup.com
    extracting File #4  (.2.u.*) 162 COPY32  COM  056 -> copy32.com
    extracting File #5  (.2.u.*) 218 DISKFIX COM  057 -> diskfix.com

Creating Disk Images
--------------------

Several template disk images are included in the distribution, and these can be
used to create blank disk images that subsequent uses of ``atrcopy`` can
reference.

The available disk images can be viewed using ``atrcopy create --help``::

    $ atrcopy create --help
    usage: atrcopy DISK_IMAGE create [-h] [-f] TEMPLATE

    positional arguments:
      TEMPLATE     template to use to create new disk image; see below for list of
                   available built-in templates

    optional arguments:
      -h, --help   show this help message and exit
      -f, --force  replace disk image file if it exists

    available templates:
      dos2dd          Atari 8-bit DOS 2 double density (180K), empty VTOC
      dos2ed          Atari 8-bit DOS 2 enhanced density (130K), empty VTOC
      dos2ed+2.5      Atari 8-bit DOS 2 enhanced density (130K) DOS 2.5 system disk
      dos2sd          Atari 8-bit DOS 2 single density (90K), empty VTOC
      dos2sd+2.0s     Atari 8-bit DOS 2 single density (90K) DOS 2.0S system disk
      dos33           Apple ][ DOS 3.3 (140K) standard RWTS, empty VTOC
      dos33autobrun   Apple ][ DOS 3.3 (140K) disk image for binary program
                      development: HELLO sets fullscreen HGR and calls BRUN on
                      user-supplied AUTOBRUN binary file

To create a new image, use::

    $ atrcopy game.dsk create dos33autobrun

which will create a new file called ``game.dsk`` based on the ``dos33autobrun``
image.

``dos33autobrun`` is a special image that can be used to create autoloading
binary programs. It contains an Applesoft Basic file called ``HELLO`` which
will autoload on boot. It sets the graphics mode to fullscreen hi-res graphics
(the first screen at $2000) and executes a ``BRUN`` command to start a binary
file named ``AUTOBRUN``. ``AUTOBRUN`` doesn't exist in the image, it's for you
to supply.


Creating a Custom Boot Disk
---------------------------

Blocks of binary data can be combined into a boot disk in either ATR format for
Atari or DSK format for Apple::

    $ atrcopy boot --help
    usage: atrcopy DISK_IMAGE boot [-h] [-f] [-s [ASM [ASM ...]]]
                                   [-d [DATA [DATA ...]]] [-b [OBJ [OBJ ...]]]
                                   [-r RUN_ADDR]

    optional arguments:
      -h, --help            show this help message and exit
      -f, --force           allow file overwrites in the disk image
      -s [ASM [ASM ...]], --asm [ASM [ASM ...]]
                            source file(s) to assemble using pyatasm
      -d [DATA [DATA ...]], --data [DATA [DATA ...]]
                            binary data file(s) to add to assembly, specify as
                            file@addr. Only a portion of the file may be included;
                            specify the subset using standard python slice
                            notation: file[subset]@addr
      -b [OBJ [OBJ ...]], --obj [OBJ [OBJ ...]], --bload [OBJ [OBJ ...]]
                            binary file(s) to add to assembly, either executables
                            or labeled memory dumps (e.g. BSAVE on Apple ][),
                            parsing each file's binary segments to add to the
                            resulting disk image at the load address for each
                            segment
      -r RUN_ADDR, --run-addr RUN_ADDR, --brun RUN_ADDR
                            run address of binary file if not the first byte of
                            the first segment

One of ``-s``, ``-d``, or ``-b`` must be speficied to provide the source for
the boot disk. The ``-b`` argument can take an Atari binary in XEX format, and
will properly handle multiple segments within that file. If no starting address
is supplied (or, if using an XEX, to override the start address normally
contained within the XEX), use the ``-r`` option. Otherwise, the run address
will point to the first byte of the first binary segment.


Creating Programs on the Disk Image
-----------------------------------

The simple assembler included in ``atrcopy`` can create binary programs by
connecting binary data together in a single file and specifying a start address
so it can be executed by the system's binary run command.

It is also possible to assemble text files that use the MAC/65 syntax, because
support for `pyatasm <https://pypi.python.org/pypi/pyatasm>`_ is built-in (but
optional). MAC/65 is a macro assembler originally designed for the Atari 8-bit
machines but since it produces 6502 code it can be used to compile for any
machine that uses the 6502: Apple, Commodore, etc.

Creating Atari 8-bit Executables
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Atari 8-bit object files include a small header and an arbitrary number of
segments. Each segment defines a contiguous block of data with a start and end
address. If the file has multiple segments, they will be processed in the order
they appear in the file, not by segment start address.

This example creates a new ``xex`` on a disk that combines the segments of an
already existing executable with some new assembly code.

After creating the test image with::

    $ atrcopy test.atr create dos2sd
    using dos2sd template:
      Atari 8-bit DOS 2 single density (90K), empty VTOC
    created test.atr: ATR Disk Image (size=92160 (720x128B), crc=0 flags=0 unused=0) Atari DOS Format: 707 usable sectors (707 free), 0 files

this command compiles the file ``test_header.s`` and prefixes it to the
existing executable::

    $ atrcopy test.atr asm -s test_header.s -b air_defense_v18.xex -o test.xex -f
    test.atr: ATR Disk Image (size=92160 (720x128B), crc=0 flags=0 unused=0) Atari DOS Format: 707 usable sectors (707 free), 0 files
    fname: test_header.s
    Pass 1: Success. (0 warnings)
    Pass 2: 
    adding 0600 - 0653, size=0053 ($53 bytes @ 0600) from test_header.s assembly
    adding 02e2 - 02e4, size=0002 ($2 bytes @ 02e2) from test_header.s assembly
    adding  $02e0-$02e2 ($0002 @ $0006) from air_defense_v18.xex
    adding  $6000-$6bd4 ($0bd4 @ $000c) from air_defense_v18.xex
    total file size: $c3d (3133) bytes
    copying test.xex to test.atr


Creating DOS 3.3 Binaries
~~~~~~~~~~~~~~~~~~~~~~~~~

For this example, the goal is to produce a single binary file that combines a
hi-res image ``title.bin`` loaded at 2000 hex (the first hi-res screen) and
code at 6000 hex from the binary file ``game``, with a start address of 6000
hex.

The binary file ``game`` was assembled using the assembler from the 
`cc65 <https://github.com/cc65/cc65>`_ project, using the command::

    cl65 -t apple2 --cpu 6502 --start-addr 0x6000 -o game game.s

Because the Apple ][ binary format is limited to a single contiguous block of
data with a start address of the first byte of data loaded, ``atrcopy`` will
fill the gaps between any segments that aren't contiguous with zeros. If the
start address is not the first byte of the first specified segment, a small
segment will be included at the beginning that jumps to the specified ``brun``
address (shown here as the segment from 1ffd - 2000). Note the gap between 4000
and 6000 hex will be filled with zeros::

    $ atrcopy game.dsk create dos33autobrun
    using dos33autobrun template:
      Apple ][ DOS 3.3 (140K) disk image for binary program development: HELLO sets
      fullscreen HGR and calls BRUN on user-supplied AUTOBRUN binary file
    created game.dsk: DOS 3.3 Disk Image (size=143360 (560x256b)
    File #0  ( A) 002 HELLO                          003 001

    $ atrcopy game.dsk asm -d title.bin@2000 -b game --brun 6000 -f -o AUTOBRUN
    game.dsk: DOS 3.3 Disk Image (size=143360 (560x256b)
    adding BSAVE data $6000-$6ef3 ($0ef3 @ $0004) from game
    setting data for $1ffd - $2000 at index $0004
    setting data for $2000 - $4000 at index $0007
    setting data for $6000 - $6ef3 at index $4007
    total file size: $4efa (20218) bytes
    copying AUTOBRUN to game.dsk


Example on macOS
----------------

macOS supplies python with the operating system so you shouldn't need to
install a framework version from python.org.

To prevent overwriting important system files, it's best to create a working
folder: a new empty folder somewhere and do all your testing in that folder.
For this example, create a folder called ``atrtest`` in your ``Documents``
folder.  Put a few disk images in this directory to use for testing.

Since this is a command line program, you must get to a command line prompt.
Start a Terminal by double clicking on Terminal.app in the
``Applications/Utilities`` folder in the Finder.  When Terminal opens, it will
put you in your home folder automatically.  Go to the ``atrtest`` folder by
typing::

    cd Documents/atrtest

You can see the ATR images you placed in this directory by using the
command::

    ls -l

For example, you might see::

    mac:~/Documents/atrtest $ ls -l
    -rw-r--r-- 1 rob  staff  92176 May 18 21:57 GAMES1.ATR

Now, run the program by typing ``atrcopy GAMES1.ATR`` and you should
see the contents of the ``ATR`` image in the familiar Atari DOS format::

    mac:~/Documents/atrtest $ atrcopy GAMES1.ATR
    GAMES1.ATR: ATR Disk Image (size=92160 (720x128B), crc=0 flags=0 unused=0) Atari DOS Format: 707 usable sectors (17 free), 9 files
    File #0  (.2.u.*) 004 DOS     SYS  039
    File #1  (.2.u.*) 043 MINER2       138
    File #2  (.2.u.*) 085 DEFENDER     132
    File #3  (.2.u.*) 217 CENTIPEDE    045
    File #4  (.2.u.*) 262 GALAXIAN     066
    File #5  (.2.u.*) 328 AUTORUN SYS  005
    File #6  (.2.u.*) 439 DIGDUG       133
    File #7  (.2.u.*) 531 ANTEATER     066
    File #8  (.2.u.*) 647 ASTEROIDS    066

See other examples as above.


References
==========

* http://www.atariarchives.org/dere/chapt09.php
* http://atari.kensclassics.org/dos.htm
* http://www.crowcastle.net/preston/atari/
* http://www.atarimax.com/jindroush.atari.org/afmtatr.html
* https://archive.org/details/Beneath_Apple_DOS_OCR

Related Atari Projects
----------------------

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
