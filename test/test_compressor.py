import os

import pytest

import numpy as np

from atrip.compressors import bzip, dcm, gzip, lz4, lzma, unix_compress, zlib

compressors_and_decompressors = [
    bzip.BZipCompressor,
    gzip.GZipCompressor,
    lz4.LZ4Compressor,
    lzma.LZMACompressor,
    zlib.ZLibCompressor,
]

read_only_compressors = [
    dcm.DCMCompressor,
    unix_compress.UnixCompressor,
]

class TestCompressor:
    def setup(self):
        data = np.arange(4096, dtype=np.uint8)
        data[1::2] = np.repeat(np.arange(16, dtype=np.uint8), 128)
        data[::100] = 0x7f
        self.byte_data = data.tobytes()

    @pytest.mark.parametrize("compressor_cls", compressors_and_decompressors)
    def test_compressor(self, compressor_cls):
        compressor = compressor_cls()

        packed = compressor.calc_packed_data(self.byte_data)
        assert packed != self.byte_data
        unpacked = compressor.calc_unpacked_data(packed)

        print(len(self.byte_data), len(packed), len(unpacked))
        assert unpacked == self.byte_data

if __name__ == "__main__":
    t = TestCompressor()
    t.setup()
    t.test_compressor(gzip.GZipCompressor)
    t.test_compressor(bzip.BZipCompressor)
    t.test_compressor(lzma.LZMACompressor)
