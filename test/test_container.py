from __future__ import print_function
from builtins import object
import numpy as np

from mock import *

from atrip.container import guess_container
from atrip import errors


class BaseContainerTest:
    base_path = None
    expected_mime = ""

    @pytest.mark.parametrize(("ext", "mod_name"), [
        ('', 'no compression'),
        ('.gz', 'gzip'),
        ('.bz2', 'bzip2'),
        ('.xz', 'lzma'),
        ('.dcm', 'dcm'),
    ])
    def test_container(self, ext, mod_name):
        pathname = self.base_path + ext
        try:
            sample_data = np.fromfile(pathname, dtype=np.uint8)
        except OSError:
            pass
        else:
            container = guess_container(sample_data)
            print(container.name)
            assert container.compression_algorithm == mod_name

class TestContainerAtariDosSDImage(BaseContainerTest):
    base_path = "../test_data/container_dos_sd_test1.atr"
    expected_mime = "application/vnd.atari8bit.atr"
    num_files_in_sample = 5

class TestContainerAtariDosEDImage(BaseContainerTest):
    base_path = "../test_data/container_dos_ed_test1.atr"
    expected_mime = "application/vnd.atari8bit.atr"
    num_files_in_sample = 5

class TestContainerAtariDosDDImage(BaseContainerTest):
    base_path = "../test_data/container_dos_dd_test1.atr"
    expected_mime = "application/vnd.atari8bit.atr"
    num_files_in_sample = 5

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.DEBUG)
    c = TestContainerAtariDosSDImage()
    c.test_container(".gz", "gzip")
