import os
import sys
import zlib
import json

import logging
log = logging.getLogger(__name__)

from ._metadata import __version__

try:
    import numpy as np
except ImportError:
    raise RuntimeError("atrcopy %s requires numpy" % __version__)

from . import errors
from .ataridos import AtrHeader, AtariDosDiskImage, BootDiskImage, AtariDosFile, XexContainerSegment, get_xex, add_atr_header
from .dos33 import Dos33DiskImage
from .kboot import KBootImage, add_xexboot_header
from .segments import SegmentData, SegmentSaver, DefaultSegment, EmptySegment, ObjSegment, RawSectorsSegment, SegmentedFileSegment, user_bit_mask, match_bit_mask, comment_bit_mask, data_style, selected_bit_mask, diff_bit_mask, not_user_bit_mask, interleave_segments, SegmentList, get_style_mask, get_style_bits
from .spartados import SpartaDosDiskImage
from .cartridge import A8CartHeader, AtariCartImage
from .parsers import SegmentParser, DefaultSegmentParser, guess_parser_for_mime, guess_parser_for_system, guess_container, iter_parsers, iter_known_segment_parsers, mime_parse_order, parsers_for_filename
from .magic import guess_detail_for_mime
from .utils import to_numpy, text_to_int
from .dummy import LocalFilesystem


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
        print("%s: %s %s" % (dirent, action, outfilename))
        if not skip:
            bytes = image.get_file(dirent)
            with open(outfilename, "wb") as fh:
                fh.write(bytes)
    else:
        print(dirent)


def find_diskimage(filename):
    if filename == ".":
        parser = LocalFilesystem()
    else:
        with open(filename, "rb") as fh:
            if options.verbose:
                print("Loading file %s" % filename)
            data = to_numpy(fh.read())
        parser = None
        container = guess_container(data, options.verbose)
        if container is not None:
            data = container.unpacked
        rawdata = SegmentData(data)
        for mime in mime_parse_order:
            if options.verbose:
                print("Trying MIME type %s" % mime)
            parser = guess_parser_for_mime(mime, rawdata, options.verbose)
            if parser is None:
                continue
            if options.verbose:
                print("Found parser %s" % parser.menu_name)
            mime2 = guess_detail_for_mime(mime, rawdata, parser)
            if mime != mime2 and options.verbose:
                print("Signature match: %s" % mime2)
            break
    if parser is None:
        raise errors.UnsupportedDiskImage("Unknown disk image type")
    else:
        parser.image.filename = filename
        parser.image.ext = ""
        return parser


def extract_files(image, files):
    if options.all:
        files = image.files
    for name in files:
        try:
            dirent = image.find_dirent(name)
        except errors.FileNotFound:
            print("%s not in %s" % (name, image))
            continue
        output = dirent.filename
        if options.lower:
            output = output.lower()
        if not options.dry_run:
            data = image.get_file(dirent)
            if os.path.exists(output) and not options.force:
                print("skipping %s, file exists. Use -f to overwrite" % output)
                continue
            print("extracting %s -> %s" % (name, output))
            with open(output, "wb") as fh:
                fh.write(data)
        else:
            print("extracting %s -> %s" % (name, output))


def save_file(image, name, filetype, data):
    try:
        dirent = image.find_dirent(name)
        if options.force:
            image.delete_file(name)
        else:
            print("skipping %s, use -f to overwrite" % (name))
            return False
    except errors.FileNotFound:
        pass
    print("copying %s to %s" % (name, image.filename))
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
        except errors.FileNotFound:
            print("%s not in %s" % (name, image))
            continue
        print("removing %s from %s" % (name, image))
        if not options.dry_run:
            image.delete_file(name)
            changed = True
    if changed:
        image.save()


def list_files(image, files, show_crc=False, show_metadata=False):
    files = set(files)
    for dirent in image.files:
        if not files or dirent.filename in files:
            if show_crc:
                data = image.get_file(dirent)
                crc = zlib.crc32(data) & 0xffffffff  # correct for some platforms that return signed int
                extra = "  %08x" % crc
            else:
                extra = ""
            print("%s%s" % (dirent, extra))
            if show_metadata:
                print(dirent.extra_metadata(image))


def crc_files(image, files):
    files = set(files)
    for dirent in image.files:
        if not files or dirent.filename in files:
            data = image.get_file(dirent)
            crc = zlib.crc32(data) & 0xffffffff  # correct for some platforms that return signed int
            print("%s: %08x" % (dirent.filename, crc))


