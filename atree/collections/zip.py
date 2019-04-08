import gzip
import io
import zipfile

import numpy as np

from .. import errors
from ..collection import Collection

import logging
log = logging.getLogger(__name__)


class ZipCollection(Collection):
    archive_type = "zip archive"

    def iter_archive(self, byte_data):
        byte_data = io.BytesIO(byte_data)
        try:
            with zipfile.ZipFile(byte_data) as zf:
                for item in zf.infolist():
                    log.debug(f"zipinfo item: {item}")
                    item_data = np.frombuffer(zf.open(item).read(), dtype=np.uint8)
                    yield item_data
        except:
            raise errors.InvalidCollection("Not a zip file")
