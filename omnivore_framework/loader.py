import os
import sys
import time

from datetime import datetime
import fs
import wx

from .utils.sortutil import before_after_wildcard_sort
from .filesystem import fsopen as open

import logging
log = logging.getLogger(__name__)


def get_loaders():
    import pkg_resources

    loaders = []
    for entry_point in pkg_resources.iter_entry_points('omnivore_framework.loaders'):
        try:
            mod = entry_point.load()
        except (ModuleNotFoundError, ImportError) as e:
            log.error(f"Failed using loader {entry_point.name}: {e}")
        else:
            log.debug(f"get_loaders: Found loader {entry_point.name}")
            loaders.append(mod)
    return loaders

def identify_file(uri):
    """Examine the file to determine MIME type and other salient info to
    allow the loader to chose an editor with which to open the file

    Returns a dict containing keys mime, ext, and possibly other keys
    that may be used by specific loaders for specific types of data.
    """
    loaders = get_loaders()
    log.debug(f"identify_file: identifying files using {loaders}")
    hits = []
    fallback = None
    with open(uri, 'rb') as fh:
        data = fh.read(10240)
        for loader in loaders:
            log.debug(f"identify_file: trying loader {loader}")
            file_metadata = loader.identify_mime(data, fh)
            if file_metadata:
                file_metadata['uri'] = uri
                mime_type = file_metadata['mime']
                if mime_type == "application/octet-stream" or mime_type == "text/plain":
                    if not fallback:
                        fallback = mime_type
                else:
                    log.debug(f"identify_file: identified: {file_metadata}")
                    hits.append(file_metadata)

    # how to find best guess?
    if hits:
        log.debug(f"identify_file: found {hits}")
        return hits[0]
    else:
        if not fallback:
            fallback = "application/octet-stream"
        log.debug(f"identify_file: identified only as the generic {fallback}")
        return dict(mime=fallback, ext="")
