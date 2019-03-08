from . import find_diskimage_from_data, errors

import logging
log = logging.getLogger(__name__)


def identify_mime(header, fh):
    mime_type = None
    try:
        fh.seek(0)
        data = fh.read()
    except IOError as e:
        log.debug(f"atrcopy loader: error reading entire file: {e}")
    else:
        try:
            parser, mime_type = find_diskimage_from_data(data, True)
        except (errors.UnsupportedContainer, errors.UnsupportedDiskImage, IOError) as e:
            log.debug(f"error in atrcopy parser: {e}")
        else:
            log.debug(f"{parser.image}: {mime_type}")

        if mime_type:
            log.debug(f"atrcopy loader: identified {mime_type}")
            return dict(mime=mime_type, ext="", atrcopy_parser=parser)
        else:
            log.debug(f"atrcopy loader: not recognized")
    return None
