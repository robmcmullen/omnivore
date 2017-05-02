__version__ = "4.0.0"

import os
import sys

import logging
log = logging.getLogger(__name__)

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
        output = dirent.filename
        if options.lower:
            output = output.lower()
        if not options.dry_run:
            data = image.get_file(dirent)
            if os.path.exists(output) and not options.force:
                print "skipping %s, file exists. Use -f to overwrite" % output
                continue
            print "extracting %s -> %s" % (name, output)
            with open(output, "wb") as fh:
                fh.write(data)
        else:
            print "extracting %s -> %s" % (name, output)


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


def assemble(image, source_files, data_files, run_addr=""):
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
        log.debug("Assembled %s into:" % name)
        for first, last, object_code in asm.segments:
            s = segments.add_segment(object_code, first)
            log.debug("  %s" % s.name)
    for name in data_files:
        if "@" not in name:
            raise AtrError("Data files must include a load address specified with the @ char")
        name, addr = name.rsplit("@", 1)
        first = text_to_int(addr)
        log.debug("Adding data file %s at $%04x" % (name, first))
        subset = slice(0, sys.maxint)
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
            log.debug("read data for %s" % s.name)
    if options.verbose:
        for s in segments:
            print "%s - %04x)" % (str(s)[:-1], s.start_addr + len(s))
    if run_addr:
        try:
            run_addr = text_to_int(run_addr)
        except ValueError:
            run_addr = None

    file_data, filetype = image.create_executable_file_image(segments, run_addr)
    changed = save_file(image, options.output, filetype, file_data)
    if changed:
        image.save()


def shred_image(image, value=0):
    print "shredding: free sectors from %s filled with %d" % (image, value)
    if not options.dry_run:
        image.shred()
        image.save()



