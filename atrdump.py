#!/usr/bin/env python

from atrutil import *

def process(dirent, options):
    skip = options.dry_run
    why = "Copying"
    filename = dirent.get_filename()
    outfilename = filename
    if options.games:
        if dirent.ext == "SYS":
            skip = True
            why = "System file skipped"
    if not skip:
        if options.xex:
            outfilename = "%s%s.XEX" % (dirent.filename, dirent.ext)
            why = "Copying to %s" % outfilename
        bytes = atr.get_file(dirent)
        with open(outfilename, "wb") as fh:
            fh.write(bytes)
    print "%s: %s" % (filename, why)

if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="Extract images off ATR format disks")
    parser.add_argument("-v", "--verbose", default=0, action="count")
    parser.add_argument("--dry-run", action="store_true", default=False, help="Don't extract, just show what would have been extracted")
    parser.add_argument("-g", "--games", action="store_true", default=False, help="Only extract things that look like games (no DOS or .SYS files)")
    parser.add_argument("-x", "--xex", action="store_true", default=False, help="Add .xex extension")
    options, extra_args = parser.parse_known_args()

    for args in extra_args:
        print args
        with open(args, "rb") as fh:
            atr = AtrDiskImage(fh)
            if options.verbose:
                print atr
            for dirent in atr.files:
                try:
                    process(dirent, options)
                except FileNumberMismatchError164:
                    print "Error 164: %s" % str(dirent)

