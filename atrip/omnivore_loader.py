from . import find_diskimage_from_data, errors

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
            parser, mime_type = find_diskimage_from_data(data, True)
        except (errors.UnsupportedContainer, errors.UnsupportedDiskImage, IOError) as e:
            log.debug(f"error in atrip parser: {e}")
        else:
            log.debug(f"{parser.image}: {mime_type}")

        if mime_type:
            log.debug(f"atrip loader: identified {mime_type}")
            return dict(mime=mime_type, ext="", atrip_parser=parser)
        else:
            log.debug(f"atrip loader: not recognized")
    return None
