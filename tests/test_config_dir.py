import os
import itertools

import numpy as np
import pytest

import mock


class TestUserDir(object):
    def setup(self):
        self.app = mock.MockApplication()

    def test_simple(self):
        self.app.setup_file_persistence("MapRoomTest")
        subdir = "dir1"
        d = self.app.get_user_dir(subdir)
        assert os.path.exists(d)
        created = set()
        for i in range(5):
            filename = "test%d" % i
            text = "this is %s in %s" % (filename, subdir)
            self.app.save_text_user_data(subdir, filename, text)
            loaded_text = self.app.get_text_user_data(subdir, filename)
            assert loaded_text == text
            created.add(filename)

        available = set(self.app.get_available_user_data(subdir))
        assert available == created



if __name__ == "__main__":
    t = TestConfigDir()
    t.setup()
    t.test_simple()
