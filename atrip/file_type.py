import hashlib
import inspect
import pkg_resources

import numpy as np

from . import errors
from . import style_bits
from .segment import Segment
from .utils import to_numpy, to_numpy_list, uuid
from . import filesystem

import logging
log = logging.getLogger(__name__)


class FileType(Segment):
    """Base class for a file contained in a filesystem.
    """
    ui_name = "Unknown file type"

    extra_serializable_attributes = []

    def __init__(self, media, name, offset, length=0):
        self.media = media
        Segment.__init__(self, media, offset, name=name, length=length)
        self.segments = self.calc_segments()
        self.style_segments()

    def __str__(self):
        s = Segment.__str__(self) + " " + self.ui_name
        return s

    def calc_segments(self):
        """Calculate the segments composing this file, or raise a FileError if
        the segment is incompatible with the file structure represented by this
        class.
        """
        return []

    def style_segments(self):
        """Add styling info to segments.

        This happens only after the successful completion of calc_segments. If
        styling were done in calc_segments, FileTypes that were attempted but
        raised errors would add styling info that would be invalid for the
        file type eventually determined to be correct.
        """
        pass


ignore_base_class_file_types = set([FileType])

_file_types = None

def _find_file_types():
    file_types = []
    for entry_point in pkg_resources.iter_entry_points('atrip.file_types'):
        mod = entry_point.load()
        log.debug(f"find_file_type: Found module {entry_point.name}={mod.__name__}")
        for name, obj in inspect.getmembers(mod):
            if inspect.isclass(obj) and FileType in obj.__mro__[1:] and obj not in ignore_base_class_file_types:
                log.debug(f"find_file_types:   found file_type class {name}")
                file_types.append(obj)
    return file_types

def find_file_types():
    global _file_types

    if _file_types is None:
        _file_types = _find_file_types()
    return _file_types

def guess_file_type(media, filename, offset, length=0):
    for m in find_file_types():
        log.debug(f"trying file_type {m.ui_name}")
        try:
            found = m(media, filename, offset, length)
        except errors.FileError as e:
            log.debug(f"found error: {e}")
            continue
        else:
            log.info(f"found file_type {m.ui_name} for {filename}")
            return found
    log.info(f"No recognized file type for {filename}")
    return FileType(media, filename, offset, length)
