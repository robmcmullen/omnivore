import bz2
import io

import numpy as np

from .. import errors
from ..compressor import Compressor


class BZipCompressor(Compressor):
    compression_algorithm = "bzip2"

    def calc_unpacked_data(self, byte_data):
        try:
            buf = io.BytesIO(byte_data)
            with bz2.BZ2File(buf, mode='rb') as f:
                unpacked = f.read()
        except OSError as e:
            raise errors.InvalidAlgorithm(e)
        return unpacked

    def calc_packed_data(self, byte_data, media=None):
        buf = io.BytesIO()
        try:
            with bz2.BZ2File(buf, mode='wb') as f:
                f.write(byte_data)
        except OSError as e:
            raise errors.InvalidAlgorithm(e)
        else:
            packed = buf.getvalue()
        return packed
