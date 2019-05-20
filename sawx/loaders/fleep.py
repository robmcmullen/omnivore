import fleep

import logging
log = logging.getLogger(__name__)


def identify_loader(file_guess):
    info = fleep.get(file_guess.sample_data)
    if info.mime:
        if isinstance(info.mime, list):
            log.debug(f"fleep loader: identified multiple mime types {info.mime}; skipping")
            return None
        else:
            log.debug(f"fleep loader: identified {info.mime}")
            return dict(mime=info.mime)
    log.debug(f"fleep loader: unidentified")
    return None
