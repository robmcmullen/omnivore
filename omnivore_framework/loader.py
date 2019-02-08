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
        mod = entry_point.load()
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
    log.debug(f"identifying files using {loaders}")
    hits = []
    fallback = None
    with open(uri, 'rb') as fh:
        data = fh.read(10240)
        for loader in loaders:
            log.debug(f"trying loader {loader}")
            mime_info = loader.identify_mime(data)
            if mime_info:
                mime_type = mime_info['mime']
                if mime_type == "application/octet-stream" or mime_type == "text/plain":
                    if not fallback:
                        fallback = mime_type
                else:
                    log.debug(f"found mime: {mime_info}")
                    hits.append(mime_info)

    # how to find best guess?
    if hits:
        log.debug(f"identify_file: best guess = {mime_info}")
        return hits[0]
    else:
        if not fallback:
            fallback = "application/octet-stream"
        log.debug(f"identify_file: identified only as the generic {fallback}")
        return dict(mime=fallback, ext="")
