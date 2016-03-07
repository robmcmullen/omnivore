__version__ = "2.4.0"

try:
    import numpy as np
except ImportError:
    raise RuntimeError("atrcopy %s requires numpy" % __version__)

from errors import *
from ataridos import AtariDosDiskImage, AtariDosFile
from diskimages import AtrHeader, BootDiskImage
from kboot import KBootImage
from segments import SegmentSaver, DefaultSegment, EmptySegment, ObjSegment, RawSectorsSegment, IndexedByteSegment
from spartados import SpartaDosDiskImage
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

    for filename in options.files:
        with open(filename, "rb") as fh:
            data = fh.read()
            image = None
            if options.debug:
                data = to_numpy(data)
                header = AtrHeader(data[0:16])
                image = SpartaDosDiskImage(data, filename)
            else:
                try:
                    data = to_numpy(data)
                    try:
                        header = AtrHeader(data[0:16])
                        for format in [KBootImage, SpartaDosDiskImage, AtariDosDiskImage]:
                            if options.verbose: print "trying", format.__name__
                            try:
                                image = format(data, filename)
                                print "%s: %s" % (filename, image)
                                break
                            except InvalidDiskImage:
                                pass
                    except AtrError:
                        for format in [AtariDosDiskImage]:
                            try:
                                image = format(data)
                                print "%s: %s" % (filename, image)
                                break
                            except:
                                raise
                                #pass
                except AtrError:
                    if options.verbose: print "%s: Doesn't look like a supported disk image" % filename
                    try:
                        image = AtariDosFile(data)
                        print "%s:\n%s" % (filename, image)
                    except InvalidBinaryFile:
                        if options.verbose: print "%s: Doesn't look like an XEX either" % filename
                    continue
                if image is None:
                    image = BootDiskImage(data, filename)
            if options.segments:
                image.parse_segments()
                print "\n".join([str(a) for a in image.segments])
            elif image.files or options.force:
                for dirent in image.files:
                    try:
                        process(image, dirent, options)
                    except FileNumberMismatchError164:
                        print "Error 164: %s" % str(dirent)
                    except ByteNotInFile166:
                        print "Invalid sector for: %s" % str(dirent)

