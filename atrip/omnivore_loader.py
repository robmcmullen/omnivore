from .collection import Collection
from . import errors

import logging
log = logging.getLogger(__name__)


def identify_loader(file_guess):
    mime_type = None
    try:
        data = file_guess.all_data
    except IOError as e:
        log.debug(f"atrip loader: error reading entire file: {e}")
    else:
        try:
            collection = Collection(file_guess.uri, data)
        except (errors.UnsupportedDiskImage, IOError) as e:
            log.debug(f"error in atrip parser: {e}")
        else:
            log.debug(f"{collection}")

        if collection.mime_type:
            log.debug(f"atrip loader: identified {collection.mime_type}")
            return dict(mime=collection.mime_type, ext="", atrip_collection=collection)
        else:
            log.debug(f"atrip loader: not recognized")
    return None
