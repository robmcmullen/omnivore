from __future__ import print_function
from builtins import object
import numpy as np

from mock import *

from atrcopy.container import guess_container
from atrcopy.parser import iter_parsers
from atrcopy import get_xex, interleave_segments, user_bit_mask, diff_bit_mask
from atrcopy import errors


class BaseContainerTest:
    base_path = None
    expected_mime = ""

    @pytest.mark.parametrize("ext", ['.gz', '.bz2', '.xz', '.dcm'])
    def test_container(self, ext):
        pathname = self.base_path + ext
        try:
            sample_data = np.fromfile(pathname, dtype=np.uint8)
        except OSError:
            pass
        else:
            container = guess_container(sample_data)
            mime, parser = iter_parsers(container)
            assert mime == self.expected_mime
            assert len(parser.image.files) == self.num_files_in_sample

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
