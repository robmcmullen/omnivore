class AtrError(RuntimeError):
    pass


class InvalidAtrHeader(AtrError):
    pass


class InvalidCartHeader(AtrError):
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


class InvalidDirent(AtrError):
    pass


class LastDirent(AtrError):
    pass


class InvalidFile(AtrError):
    pass


class FileNumberMismatchError164(InvalidFile):
    pass


class ByteNotInFile166(InvalidFile):
    pass


class InvalidBinaryFile(InvalidFile):
    pass


class InvalidSegmentParser(AtrError):
    pass


class NoSpaceInDirectory(AtrError):
    pass


class NotEnoughSpaceOnDisk(AtrError):
    pass


class FileNotFound(AtrError):
    pass


class UnsupportedContainer(AtrError):
    pass


class InvalidContainer(AtrError):
    pass
