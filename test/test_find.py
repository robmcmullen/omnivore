import glob

import numpy as np

from mock import *

from atrip.container import guess_container
from atrip.media_type import Media, guess_media_type
from atrip import errors, find_container, find_collection

class TestContainer:
    container = None

    def setup(self):
        if self.container is None:
            filename = "dos_sd_test1.atr"
            pathname = os.path.join(os.path.dirname(__file__), "../samples", filename)
            self.__class__.container = find_container(pathname)

    def test_find_file(self):
        c = self.container
        dirent = c.find_dirent("A128.DAT", True)
        print(dirent)
        assert dirent is not None

        dirent = c.find_dirent("a1024.dat", False)
        print(dirent)
        assert dirent is not None

        dirent = c.find_dirent("a1024.dat", True)
        print(dirent)
        assert dirent is None

    def test_uuid(self):
        c = self.container
        segments = list(c.iter_segments())
        for s in segments:
            print(s, s.uuid)
            found = c.find_uuid(s.uuid)
            assert s == found


class TestCollection:
    collection = None

    def setup(self):
        if self.collection is None:
            filename = "dos_sd_test_collection.zip"
            pathname = os.path.join(os.path.dirname(__file__), "../samples", filename)
            self.__class__.collection = find_collection(pathname)

    @pytest.mark.parametrize("filename", [
            "A128.DAT",
            "D1:A128.DAT",
            "A1024.DAT",
            "D1:A1024.DAT",
            "D2:E256.DAT",
            "D2:B512.DAT",
            "D3:A8000.DAT",
            "D4:A15000.DAT",
        ])
    def test_find_file(self, filename):
        c = self.collection
        dirent = c.find_dirent(filename, True)
        assert dirent is not None

        lower = filename.lower()
        dirent = c.find_dirent(lower, False)
        assert dirent is not None

        dirent = c.find_dirent(lower, True)
        assert dirent is None

    @pytest.mark.parametrize("filename", [
            "sir_not_appearing_in_this_film",
            "D1:sir_not_appearing_in_this_film",
            "D3:B256.DAT",
            "D4:F4096.DAT",  # deleted file
        ])
    def test_missing_file(self, filename):
        c = self.collection
        dirent = c.find_dirent(filename, True)
        assert dirent is None

    def test_uuid(self):
        c = self.collection
        segments = []
        for item in c.containers:
            segments.extend(item.iter_segments())
        print(c.verbose_info)
        for s in segments:
            print(s, s.uuid)
            found = c.find_uuid(s.uuid)
            assert s == found


if __name__ == "__main__":
    t = TestContainer()
    t.setup()
    # t.test_find_file()
    # t.test_uuid()
    t = TestCollection()
    t.setup()
    t.test_find_file("D1:A128.DAT")
    # t.test_uuid()
