import gzip
import io
import zipfile

import numpy as np

from .. import errors
from ..archiver import Archiver

import logging
log = logging.getLogger(__name__)


class ZipArchiver(Archiver):
    archive_type = "zip"

    def iter_archive(self, basename, byte_data):
        byte_data = io.BytesIO(byte_data)
        try:
            with zipfile.ZipFile(byte_data) as zf:
                for item in zf.infolist():
                    log.debug(f"zipinfo item: {item}")
                    item_data = np.frombuffer(zf.open(item).read(), dtype=np.uint8)
                    yield item.filename, item_data
        except:
            raise errors.InvalidArchiver("Not a zip file")
