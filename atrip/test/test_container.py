import glob

import numpy as np

from mock import *

from atrip.container import guess_container
from atrip import errors


read_only_compressors = set(['.Z'])


class BaseContainerTest:
    base_path = None
    expected_mime = ""

    @pytest.mark.parametrize(("ext", "mod_name"), [
        ('', 'none'),
        ('.gz', 'gzip'),
        ('.bz2', 'bzip2'),
        ('.xz', 'lzma'),
        ('.lz4', 'lz4'),
        ('.Z', 'unix compress'),
        ('.dcm', 'dcm'),
    ])
    def test_container(self, ext, mod_name):
        pathname = os.path.abspath(os.path.join(os.path.dirname(__file__), self.base_path + ext))
        try:
            sample_data = np.fromfile(pathname, dtype=np.uint8)
        except OSError as e:
            pytest.skip(f"no source file {pathname}")
        else:
            container = guess_container(sample_data)
            assert container.decompression_order[0].compression_algorithm == mod_name

            output = "tmp." + os.path.basename(pathname)
            pathname = os.path.join(os.path.dirname(__file__), output)

            try:
                compressed = container.calc_packed_bytes()
            except errors.InvalidAlgorithm:
                if ext in read_only_compressors:
                    pytest.skip(f"skipping {pathname} because can't compress {ext} yet")

            # compressed data may not be the same; don't really care as long as
            # it decompresses the same
            container2 = guess_container(compressed)
            assert np.array_equal(container._data, container2._data)


class TestContainerAtariDosSDImage(BaseContainerTest):
    base_path = "../samples/dos_sd_test1.atr"
    expected_mime = "application/vnd.atari8bit.atr"
    num_files_in_sample = 5

class TestContainerAtariDosEDImage(BaseContainerTest):
    base_path = "../samples/dos_ed_test1.atr"
    expected_mime = "application/vnd.atari8bit.atr"
    num_files_in_sample = 5

class TestContainerAtariDosDDImage(BaseContainerTest):
    base_path = "../samples/dos_dd_test1.atr"
    expected_mime = "application/vnd.atari8bit.atr"
    num_files_in_sample = 5


class TestMultipleCompression:
    @pytest.mark.parametrize(("pathname"), globbed_sample_atari_files)
    def test_glob(self, pathname):
        sample_data = np.fromfile(pathname, dtype=np.uint8)
        container = guess_container(sample_data)
        container.guess_media_type()
        output = "tmp." + os.path.basename(pathname)
        pathname = os.path.join(os.path.dirname(__file__), output)

        try:
            compressed = container.calc_packed_bytes()
        except errors.InvalidAlgorithm as e:
            pytest.skip(f"skipping {pathname}: {e}")
        else:
            # compressed data may not be the same; don't really care as long as
            # it decompresses the same
            container2 = guess_container(compressed)
            assert np.array_equal(container._data, container2._data)


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.DEBUG)
    c = TestContainerAtariDosSDImage()
    # c.test_container(".gz", "gzip")
    # c.test_container(".dcm", "dcm")
    c = TestMultipleCompression()
    c.test_glob("../samples/mydos_sd_mydos4534.dcm.lz4")
