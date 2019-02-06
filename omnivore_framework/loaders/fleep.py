import fleep

import logging
log = logging.getLogger(__name__)


def identify_mime(header):
    info = fleep.get(header)
    if info.mime:
        log.debug(f"fleep loader: identified {info.mime}")
        return dict(mime=info.mime, ext=info.ext)
    log.debug(f"fleep loader: unidentified")
    return None
