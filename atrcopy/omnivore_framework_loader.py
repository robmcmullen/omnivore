from . import find_diskimage_from_data, errors

import logging
log = logging.getLogger(__name__)


def identify_mime(header):
    mime_type = None
    try:
        parser, mime_type = find_diskimage_from_data(header, True)
    except (errors.UnsupportedContainer, errors.UnsupportedDiskImage, IOError) as e:
        print(f"error in atrcopy parser: {e}")
    else:
        print(f"{parser.image}: {mime_type}")
 
    if mime_type:
        log.debug(f"atrcopy loader: identified {mime_type}")
        return dict(mime=mime_type, ext="")
    else:
        log.debug(f"atrcopy loader: unidentified")
        return None
