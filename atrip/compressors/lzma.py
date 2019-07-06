import lzma
import io

import numpy as np

from .. import errors
from ..compressor import Compressor


class LZMACompressor(Compressor):
    compression_algorithm = "lzma"

    def calc_unpacked_data(self, byte_data):
        try:
            buf = io.BytesIO(byte_data)
            with lzma.LZMAFile(buf, mode='rb') as f:
                unpacked = f.read()
        except lzma.LZMAError as e:
            raise errors.InvalidAlgorithm(e)
        if len(unpacked) == 0:
            raise errors.InvalidAlgorithm("Unpacked to zero size")
        return unpacked

    def calc_packed_data(self, byte_data, media=None):
        buf = io.BytesIO()
        try:
            with lzma.LZMAFile(buf, mode='wb') as f:
                f.write(byte_data)
        except OSError as e:
            raise errors.InvalidAlgorithm(e)
        else:
            packed = buf.getvalue()
        return packed
