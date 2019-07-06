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


class InvalidSegment(AtrError):
    pass


class ReadOnlyContainer(AtrError):
    pass


# Errors for compressors and other translators

class AlgorithmError(AtrError):
    pass

class UnsupportedAlgorithm(AlgorithmError):
    pass

class InvalidAlgorithm(AlgorithmError):
    pass


# Errors for archivers

class ArchiverError(AtrError):
    pass

class InvalidArchiver(ArchiverError):
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


class UnsupportedSectorType(MediaError):
    pass


# Errors when trying to determine filesystem. Raising one of these errors
# during filesystem detection will abort the process and report failure for
# that filesystem.

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


# Errors in files or structure of a file. These are separate from
# FilesystemError subclasses to indicate they aren't fatal when detecting
# filesystems

class FileError(AtrError):
    pass


class FileStructureError(FileError):
    pass


class FileNumberMismatchError164(FileError):
    pass


class ByteNotInFile166(FileError):
    pass


class InvalidBinaryFile(FileError):
    pass
