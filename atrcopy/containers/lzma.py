import lzma
import io

import numpy as np

from .. import errors
from ..container import Container


class LZMAContainer(Container):
    compression_algorithm = "lzma"

    def calc_unpacked_bytes(self, byte_data):
        try:
            buf = io.BytesIO(byte_data)
            with lzma.LZMAFile(buf, mode='rb') as f:
                unpacked = f.read()
        except lzma.LZMAError as e:
            raise errors.InvalidContainer(e)
        return unpacked
