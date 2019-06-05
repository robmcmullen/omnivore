import gzip
import io

import numpy as np

from .. import errors
from ..compressor import Compressor


class GZipCompressor(Compressor):
    compression_algorithm = "gzip"

    def calc_unpacked_data(self, byte_data):
        try:
            buf = io.BytesIO(byte_data)
            with gzip.GzipFile(mode='rb', fileobj=buf) as f:
                unpacked = f.read()
        except OSError as e:
            raise errors.InvalidAlgorithm(e)
        return unpacked

    def calc_packed_data(self, byte_data, media=None):
        buf = io.BytesIO()
        try:
            with gzip.GzipFile(mode='wb', fileobj=buf) as f:
                f.write(byte_data)
        except OSError as e:
            raise errors.InvalidAlgorithm(e)
        else:
            packed = buf.getvalue()
        return packed
