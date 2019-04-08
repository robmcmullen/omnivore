import gzip
import io

import numpy as np

from .. import errors
from ..container import Container


class GZipContainer(Container):
    compression_algorithm = "gzip"

    def calc_unpacked_bytes(self, byte_data):
        try:
            buf = io.BytesIO(byte_data)
            with gzip.GzipFile(mode='rb', fileobj=buf) as f:
                unpacked = f.read()
        except OSError as e:
            raise errors.InvalidContainer(e)
        return unpacked
