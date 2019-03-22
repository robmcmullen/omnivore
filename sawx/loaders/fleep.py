import fleep

import logging
log = logging.getLogger(__name__)


def identify_mime(uri, fh, header):
    info = fleep.get(header)
    if info.mime:
        log.debug(f"fleep loader: identified {info.mime}")
        return dict(mime=info.mime)
    log.debug(f"fleep loader: unidentified")
    return None
