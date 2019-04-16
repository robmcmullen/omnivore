import os
import sys
import time
import zipfile

from datetime import datetime
import wx

from .filesystem import fsopen as open
from .filesystem import filesystem_path
from .utils.textutil import guessBinary

import logging
log = logging.getLogger(__name__)


def get_loaders():
    import pkg_resources

    loaders = []
    for entry_point in pkg_resources.iter_entry_points('sawx.loaders'):
        try:
            mod = entry_point.load()
        except Exception as e:
            log.error(f"Failed importing loader {entry_point.name}: {e}")
            import traceback
            traceback.print_exc()
        else:
            log.debug(f"get_loaders: Found loader {entry_point.name}")
            loaders.append(mod)
    return loaders


class FileGuess:
    def __init__(self, uri):
        self.uri = uri
        self.fh = open(uri, 'rb')
        self._sample_data = None
        self._sample_lines = None
        self._all_data = None
        self._is_binary = None
        self._is_zipfile = None
        self._zipfile = None
        self._filesystem_path = None

    @property
    def sample_data(self):
        if self._sample_data is None:
            self._sample_data = self.fh.read(10240)
        return self._sample_data

    @property
    def sample_lines(self):
        if self._sample_lines is None:
            self._sample_lines = self.sample_data.splitlines()
        return self._sample_lines

    @property
    def all_data(self):
        if self._all_data is None:
            self.fh.seek(0)
            self._all_data = self.fh.read()
        return self._all_data

    @property
    def is_binary(self):
        if self._is_binary is None:
            self._is_binary = guessBinary(self.sample_data)
        return self._is_binary

    @property
    def is_text(self):
        return not self.is_binary

    @property
    def is_zipfile(self):
        if self._is_zipfile is None:
            self.fh.seek(0)
            self._is_zipfile = zipfile.is_zipfile(self.fh)
        return self._is_zipfile

    @property
    def zipfile(self):
        if self._zipfile is None:
            self.fh.seek(0)
            self._zipfile = zipfile.ZipFile(self.fh)
        return self._zipfile

    @property
    def filesystem_path(self):
        if self._filesystem_path is None:
            self._filesystem_path = filesystem_path(self.uri)  # may raise OSError
        return self._filesystem_path

    def zipfile_contains(self, filename):
        if not self.is_zipfile:
            return False
        try:
            info = self.zipfile.getinfo(filename)
            print(f"ZIPFILE INFO FOR {filename}: {info}")
        except KeyError:
            return False
        return True

    def zipfile_contains_extension(self, ext):
        if not self.is_zipfile:
            return False
        for item in self.zipfile.infolist():
            if item.filename.endswith(ext):
                return True
        return True


def identify_file(uri, match_multiple=False):
    """Examine the file to determine MIME type and other salient info to
    allow the loader to chose an editor with which to open the file

    Returns a dict containing (at least) the keys:

    * uri -- the uri of the file
    * mime  -- the text string identifying the MIME type

    and possibly other keys that may be used by specific loaders for specific
    types of data.
    """
    loaders = get_loaders()
    log.debug(f"identify_file: identifying file {uri} using {loaders}")
    hits = []
    fallback = None
    file_guess = FileGuess(uri)
    for loader in loaders:
        log.debug(f"identify_file: trying loader {loader}")
        try:
            loader.identify_loader
        except AttributeError:
            log.warning(f"identify_file: attempting to call identify_mime from {loader} with old style parameters")
            file_metadata = loader.identify_mime(file_guess.sample_data, file_guess.fh)
        else:
            file_metadata = loader.identify_loader(file_guess)
        if file_metadata:
            file_metadata['uri'] = uri
            mime_type = file_metadata['mime']
            if mime_type == "application/octet-stream" or mime_type == "text/plain":
                log.debug(f"identify_file: identified as generic type {mime_type}")
                if not fallback:
                    fallback = mime_type
            else:
                log.debug(f"identify_file: identified: {file_metadata}")
                if not match_multiple:
                    return file_metadata
                hits.append(file_metadata)

    # how to find best guess?
    if hits:
        log.debug(f"identify_file: found {hits}")
        return hits[0]
    else:
        if not fallback:
            fallback = "application/octet-stream"
        log.debug(f"identify_file: identified only as the generic {fallback}")
        return dict(mime=fallback, uri=uri)
