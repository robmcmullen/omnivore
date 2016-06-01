class AtrError(RuntimeError):
    pass

class InvalidAtrHeader(AtrError):
    pass

class InvalidCartHeader(AtrError):
    pass

class InvalidDiskImage(AtrError):
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
