__version__ = "4.0.0"

import logging

try:
    import numpy as np
except ImportError:
    raise RuntimeError("atrcopy %s requires numpy" % __version__)

from errors import *
from ataridos import AtrHeader, AtariDosDiskImage, BootDiskImage, AtariDosFile, XexContainerSegment, get_xex, add_atr_header
from dos33 import Dos33DiskImage
from kboot import KBootImage, add_xexboot_header
from segments import SegmentData, SegmentSaver, DefaultSegment, EmptySegment, ObjSegment, RawSectorsSegment, SegmentedFileSegment, user_bit_mask, match_bit_mask, comment_bit_mask, data_style, selected_bit_mask, diff_bit_mask, not_user_bit_mask, interleave_segments, SegmentList, get_style_mask, get_style_bits
from spartados import SpartaDosDiskImage
from cartridge import A8CartHeader, AtariCartImage
from parsers import SegmentParser, DefaultSegmentParser, guess_parser_for_mime, guess_parser_for_system, iter_parsers, iter_known_segment_parsers, mime_parse_order
from utils import to_numpy, text_to_int


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


def find_diskimage(filename):
    try:
        with open(filename, "rb") as fh:
            if options.verbose:
                print "Loading file %s" % filename
            rawdata = SegmentData(fh.read())
            parser = None
            for mime in mime_parse_order:
                if options.verbose:
                    print "Trying MIME type %s" % mime
                parser = guess_parser_for_mime(mime, rawdata, options.verbose)
                if parser is None:
                    continue
                if options.verbose:
                    print "Found parser %s" % parser.menu_name
                print "%s: %s" % (filename, parser.image)
                break
            if parser is None:
                print "%s: Unknown disk image type" % filename
    except UnsupportedDiskImage, e:
        print "%s: %s" % (filename, e)
        return None
    else:
        parser.image.filename = filename
        parser.image.ext = ""
        return parser


def extract_files(image, files):
    for name in files:
        try:
            dirent = image.find_dirent(name)
        except FileNotFound:
            print "%s not in %s" % (name, image)
            continue
        print "extracting %s" % name
        if not options.dry_run:
            data = image.get_file(dirent)
            with open(dirent.filename, "wb") as fh:
                fh.write(data)


def save_file(image, name, filetype, data):
    try:
        dirent = image.find_dirent(name)
        if options.force:
            image.delete_file(name)
        else:
            print "skipping %s, use -f to overwrite" % (name)
            return False
    except FileNotFound:
        pass
    print "copying %s to %s" % (name, image)
    if not options.dry_run:
        image.write_file(name, filetype, data)
        return True
    return False


def add_files(image, files):
    filetype = options.filetype
    if not filetype:
        filetype = image.default_filetype
    changed = False
    for name in files:
        with open(name, "rb") as fh:
            data = fh.read()
        changed = save_file(image, name, filetype, data)
    if changed:
        image.save()


def remove_files(image, files):
    changed = False
    for name in files:
        try:
            dirent = image.find_dirent(name)
        except FileNotFound:
            print "%s not in %s" % (name, image)
            continue
        print "removing %s from %s" % (name, image)
        if not options.dry_run:
            image.delete_file(name)
            changed = True
    if changed:
        image.save()


def list_files(image, files):
    files = set(files)
    for dirent in image.files:
        if not files or dirent.filename in files:
            print dirent
            if options.metadata:
                print dirent.extra_metadata(image)


def assemble(image, source_files, data_files):
    if source_files:
        try:
            import pyatasm
        except ImportError:
            raise AtrError("Please install pyatasm to compile code.")
    changed = False
    segments = SegmentList()
    for name in source_files:
        try:
            asm = pyatasm.Assemble(name)
        except SyntaxError, e:
            raise AtrError("Assembly error: %s" % e.msg)
        for first, last, object_code in asm.segments:
            s = segments.add_segment(object_code, first)
            print s.name
    for name in data_files:
        if "@" not in name:
            raise AtrError("Data files must include a load address specified with the @ char")
        name, addr = name.rsplit("@", 1)
        first = text_to_int(addr)
        subset = slice(0, -1)
        if "[" in name and "]" in name:
            name, slicetext = name.rsplit("[", 1)
            if ":" in slicetext:
                start, end = slicetext.split(":", 1)
                try:
                    start = int(start)
                except:
                    start = 0
                if end.endswith("]"):
                    end = end[:-1]
                try:
                    end = int(end)
                except:
                    end = None
                subset = slice(start, end)
        with open(name, 'rb') as fh:
            data = fh.read()[subset]
            s = segments.add_segment(data, first)
            print s.name
    if options.verbose:
        for s in segments:
            print "%s - %04x)" % (str(s)[:-1], s.start_addr + len(s))
    file_data, filetype = image.create_executable_file_image(segments)
    changed = save_file(image, options.output, filetype, file_data)
    if changed:
        image.save()


