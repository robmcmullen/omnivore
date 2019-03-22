import os
import sys
import time

from datetime import datetime
import wx

from .filesystem import fsopen as open

import logging
log = logging.getLogger(__name__)


def get_loaders():
    import pkg_resources

    loaders = []
    for entry_point in pkg_resources.iter_entry_points('sawx.loaders'):
        try:
            mod = entry_point.load()
        except (ModuleNotFoundError, ImportError) as e:
            log.error(f"Failed using loader {entry_point.name}: {e}")
            import traceback
            traceback.print_exc()
        else:
            log.debug(f"get_loaders: Found loader {entry_point.name}")
            loaders.append(mod)
    return loaders

def identify_file(uri):
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
    with open(uri, 'rb') as fh:
        sample_data = fh.read(10240)
        for loader in loaders:
            log.debug(f"identify_file: trying loader {loader}")
            try:
                file_metadata = loader.identify_mime(uri, fh, sample_data)
            except TypeError:
                log.warning(f"identify_file: attempting to call identify_mime from {loader} with old style parameters")
                file_metadata = loader.identify_mime(sample_data, fh)
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
        return dict(mime=fallback, uri=uri)