def run():
    import argparse

    global options

    # Subparser command aliasing from: https://gist.github.com/sampsyo/471779
    # released into the public domain by its author
    class AliasedSubParsersAction(argparse._SubParsersAction):
        class _AliasedPseudoAction(argparse.Action):
            def __init__(self, name, aliases, help):
                dest = name
                if aliases:
                    dest += ' (%s)' % ','.join(aliases)
                sup = super(AliasedSubParsersAction._AliasedPseudoAction, self)
                sup.__init__(option_strings=[], dest=dest, help=help) 

        def add_parser(self, name, **kwargs):
            if 'aliases' in kwargs:
                aliases = kwargs['aliases']
                del kwargs['aliases']
            else:
                aliases = []

            parser = super(AliasedSubParsersAction, self).add_parser(name, **kwargs)

            # Make the aliases work.
            for alias in aliases:
                self._name_parser_map[alias] = parser
            # Make the help text reflect them, first removing old help entry.
            if 'help' in kwargs:
                help = kwargs.pop('help')
                self._choices_actions.pop()
                pseudo_action = self._AliasedPseudoAction(name, aliases, help)
                self._choices_actions.append(pseudo_action)

            return parser

    command_aliases = {
        "list": ["t", "ls", "dir", "catalog"],
        "extract": ["x"],
        "add": ["a"],
        "create": ["c"],
        "assemble": ["s", "asm"],
        "delete": ["rm", "del"],
        "vtoc": ["v"],
        "segments": [],
    }
    reverse_aliases = {z: k for k, v in command_aliases.iteritems() for z in v}
    usage = "%(prog)s [-h] [-v] [--dry-run] DISK_IMAGE [...]"
    subparser_usage = "%(prog)s [-h] [-v] [--dry-run] DISK_IMAGE"

    parser = argparse.ArgumentParser(prog="atrcopy DISK_IMAGE", description="Manipulate files on several types of 8-bit computer disk images. Type '%(prog)s COMMAND --help' for list of options available for each command.")
    parser.register('action', 'parsers', AliasedSubParsersAction)
    parser.add_argument("-v", "--verbose", default=0, action="count")
    parser.add_argument("--dry-run", action="store_true", default=False, help="don't perform operation, just show what would have happened")

    subparsers = parser.add_subparsers(dest='command', help='', metavar="COMMAND")

    command = "list"
    list_parser = subparsers.add_parser(command, help="List files on the disk image. This is the default if no command is specified", aliases=command_aliases[command])
    list_parser.add_argument("-g", "--segments", action="store_true", default=False, help="display segments")
    list_parser.add_argument("-m", "--metadata", action="store_true", default=False, help="show extra metadata for named files")
    list_parser.add_argument("files", metavar="FILENAME", nargs="*", help="an optional list of files to display")

    command = "extract"
    extract_parser = subparsers.add_parser(command, help="Copy files from the disk image to the local filesystem", aliases=command_aliases[command])
    extract_parser.add_argument("-a", "--all", action="store_true", default=False, help="operate on all files on disk image")
    extract_parser.add_argument("-l", "--lower", action="store_true", default=False, help="convert extracted filenames to lower case")
    #extract_parser.add_argument("-n", "--no-sys", action="store_true", default=False, help="only extract things that look like games (no DOS or .SYS files)")
    extract_parser.add_argument("-e", "--ext", action="store", nargs=1, default=False, help="add the specified extension")
    extract_parser.add_argument("-f", "--force", action="store_true", default=False, help="allow file overwrites on local filesystem")
    extract_parser.add_argument("files", metavar="FILENAME", nargs="*", help="if not using the -a/--all option, a file (or list of files) to extract from the disk image.")

    command = "add"
    add_parser = subparsers.add_parser(command, help="Add files to the disk image", aliases=command_aliases[command])
    add_parser.add_argument("-f", "--force", action="store_true", default=False, help="allow file overwrites in the disk image")
    add_parser.add_argument("-t", "--filetype", action="store", default="", help="file type metadata for writing to disk images that require it (e.g. DOS 3.3)")
    add_parser.add_argument("files", metavar="FILENAME", nargs="+", help="a file (or list of files) to copy to the disk image")

    # command = "create"
    # create_parser = subparsers.add_parser(command, help="Create a new disk image", aliases=command_aliases[command])
    # create_parser.add_argument("-f", "--force", action="store_true", default=False, help="replace disk image file if it exists")
    # create_parser.add_argument("-s", "--sys", action="store_true", default=False, help="include system files (e.g. DOS.SYS and DUP.SYS for Atari DOS 2")
    # create_parser.add_argument("-2", "--dos2", default="dos2", const="dos2", dest="image_type", action="store_const", help="blank Atari DOS 2")
    # create_parser.add_argument("-33", "--dos33", default="dos2", const="dos33", dest="image_type", action="store_const", help="blank Apple DOS 3.3")

    command = "assemble"
    assembly_parser = subparsers.add_parser(command, help="Create a new binary file in the disk image", aliases=command_aliases[command])
    assembly_parser.add_argument("-f", "--force", action="store_true", default=False, help="allow file overwrites in the disk image")
    assembly_parser.add_argument("-s", "--asm", nargs="*", action="append", help="source file(s) to assemble using pyatasm")
    assembly_parser.add_argument("-d","-b", "--data", nargs="*", action="append", help="binary data file(s) to add to assembly, specify as file@addr. Only a portion of the file may be included; specify the subset using standard python slice notation: file[subset]@addr")
    assembly_parser.add_argument("-r", "--run-addr", "--brun", action="store", default="", help="run address of binary file if not the first byte of the first segment")
    assembly_parser.add_argument("-o", "--output", action="store", default="", required=True, help="output file name in disk image")

    command = "delete"
    delete_parser = subparsers.add_parser(command, help="Delete files from the disk image", aliases=command_aliases[command])
    delete_parser.add_argument("-f", "--force", action="store_true", default=False, help="remove the file even if it is write protected ('locked' in Atari DOS 2 terms), if write-protect is supported disk image")
    delete_parser.add_argument("files", metavar="FILENAME", nargs="+", help="a file (or list of files) to remove from the disk image")

    command = "vtoc"
    vtoc_parser = subparsers.add_parser(command, help="Show a formatted display of sectors free in the disk image", aliases=command_aliases[command])
    vtoc_parser.add_argument("-e", "--clear-empty", action="store_true", default=False, help="fill empty sectors with 0")

    command = "segments"
    vtoc_parser = subparsers.add_parser(command, help="Show the list of parsed segments in the disk image", aliases=command_aliases[command])


    # argparse doesn't seem to allow an argument fixed to item 1, so have to
    # hack with the arg list to get arg #1 to be the disk image. Because of
    # this hack, we have to perform an additional hack to figure out what the
    # --help option applies to if it's in the argument list.
    args = list(sys.argv[1:])
    if len(args) > 0:
        found_help = -1
        first_non_dash = 0
        num_non_dash = 0
        for i in range(len(args)):
            if args[i].startswith("-"):
                if i == 0:
                    first_non_dash = -1
                if args[i] =="-h" or args[i] == "--help":
                    found_help = i
            else:
                num_non_dash += 1
                if first_non_dash < 0:
                    first_non_dash = i
        if found_help >= 0 or first_non_dash < 0:
            if found_help == 0 or first_non_dash < 0:
                # put dummy argument so help for entire script will be shown
                args = ["--help"]
            elif args[first_non_dash] in command_aliases or args[first_non_dash] in reverse_aliases:
                # if the first argument without a leading dash looks like a
                # command instead of a disk image, show help for that command
                args = [args[first_non_dash], "--help"]
            else:
                # show script help
                args = ["--help"]
        else:
            # allow global options to come before or after disk image name
            disk_image_name = args[first_non_dash]
            args[first_non_dash:first_non_dash + 1] = []
            if num_non_dash == 1:
                # If there is only a disk image but no command specified, use
                # the default
                args.append('list')
    else:
        disk_image_name = None

    # print "parsing: %s" % str(args)
    options = parser.parse_args(args)
    # print options
    command = reverse_aliases.get(options.command, options.command)

    # Turn off debug messages by default
    logging.basicConfig(level=logging.WARNING)
    log = logging.getLogger("atrcopy")
    if options.verbose:
        log.setLevel(logging.DEBUG)
    else:
        log.setLevel(logging.INFO)

    if command == "create":
        pass
    else:
        parser = find_diskimage(disk_image_name)
        if parser and parser.image:
            if command == "vtoc":
                vtoc = parser.image.get_vtoc_object()
                print vtoc
                if options.clear_empty:
                    shred_image(parser.image)
            elif command == "list":
                list_files(parser.image, options.files)
            elif command == "add":
                add_files(parser.image, options.files)
            elif command == "delete":
                remove_files(parser.image, options.files)
            elif command == "extract":
                extract_files(parser.image, options.files)
            elif command == "assemble":
                asm = options.asm[0] if options.asm else []
                data = options.data[0] if options.data else []
                assemble(parser.image, asm, data, options.run_addr)
            elif command == "segments":
                print "\n".join([str(a) for a in parser.segments])
        else:
            log.error("Invalid disk image: %s" % disk_image_name)
