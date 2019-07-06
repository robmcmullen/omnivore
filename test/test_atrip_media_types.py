import glob

import numpy as np

from mock import *

from atrip.container import guess_container
from atrip.media_type import Media, guess_media_type
from atrip import errors


class TestMediasInTestDataDir:
    base_path = None
    expected_mime = ""

    @pytest.mark.parametrize("pathname", sorted(glob.glob(os.path.join(os.path.dirname(__file__), "../samples/", "*"))))
    def test_samples_dir(self, pathname):
        if ".tar" in pathname or ".zip" in pathname:
            pytest.skip(f"skipping collections for this test: {pathname}")
        print(f"checking {pathname}")
        sample_data = np.fromfile(pathname, dtype=np.uint8)
        container = guess_container(sample_data)
        container.guess_media_type()
        is_expected_media(container, pathname)


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.WARNING)
    log = logging.getLogger("atrip.media_type")
    log.setLevel(logging.DEBUG)

    def check(pathname):
        print(f"checking {pathname}")
        sample_data = np.fromfile(pathname, dtype=np.uint8)
        container = guess_container(sample_data)
        container.guess_media_type()
        print(container.verbose_info)

    import sys
    import glob
    if len(sys.argv) > 1:
        images = sys.argv[1:]
    else:
        images = sorted(glob.glob(os.path.join(os.path.dirname(__file__), "../samples/", "*")))
    for pathname in images:
        check(pathname)
