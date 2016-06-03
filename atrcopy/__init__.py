__version__ = "3.0.1"

import logging

try:
    import numpy as np
except ImportError:
    raise RuntimeError("atrcopy %s requires numpy" % __version__)

from errors import *
from ataridos import AtariDosDiskImage, AtariDosFile, get_xex
from diskimages import AtrHeader, BootDiskImage, add_atr_header
from kboot import KBootImage, add_xexboot_header
from segments import SegmentData, SegmentSaver, DefaultSegment, EmptySegment, ObjSegment, RawSectorsSegment, user_bit_mask, match_bit_mask, comment_bit_mask, data_bit_mask, selected_bit_mask, diff_bit_mask, not_user_bit_mask, interleave_segments
from spartados import SpartaDosDiskImage
from cartridge import A8CartHeader, AtariCartImage
from parsers import SegmentParser, DefaultSegmentParser, guess_parser_for_mime, guess_parser_for_system, iter_parsers, iter_known_segment_parsers, mime_parse_order
from utils import to_numpy


def process(image, dirent, options):
    skip = False
    action = "copying to"
    filename = dirent.get_filename()
    outfilename = filename
    if options.no_sys:
        if dirent.ext == "SYS":
            skip = True
            action = "skipping system file"
    if not skip:
        if options.xex:
            outfilename = "%s%s.XEX" % (dirent.filename, dirent.ext)
    if options.lower:
        outfilename = outfilename.lower()
    
    if options.dry_run:
        action = "DRY_RUN: %s" % action
        skip = True
    if options.extract:
        print "%s: %s %s" % (dirent, action, outfilename)
        if not skip:
            bytes = image.get_file(dirent)
            with open(outfilename, "wb") as fh:
                fh.write(bytes)
    else:
        print dirent

def run():
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="Extract images off ATR format disks")
    parser.add_argument("-v", "--verbose", default=0, action="count")
    parser.add_argument("-d", "--debug", action="store_true", default=False, help="debug the currently under-development parser")
    parser.add_argument("-l", "--lower", action="store_true", default=False, help="convert filenames to lower case")
    parser.add_argument("--dry-run", action="store_true", default=False, help="don't extract, just show what would have been extracted")
    parser.add_argument("-n", "--no-sys", action="store_true", default=False, help="only extract things that look like games (no DOS or .SYS files)")
    parser.add_argument("-x", "--extract", action="store_true", default=False, help="extract files")
    parser.add_argument("--xex", action="store_true", default=False, help="add .xex extension")
    parser.add_argument("-f", "--force", action="store_true", default=False, help="force operation on disk images that have bad directory entries or look like boot disks")
    parser.add_argument("files", metavar="ATR", nargs="+", help="an ATR image file [or a list of them]")
    parser.add_argument("-s", "--segments", action="store_true", default=False, help="display segments")
    options, extra_args = parser.parse_known_args()

    # Turn off debug messages by default
    log = logging.getLogger("atrcopy")
    if options.verbose:
        log.setLevel(logging.DEBUG)
    else:
        log.setLevel(logging.INFO)
    
    for filename in options.files:
        with open(filename, "rb") as fh:
            if options.verbose:
                print "Loading file %s" % filename
            rawdata = SegmentData(fh.read())
            parser = None
            for mime in mime_parse_order:
                if options.verbose:
                    print "Trying MIME type %s" % mime
                parser = guess_parser_for_mime(mime, rawdata)
                if parser is None:
                    continue
                if options.verbose:
                    print "Found parser %s" % parser.menu_name
                print "%s: %s" % (filename, parser.image)
                if options.segments:
                    print "\n".join([str(a) for a in parser.segments])
                elif parser.image.files or options.force:
                    for dirent in parser.image.files:
                        try:
                            process(parser.image, dirent, options)
                        except FileNumberMismatchError164:
                            print "Error 164: %s" % str(dirent)
                        except ByteNotInFile166:
                            print "Invalid sector for: %s" % str(dirent)
                break
            if parser is None:
                print "%s: Unknown file type" % filename
