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

Here's Flicky::

    static const gfx_layout charlayout =
    {
            8,8,
            RGN_FRAC(1,3),
            3,
            { RGN_FRAC(0,3), RGN_FRAC(1,3), RGN_FRAC(2,3) },
            { 0, 1, 2, 3, 4, 5, 6, 7 },
            { 0*8, 1*8, 2*8, 3*8, 4*8, 5*8, 6*8, 7*8 },
            8*8
    };

    static const gfx_decode gfxdecodeinfo[] =
    {
            /* sprites use colors 0-511, but are not defined here */
            { REGION_GFX1, 0, &charlayout, 512, 128 },
            { -1 } /* end of array */
    };



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
