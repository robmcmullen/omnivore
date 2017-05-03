atrcopy
=======

Command line utility to manage file systems on Atari 8-bit and Apple ][ disk
images.

Prerequisites
-------------

Starting with atrcopy 2.0, numpy is required. It will be automatically
installed when installing atrcopy with::

    pip install atrcopy


Features
========

* list contents of disk images
* copy files to and from disk images
* delete files from disk images
* create new disk images
* compile assembly source into binary files if `pyatasm <https://pypi.python.org/pypi/pyatasm>`_ is installed


Supported Formats
=================

Supported Disk Image Types
--------------------------

* ``XFD``: XFormer images, basically raw disk dumps
* ``ATR``: Nick Kennedy's disk image format; includes 16 byte header
* ``DSK``: Apple ][ DOS 3.3 disk image; raw sector dump

Supported File System Formats
----------------------------

+--------------+-------------+---------+-------+-------------------+
| File System  | Platform    | Read    | Write | Status            |
+==============+=============+=========+=======+===================+
| DOS 2 (90K)  | Atari 8-bit | Yes     | Yes   | Fully supported   |
+--------------+-------------+---------+-------+-------------------+
| DOS 2 (180K) | Atari 8-bit | Yes     | Yes   | Fully supported   |
+--------------+-------------+---------+-------+-------------------+
| DOS 3 (130K) | Atari 8-bit | Yes     | Yes   | Fully supported   |
+--------------+-------------+---------+-------+-------------------+
| SpartaDOS    | Atari 8-bit | No      | No    | Under development |
+--------------+-------------+---------+-------+-------------------+
| MyDOS        | Atari 8-bit | Partial | No    | Under development |
+--------------+-------------+---------+-------+-------------------+
| DOS 3.3      | Apple ][    | Yes     | Yes   | Fully supported   |
+--------------+-------------+---------+-------+-------------------+
| ProDOS 8     | Apple ][    | No      | No    | Unimplemented     |
+--------------+-------------+---------+-------+-------------------+


Other Supported Formats
-----------------------

* XEX format: Atari executable files
* KBoot format: a single executable file packaged up into a bootable disk image
* Atari ROM cartridges (both plain binary and Atari800 .CAR format)
* MAME ROM zipfiles


Example Usage
=============

Basic usage is::

    atrcopy DISK_IMAGE <global options> COMMAND <command options>

where the available commands include:

* ``list``: list files on the disk image. This is the default if no command is specified
* ``create``: create a new disk image
* ``add``: add files to a disk image
* ``extract``: copy files from the disk image to the local file system
* ``assemble``: create a binary file from ATasm source, optionally including segments containing raw binary data
* ``delete``: delete files from the disk image
* ``vtoc``: show and manipulate the VTOC for images that support it

The ``DISK_IMAGE`` is always required which points to the path on your local
file system of the disk image.  ``COMMAND`` is one of the commands listed
above, and the commands may be abbreviated as shown here::

    $ atrcopy --help
    usage: atrcopy DISK_IMAGE [-h] [-v] [--dry-run] COMMAND ...

    Manipulate files on several types of 8-bit computer disk images. Type 'atrcopy
    DISK_IMAGE COMMAND --help' for list of options available for each command.

    positional arguments:
      COMMAND
        list (t,ls,dir,catalog)
                            List files on the disk image. This is the default if
                            no command is specified
        extract (x)         Copy files from the disk image to the local filesystem
        add (a)             Add files to the disk image
        assemble (s,asm)    Create a new binary file in the disk image
        delete (rm,del)     Delete files from the disk image
        vtoc (v)            Show a formatted display of sectors free in the disk
                            image
        segments            Show the list of parsed segments in the disk image

    optional arguments:
      -h, --help            show this help message and exit
      -v, --verbose
      --dry-run             don't perform operation, just show what would have
                            happened


Help for available options for each command is available using::

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
    DOS_25.ATR: ATR Disk Image (size=133120 (1040x128b), crc=0 flags=0 unused=0) Atari DOS Format: 1010 usable sectors (739 free), 6 files
    File #0  (.2.u.*) 004 DOS     SYS  037
    File #1  (.2.u.*) 041 DUP     SYS  042
    File #2  (.2.u.*) 083 RAMDISK COM  009
    File #3  (.2.u.*) 092 SETUP   COM  070
    File #4  (.2.u.*) 162 COPY32  COM  056
    File #5  (.2.u.*) 218 DISKFIX COM  057

Extract a file::

    $ atrcopy DOS_25.ATR extract SETUP.COM
    DOS_25.ATR: ATR Disk Image (size=133120 (1040x128b), crc=0 flags=0 unused=0) Atari DOS Format: 1010 usable sectors (739 free), 6 files
    extracting SETUP.COM -> SETUP.COM

Extract all files::

    $ atrcopy DOS_25.ATR extract --all
    DOS_25.ATR: ATR Disk Image (size=133120 (1040x128b), crc=0 flags=0 unused=0) Atari DOS Format: 1010 usable sectors (739 free), 6 files
    extracting File #0  (.2.u.*) 004 DOS     SYS  037 -> DOS.SYS
    extracting File #1  (.2.u.*) 041 DUP     SYS  042 -> DUP.SYS
    extracting File #2  (.2.u.*) 083 RAMDISK COM  009 -> RAMDISK.COM
    extracting File #3  (.2.u.*) 092 SETUP   COM  070 -> SETUP.COM
    extracting File #4  (.2.u.*) 162 COPY32  COM  056 -> COPY32.COM
    extracting File #5  (.2.u.*) 218 DISKFIX COM  057 -> DISKFIX.COM

Extract all, renaming to lower case on the host file system::

    $ atrcopy DOS_25.ATR extract --all -l
    DOS_25.ATR: ATR Disk Image (size=133120 (1040x128b), crc=0 flags=0 unused=0) Atari DOS Format: 1010 usable sectors (739 free), 6 files
    extracting File #0  (.2.u.*) 004 DOS     SYS  037 -> dos.sys
    extracting File #1  (.2.u.*) 041 DUP     SYS  042 -> dup.sys
    extracting File #2  (.2.u.*) 083 RAMDISK COM  009 -> ramdisk.com
    extracting File #3  (.2.u.*) 092 SETUP   COM  070 -> setup.com
    extracting File #4  (.2.u.*) 162 COPY32  COM  056 -> copy32.com
    extracting File #5  (.2.u.*) 218 DISKFIX COM  057 -> diskfix.com

Example on Mac OS X
-------------------

OS X supplies python with the operating system so you shouldn't need to install
a framework version from python.org.

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
    GAMES1.ATR: ATR Disk Image (size=92160 (720x128b), crc=0 flags=0 unused=0) Atari DOS Format: 707 usable sectors (17 free), 9 files
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
