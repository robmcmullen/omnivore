atrcopy
=======

Utilities to list files on and extract files from Atari 8-bit emulator disk
images.  Eventually, I hope to add support for these images to pyfilesystem.

Prerequisites
-------------

Starting with atrcopy 2.0, numpy is required.

The standard python install tool, pip, does not seem to be able to handle the
automatic installation of numpy, so to install atrcopy, use::

    pip install numpy
    pip install atrcopy


References
==========

* http://www.atariarchives.org/dere/chapt09.php
* http://atari.kensclassics.org/dos.htm
* http://www.crowcastle.net/preston/atari/
* http://www.atarimax.com/jindroush.atari.org/afmtatr.html


Supported Disk Image Formats
============================

* ``XFD``: XFormer images, basically raw disk dumps
* ``ATR``: Nick Kennedy's disk image format; includes 16 byte header

Supported Filesystem Formats
----------------------------

* XEX format: Atari executable files
* Atari DOS in single, enhanced, and double density
* KBoot format: a single executable file packaged up into a bootable disk image

Other Supported Formats
-----------------------

* Atari ROM cartridges (both plain binary and Atari800 .CAR format)
* MAME ROM zipfiles


Example Usage
=============

To extract all non SYS files while converting to lower case, use::

    $ python atrcopy.py /tmp/GAMES1.ATR -x -l -n
    GAMES1.ATR
    File #0 : *DOS     SYS  039 : skipping system file dos.sys
    File #1 : *MINER2       138 : copying to miner2
    File #2 : *DEFENDER     132 : copying to defender
    File #3 : *CENTIPEDE    045 : copying to centiped.e
    File #4 : *GALAXIAN     066 : copying to galaxian
    File #5 : *AUTORUN SYS  005 : skipping system file autorun.sys
    File #6 : *DIGDUG       133 : copying to digdug
    File #7 : *ANTEATER     066 : copying to anteater
    File #8 : *ASTEROIDS    066 : copying to asteroid.s


Example on Mac OS X
-------------------

OS X supplies python with the operating system so you shouldn't need to install
a framework version from python.org.

To prevent overwriting important system files, it's best to create a working
folder: a new empty folder somewhere and do all your testing in that folder.
For this example, create a folder called ``atrtest`` in your ``Documents``
folder.  Put a few disk images in this directory to use for testing.

Download or copy the file ``atrcopy.py`` and put it the ``Documents/atrtest``
folder.

Since this is a command line programe, you must start a Terminal by double
clicking on Terminal.app in the ``Applications/Utilities`` folder in
the Finder.  When Terminal opens, it will put you in your home folder
automatically.  Go to the ``atrtest`` folder by typing::

    cd Documents/atrtest

You should see the file ``atrcopy.py`` as well as the other ATR images you
placed in this directory by using the command::

    ls -l

For example, you might see::

    mac:~/Documents/atrtest $ ls -l
    -rw-r--r-- 1 rob  staff  92176 May 18 21:57 GAMES1.ATR
    -rwxr-xr-x 1 rob  staff   8154 May 18 22:36 atrcopy.py

Now, run the program by typing ``python atrcopy.py YOURFILE.ATR`` and you should
see the contents of the ``ATR`` image in the familiar Atari DOS format::

    mac:~/Documents/atrtest $ python atrcopy.py GAMES1.ATR
    GAMES1.ATR
    File #0 : *DOS     SYS  039 
    File #1 : *MINER2       138 
    File #2 : *DEFENDER     132 
    File #3 : *CENTIPEDE    045 
    File #4 : *GALAXIAN     066 
    File #5 : *AUTORUN SYS  005 
    File #6 : *DIGDUG       133 
    File #7 : *ANTEATER     066 
    File #8 : *ASTEROIDS    066 

Without any additional arguments, it will not extract files.  To actually pull
the files out of the ``ATR`` image, you need to specify the ``-x`` command line
argument::

    mac:~/Documents/atrtest $ python atrcopy.py -x GAMES1.ATR
    GAMES1.ATR
    File #0 : *DOS     SYS  039 : copying to DOS.SYS
    File #1 : *MINER2       138 : copying to MINER2
    File #2 : *DEFENDER     132 : copying to DEFENDER
    File #3 : *CENTIPEDE    045 : copying to CENTIPED.E
    File #4 : *GALAXIAN     066 : copying to GALAXIAN
    File #5 : *AUTORUN SYS  005 : copying to AUTORUN.SYS
    File #6 : *DIGDUG       133 : copying to DIGDUG
    File #7 : *ANTEATER     066 : copying to ANTEATER
    File #8 : *ASTEROIDS    066 : copying to ASTEROID.S

There are other flags, like the ``-l`` flag to covert to lower case, and the
``--xex`` flag to add the `.XEX` extension to the filename, and ``-n`` to skip
DOS files.  So a full example might be::

    mac:~/Documents/atrtest $ python atrcopy.py -n -l -x --xex GAMES1.ATR
    GAMES1.ATR
    File #0 : *DOS     SYS  039 : skipping system file dos.sys
    File #1 : *MINER2       138 : copying to miner2.xex
    File #2 : *DEFENDER     132 : copying to defender.xex
    File #3 : *CENTIPEDE    045 : copying to centipede.xex
    File #4 : *GALAXIAN     066 : copying to galaxian.xex
    File #5 : *AUTORUN SYS  005 : skipping system file autorun.sys
    File #6 : *DIGDUG       133 : copying to digdug.xex
    File #7 : *ANTEATER     066 : copying to anteater.xex
    File #8 : *ASTEROIDS    066 : copying to asteroids.xex


Command Line Arguments
----------------------

The available command line arguments are summarized using the standard ``--
help`` argument::

    $ python atrcopy.py --help
    usage: atrcopy.py [-h] [-v] [-l] [--dry-run] [-n] [-x] [--xex] ATR [ATR ...]

    Extract images off ATR or XFD format disks

    positional arguments:
      ATR            a disk image file [or a list of them]

    optional arguments:
      -h, --help     show this help message and exit
      -v, --verbose
      -l, --lower    convert filenames to lower case
      --dry-run      don't extract, just show what would have been extracted
      -n, --no-sys   only extract things that look like games (no DOS or .SYS
                     files)
      -x, --extract  extract files
      --xex          add .xex extension
      -f, --force    force operation on disk images that have bad directory
                     entries or look like boot disks