def assemble_segments(source_files, data_files, obj_files, run_addr=""):
    if source_files:
        try:
            import pyatasm
        except ImportError:
            raise errors.AtrError("Please install pyatasm to compile code.")
    changed = False
    segments = SegmentList()
    for name in source_files:
        try:
            asm = pyatasm.Assemble(name)
        except SyntaxError as e:
            raise errors.AtrError("Assembly error: %s" % e.msg)
        log.debug("Assembled %s into:" % name)
        for first, last, object_code in asm.segments:
            s = segments.add_segment(object_code, first)
            log.debug("  %s" % s.name)
            print("adding %s from %s assembly" % (s, name))
    for name in data_files:
        if "@" not in name:
            raise errors.AtrError("Data files must include a load address specified with the @ char")
        name, addr = name.rsplit("@", 1)
        first = text_to_int(addr)
        log.debug("Adding data file %s at $%04x" % (name, first))
        subset = slice(0, sys.maxsize)
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
    for name in obj_files:
        try:
            parser = find_diskimage(name)
        except errors.AtrError as e:
            print(f"skipping {name}: {e}")
        else:
            for s in parser.segments:
                if hasattr(s, 'run_address'):
                    if not run_addr:
                        run_addr = s.run_address()
                    else:
                        print(f"already have run address {run_addr}; skipping {s.run_address()}")
                elif s.origin > 0:
                    print(f"adding {s} from {name}")
                    segments.add_segment(s.data, s.origin)
    if options.verbose:
        for s in segments:
            print("%s - %04x)" % (str(s)[:-1], s.origin + len(s)))
    if run_addr:
        try:
            run_addr = text_to_int(run_addr)
        except (AttributeError, ValueError):
            # not text, try as integer
            try:
                run_addr = int(run_addr)
            except ValueError:
                run_addr = None

    return segments, run_addr

def assemble(image, source_files, data_files, obj_files, run_addr=""):
    segments, run_addr = assemble_segments(source_files, data_files, obj_files, run_addr)
    file_data, filetype = image.create_executable_file_image(options.output, segments, run_addr)
    print("total file size: $%x (%d) bytes" % (len(file_data), len(file_data)))
    changed = save_file(image, options.output, filetype, file_data)
    if changed:
        image.save()


def boot_image(image_name, source_files, data_files, obj_files, run_addr=""):
    try:
        image_cls = parsers_for_filename(image_name)[0]
    except errors.InvalidDiskImage as e:
        print("%s: %s" % (image_name, e))
        return None
    segments, run_addr = assemble_segments(source_files, data_files, obj_files, run_addr)
    if segments:
        image = image_cls.create_boot_image(segments, run_addr)
        print("saving boot disk %s" % (image_name))
        image.save(image_name)
    else:
        print("No segments to save to boot disk")


def shred_image(image, value=0):
    print("shredding: free sectors from %s filled with %d" % (image, value))
    if not options.dry_run:
        image.shred()
        image.save()


def get_template_path(rel_path="templates"):
    path = __file__

    template_path = os.path.normpath(os.path.join(os.path.dirname(path), rel_path))
    frozen = getattr(sys, 'frozen', False)
    if frozen:
        if frozen == True:
            # pyinstaller sets frozen=True and uses sys._MEIPASS
            root = sys._MEIPASS
            template_path = os.path.normpath(os.path.join(root, template_path))
        elif frozen  == 'macosx_app':
            #print "FROZEN!!! %s" % frozen
            root = os.environ['RESOURCEPATH']
            if ".zip/" in template_path:
                zippath, template_path = template_path.split(".zip/")
            template_path = os.path.normpath(os.path.join(root, template_path))
        else:
            print("App packager %s not yet supported for image paths!!!")
    return template_path


def get_template_images(partial=""):
    import glob

    path = get_template_path()
    files = glob.glob(os.path.join(path, "*"))
    templates = {}
    for path in files:
        name = os.path.basename(path)
        if name.endswith(".inf"):
            continue
        if partial not in name:
            continue
        try:
            with open(path + ".inf", "r") as fh:
                s = fh.read()
                try:
                    j = json.loads(s)
                except ValueError:
                    continue
                j['name'] = name
                j['path'] = path
                templates[name] = j
        except IOError:
            continue
    return templates


