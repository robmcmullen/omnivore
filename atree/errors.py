class AtrError(RuntimeError):
    pass


class InvalidSegmentLength(AtrError):
    pass


class InvalidSegmentOrder(AtrError):
    pass


class InvalidDiskImage(AtrError):
    """ Disk image is not recognized by a parser.

    Usually a signal to try the next parser; this error doesn't propagate out
    to the user much.
    """
    pass


class UnsupportedDiskImage(AtrError):
    """ Disk image is recognized by a parser but it isn't supported yet.

    This error does propagate out to the user.
    """
    pass


class InvalidSegmentParser(AtrError):
    pass


class UnsupportedContainer(AtrError):
    pass


class ReadOnlyContainer(AtrError):
    pass


class InvalidContainer(AtrError):
    pass

# Errors when trying to determine media type

class MediaError(AtrError):
    pass


class InvalidMediaSize(MediaError):
    pass


class InvalidHeader(MediaError):
    pass


class InvalidSectorNumber(MediaError):
    pass


# Errors when trying to determine filesystem

class FilesystemError(AtrError):
    pass


class IncompatibleMediaError(FilesystemError):
    pass


class InvalidDirent(FilesystemError):
    pass


class LastDirent(FilesystemError):
    pass


class NoSpaceInDirectory(FilesystemError):
    pass


class NotEnoughSpaceOnDisk(FilesystemError):
    pass


class FileNotFound(FilesystemError):
    pass


# Errors in files or structure of a file

class FileError(FilesystemError):
    pass


class FileStructureError(FilesystemError):
    pass


class FileNumberMismatchError164(FileError):
    pass


class ByteNotInFile166(FileError):
    pass


class InvalidBinaryFile(FileError):
    pass
