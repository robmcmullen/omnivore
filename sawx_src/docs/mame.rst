================
MAME ROM Editing
================

Sprite Layout
=============

From Dan Boris, gfx_layout describes the graphics memory structure. Donkey Kong
is a simpler example::

    static const gfx_layout charlayout =
    {
            8,8,    /* 8*8 characters */
            RGN_FRAC(1,2),
            2,      /* 2 bits per pixel */
            { RGN_FRAC(1,2), RGN_FRAC(0,2) },       /* the two bitplanes are separated */
            { 0, 1, 2, 3, 4, 5, 6, 7 },     /* pretty straightforward layout */
            { 0*8, 1*8, 2*8, 3*8, 4*8, 5*8, 6*8, 7*8 },
            8*8     /* every char takes 8 consecutive bytes */
    };

    static const gfx_layout spritelayout =
    {
            16,16,  /* 16*16 sprites */
            RGN_FRAC(1,4),  /* 128 sprites */
            2,      /* 2 bits per pixel */
            { RGN_FRAC(1,2), RGN_FRAC(0,2) },       /* the two bitplanes are separated */
            { 0, 1, 2, 3, 4, 5, 6, 7,       /* the two halves of the sprite are separated */
                            RGN_FRAC(1,4)+0, RGN_FRAC(1,4)+1, RGN_FRAC(1,4)+2, RGN_FRAC(1,4)+3, RGN_FRAC(1,4)+4, RGN_FRAC(1,4)+5, RGN_FRAC(1,4)+6, RGN_FRAC(1,4)+7 },
            { 0*8, 1*8, 2*8, 3*8, 4*8, 5*8, 6*8, 7*8,
                            8*8, 9*8, 10*8, 11*8, 12*8, 13*8, 14*8, 15*8 },
            16*8    /* every sprite takes 16 consecutive bytes */
    };

Here's Flicky, from ``advancemame-1.2/src/drivers/system1.c``::

    static const gfx_layout charlayout =
    {
            8,8,   /* 8 pixels wide, 8 pixels high */
            RGN_FRAC(1,3), /* region fraction / 3 pixels */
            3,  /* 3 bits per pixel */
            { RGN_FRAC(0,3), RGN_FRAC(1,3), RGN_FRAC(2,3) }, /* bitplane locations: starting at 0, 1/3 of the way and 2/3rds of the way through the region */
            { 0, 1, 2, 3, 4, 5, 6, 7 }, /* pixels consecutive across char */
            { 0*8, 1*8, 2*8, 3*8, 4*8, 5*8, 6*8, 7*8 }, /* consecutive order as go down lines */
            8*8 /* each char uses 64 consecutive bits */
    };

    static const gfx_decode gfxdecodeinfo[] =
    {
            /* sprites use colors 0-511, but are not defined here */
            { REGION_GFX1, 0, &charlayout, 512, 128 },
            { -1 } /* end of array */
    };

From Dan Boris's `MAME Driver explanations
<http://www.atarihq.com/danb/files/mamedrv1.txt>`_: I've put comments above
describing the format. They are 8x8 character pixels, 3 bits per pixel with
bitplanes in BSQ order, so one entire bitplane definition before the next
bitplane.



There are two graphics regions. From the listxml for MAME .106, the first is::

    <rom name="epr-5868.62" size="8192" crc="7402256b" sha1="5bd660ac24a2d0d8ad983e948674a82a2d2e8b49" region="gfx1" dispose="yes" offset="0"/>
    <rom name="epr-5867.61" size="8192" crc="2f5ce930" sha1="4bc3bc6eb8f03926d3710c9f96fcc1b116e918d3" region="gfx1" dispose="yes" offset="2000"/>
    <rom name="epr-5866.64" size="8192" crc="967f1d9a" sha1="652be7848526c6e61db4a502f75d1689d2ff2f59" region="gfx1" dispose="yes" offset="4000"/>
    <rom name="epr-5865.63" size="8192" crc="03d9a34c" sha1="e158db3e0b86f2b8ad34cefc2714cb0a942efde7" region="gfx1" dispose="yes" offset="6000"/>
    <rom name="epr-5864.66" size="8192" crc="e659f358" sha1="cf59f1fb0f9fb77d5ac36be52b6ee946ee85d6de" region="gfx1" dispose="yes" offset="8000"/>
    <rom name="epr-5863.65" size="8192" crc="a496ca15" sha1="8c629a853486bbe049b1deecdc00f9e16b87698f" region="gfx1" dispose="yes" offset="a000"/>

and the second is::

    <rom name="epr-5855.117" size="16384" crc="b5f894a1" sha1="2c72dc16739dad155fcd572e1add067a7647f5bd" region="gfx2" offset="0"/>
    <rom name="epr-5856.110" size="16384" crc="266af78f" sha1="dcbfce550d10a1f2b3ce3e7e081fc008cb575708" region="gfx2" offset="4000"/>

`MAMEdb reports similar info <http://mamedb.com/game/flicky>`_, but calls gfx1
`tiles` and gfx2 `sprites`.


Encryption
==========

MAME ROMs can be encrypted, and the encryption scheme predictably got more
complicated as time went on. Flicky uses an XOR scheme but apparently only had
48 keys so it was reverse engineered.

Looking at the AdvanceMAME 1.2 source, Flicky uses the following files::

    drivers/system1.c 
    vidhrdw/system1.c


High Score Files
================

Flicky's high score file with one entry::

    $ hexdump -C hi/flicky.hi 
    00000000  01 36 70 00 10 00 00 09  00 00 08 00 00 07 00 00  |.6p.............|
    00000010  06 00 00 05 00 10 03 03  03 02 02 02 52 4f 42 48  |............ROBH|
    00000020  5c 49 49 43 49 59 5c 4b  4b 54 47 4d 5c 54 53 45  |\IICIY\KKTGM\TSE|
    00000030  20 01 36 70                                       | .6p|
    00000034

I tried moving it over to another computer and it wasn't recognized, so I don't
know what triggers the loading of the files.