def get_template_info():
    import textwrap
    fmt = "  %-14s  %s"

    templates = get_template_images()

    lines = []
    lines.append("available templates:")
    for name in sorted(templates.keys()):
        d = textwrap.wrap(templates[name]["description"], 80 - 1 - 14 - 2 - 2)
        lines.append(fmt % (os.path.basename(name), d[0]))
        lines.extend([fmt % ("", line) for line in d[1:]])
    return os.linesep.join(lines) + os.linesep


def get_template_data(template):
    possibilities = get_template_images(template)
    if not possibilities:
        raise errors.InvalidDiskImage("Unknown template disk image %s" % template)
    if len(possibilities) > 1:
        raise errors.InvalidDiskImage("Name %s is ambiguous (%d matches: %s)" % (template, len(possibilities), ", ".join(sorted(possibilities.keys()))))
    name, inf = possibilities.popitem()
    path = inf['path']
    try:
        with open(path, "rb") as fh:
            data = fh.read()
    except IOError:
        raise errors.InvalidDiskImage("Failed reading template file %s" % path)
    return data, inf


def create_image(template, name):
    import textwrap

    try:
        data, inf = get_template_data(template)
    except errors.InvalidDiskImage as e:
        info = get_template_info()
        print("Error: %s\n\n%s" % (e, info))
        return
    print("Using template %s:\n  %s" % (inf['name'], "\n  ".join(textwrap.wrap(inf["description"], 77))))
    if not options.dry_run:
        if os.path.exists(name) and not options.force:
            print("skipping %s, use -f to overwrite" % (name))
        else:
            with open(name, "wb") as fh:
                fh.write(data)
            parser = find_diskimage(name)
            print("created %s: %s" % (name, str(parser.image)))
            list_files(parser.image, [])
    else:
        print("creating %s" % name)


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
        "crc": [],
        "extract": ["x"],
        "add": ["a"],
        "create": ["c"],
        "boot": ["b"],
        "assemble": ["s", "asm"],
        "delete": ["rm", "del"],
        "vtoc": ["v"],
        "segments": [],
    }
    # reverse aliases does the inverse mapping of command aliases, including
    # the identity mapping of "command" to "command"
    reverse_aliases = {z: k for k, v in command_aliases.items() for z in (v + [k])}

    skip_diskimage_summary = set(["crc"])

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
    list_parser.add_argument("-c", "--crc", action="store_true", default=False, help="compute CRC32 for each file")
    list_parser.add_argument("files", metavar="FILENAME", nargs="*", help="an optional list of files to display")

    command = "crc"
    crc_parser = subparsers.add_parser(command, help="List files on the disk image and the CRC32 value in format suitable for parsing", aliases=command_aliases[command])
    crc_parser.add_argument("files", metavar="FILENAME", nargs="*", help="an optional list of files to display")

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

    command = "create"
    create_parser = subparsers.add_parser(command, help="Create a new disk image", aliases=command_aliases[command], epilog="<generated on demand to list available templates>", formatter_class=argparse.RawDescriptionHelpFormatter)
    create_parser.add_argument("-f", "--force", action="store_true", default=False, help="replace disk image file if it exists")
    create_parser.add_argument("template", metavar="TEMPLATE", nargs=1, help="template to use to create new disk image; see below for list of available built-in templates")

    command = "assemble"
    assembly_parser = subparsers.add_parser(command, help="Create a new binary file in the disk image", aliases=command_aliases[command])
    assembly_parser.add_argument("-f", "--force", action="store_true", default=False, help="allow file overwrites in the disk image")
    assembly_parser.add_argument("-s", "--asm", nargs="*", action="append", help="source file(s) to assemble using pyatasm")
    assembly_parser.add_argument("-d","--data", nargs="*", action="append", help="binary data file(s) to add to assembly, specify as file@addr. Only a portion of the file may be included; specify the subset using standard python slice notation: file[subset]@addr")
    assembly_parser.add_argument("-b", "--obj", "--bload", nargs="*", action="append", help="binary file(s) to add to assembly, either executables or labeled memory dumps (e.g. BSAVE on Apple ][), parsing each file's binary segments to add to the resulting disk image at the load address for each segment")
    assembly_parser.add_argument("-r", "--run-addr", "--brun", action="store", default="", help="run address of binary file if not the first byte of the first segment")
    assembly_parser.add_argument("-o", "--output", action="store", default="", required=True, help="output file name in disk image")

    command = "boot"
    boot_parser = subparsers.add_parser(command, help="Create a bootable disk image", aliases=command_aliases[command])
    boot_parser.add_argument("-f", "--force", action="store_true", default=False, help="allow file overwrites in the disk image")
    boot_parser.add_argument("-s", "--asm", nargs="*", action="append", help="source file(s) to assemble using pyatasm")
    boot_parser.add_argument("-d","--data", nargs="*", action="append", help="binary data file(s) to add to assembly, specify as file@addr. Only a portion of the file may be included; specify the subset using standard python slice notation: file[subset]@addr")
    boot_parser.add_argument("-b", "--obj", "--bload", nargs="*", action="append", help="binary file(s) to add to assembly, either executables or labeled memory dumps (e.g. BSAVE on Apple ][), parsing each file's binary segments to add to the resulting disk image at the load address for each segment")
    boot_parser.add_argument("-r", "--run-addr", "--brun", action="store", default="", help="run address of binary file if not the first byte of the first segment")

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
        non_dash = []
        for i, arg in enumerate(args):
            if arg.startswith("-"):
                if i == 0:
                    first_non_dash = -1
                if arg =="-h" or arg == "--help":
                    found_help = i
            else:
                num_non_dash += 1
                non_dash.append(arg)
                if first_non_dash < 0:
                    first_non_dash = i
        if found_help >= 0 or first_non_dash < 0:
            if found_help == 0 or first_non_dash < 0:
                # put dummy argument so help for entire script will be shown
                args = ["--help"]
            elif non_dash[0] in reverse_aliases:
                # if the first argument without a leading dash looks like a
                # command instead of a disk image, show help for that command
                args = [non_dash[0], "--help"]
            elif len(non_dash) > 0 and non_dash[1] in reverse_aliases:
                # if the first argument without a leading dash looks like a
                # command instead of a disk image, show help for that command
                args = [non_dash[1], "--help"]
            else:
                # show script help
                args = ["--help"]
            if reverse_aliases.get(args[0], None) == "create":
                create_parser.epilog = get_template_info()
        else:
            # Allow global options to come before or after disk image name
            disk_image_name = args[first_non_dash]
            args[first_non_dash:first_non_dash + 1] = []
            if num_non_dash == 1:
                # If there is only a disk image but no command specified,
                # use the default
                args.append('list')
    else:
        disk_image_name = None
        parser.print_help()
        sys.exit(1)

    # print "parsing: %s" % str(args)
    options = parser.parse_args(args)
    # print options
    command = reverse_aliases[options.command]

    # Turn off debug messages by default
    logging.basicConfig(level=logging.WARNING)
    log = logging.getLogger("atrcopy")
    if options.verbose:
        log.setLevel(logging.DEBUG)
    else:
        log.setLevel(logging.INFO)

    if command == "create":
        create_image(options.template[0], disk_image_name)
    elif command == "boot":
        asm = options.asm[0] if options.asm else []
        data = options.data[0] if options.data else []
        obj = options.obj[0] if options.obj else []
        boot_image(disk_image_name, asm, data, obj, options.run_addr)
    else:
        try:
            parser = find_diskimage(disk_image_name)
        except (errors.UnsupportedContainer, errors.UnsupportedDiskImage, IOError) as e:
            print(f"{disk_image_name}: {e}")
        else:
            if command not in skip_diskimage_summary:
                print("%s: %s" % (disk_image_name, parser.image))
            if command == "vtoc":
                vtoc = parser.image.get_vtoc_object()
                print(vtoc)
                if options.clear_empty:
                    shred_image(parser.image)
            elif command == "list":
                list_files(parser.image, options.files, options.crc, options.metadata)
            elif command == "crc":
                crc_files(parser.image, options.files)
            elif command == "add":
                add_files(parser.image, options.files)
            elif command == "delete":
                remove_files(parser.image, options.files)
            elif command == "extract":
                extract_files(parser.image, options.files)
            elif command == "assemble":
                asm = options.asm[0] if options.asm else []
                data = options.data[0] if options.data else []
                obj = options.obj[0] if options.obj else []
                assemble(parser.image, asm, data, obj, options.run_addr)
            elif command == "segments":
                print("\n".join([str(a) for a in parser.segments]))
