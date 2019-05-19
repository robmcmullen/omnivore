import gzip
import io
import tarfile

import numpy as np

from .. import errors
from ..archiver import Archiver

import logging
log = logging.getLogger(__name__)


class TarArchiver(Archiver):
    archive_type = "tar"

    def iter_archive(self, basename, byte_data):
        byte_data = io.BytesIO(byte_data)
        try:
            with tarfile.open(None, "r", byte_data) as zf:
                for item in zf.getmembers():
                    log.debug(f"tarinfo item: {item}")
                    item_data = np.frombuffer(zf.extractfile(item).read(), dtype=np.uint8)
                    yield item.name, item_data
        except:
            raise errors.InvalidArchiver("Not a tar file")