def shred_image(image, value=0):
    print "shredding: free sectors from %s filled with %d" % (image, value)
    if not options.dry_run:
        image.shred()
        image.save()


def run():
    import sys
    import argparse

    global options

    parser = argparse.ArgumentParser(description="Manipulate files on several types of 8-bit computer disk images")
    parser.add_argument("-v", "--verbose", default=0, action="count")
    parser.add_argument("--dry-run", action="store_true", default=False, help="don't perform operation, just show what would have happened")

    parser.add_argument("-x", "-e", "--extract", action="store_true", default=False, help="extract named files")
    parser.add_argument("-a", "--add", action="store_true", default=False, help="add files to image")
    parser.add_argument("-d", "--delete", action="store_true", default=False, help="remove named files from image")
    parser.add_argument("-t", "--filetype", action="store", default="", help="file type metadata for writing to disk images that require it")
    parser.add_argument("-s", "--asm", nargs="+", action="append", help="source file(s) to assemble using pyatasm (requires -o to specify filename stored on disk image)")
    parser.add_argument("-b", "--bytes", nargs="+", action="append", help="data file(s) to add to assembly, specify as file@addr (requires -o to specify filename stored on disk image)")
    parser.add_argument("-o", "--output", action="store", default="", help="output file name for those commands that need it")
    parser.add_argument("-f", "--force", action="store_true", default=False, help="force operation, allowing file overwrites or attempt operation on non-standard disk images")
    parser.add_argument("--all", action="store_true", default=False, help="operate on all files on disk image")

    parser.add_argument("-l", "--lower", action="store_true", default=False, help="convert extracted filenames to lower case")
    parser.add_argument("-n", "--no-sys", action="store_true", default=False, help="only extract things that look like games (no DOS or .SYS files)")
    parser.add_argument("--xex", action="store_true", default=False, help="add .xex extension")
    parser.add_argument("-g", "--segments", action="store_true", default=False, help="display segments")
    parser.add_argument("--shred", action="store_true", default=False, help="fill empty sectors with 0")
    parser.add_argument("--vtoc", action="store_true", default=False, help="show the VTOC")
    parser.add_argument("-m", "--metadata", action="store_true", default=False, help="show extra metadata for named files")
    parser.add_argument("files", metavar="IMAGE", nargs="+", help="a disk image file [or a list of them]")
    options, extra_args = parser.parse_known_args()

    # Turn off debug messages by default
    logging.basicConfig(level=logging.WARNING)
    log = logging.getLogger("atrcopy")
    if options.verbose:
        log.setLevel(logging.DEBUG)
    else:
        log.setLevel(logging.INFO)

    file_list = []
    if options.add or options.extract or options.delete:
        image = options.files.pop()
        file_list = options.files
        options.files = [image]

    if options.all and file_list:
            raise AtrError("Specifying a list of files and --all doesn't make sense.")

    image_files = []
    for filename in options.files:
        if filename == "-":
            import fileinput

            for line in fileinput.input(["-"]):
                line = line.rstrip()
                print "-->%s<--" % line
                image_files.append(line)
        else:
            image_files.append(filename)

    for filename in image_files:
        parser = find_diskimage(filename)
        if parser and parser.image:
            if options.all:
                file_list = list(parser.image.files)

            if options.segments:
                print "\n".join([str(a) for a in parser.segments])
            elif options.add:
                add_files(parser.image, file_list)
            elif options.extract:
                extract_files(parser.image, file_list)
            elif options.delete:
                remove_files(parser.image, file_list)
            elif options.asm or options.bytes:
                asm = options.asm[0] if options.asm else []
                datafiles = options.bytes[0] if options.bytes else []
                assemble(parser.image, asm, datafiles)
            else:
                list_files(parser.image, file_list)

            if options.shred:
                shred_image(parser.image)

            if options.vtoc:
                vtoc = parser.image.get_vtoc_object()
                print vtoc
