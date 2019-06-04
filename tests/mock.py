

import os

# Include src directory so that modules can be imported normally
import sys
src_dir = os.path.realpath(os.path.abspath(".."))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

import pytest
try:
    slow = pytest.mark.skipif(
        not pytest.config.getoption("--runslow"),
        reason="need --runslow option to run"
        )
except AttributeError:
    # pytest doesn't load the config module when not run using py.test
    # skip this check when running a test_*.py from the command line
    import functools
    slow = lambda a: functools.partial(print, "skipping slow test %s" % repr(a))

# Turn logging on by default at the DEBUG level for tests
import logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

import numpy as np
from numpy.testing import assert_almost_equal

def null(self, *args, **kwargs):
    pass

# class MockApplication(FilePersistenceMixin):
#     document_class = SegmentedDocument

class MockWindowSink(object):
    recalc_view = null
    set_font = null
    Refresh = null

class MockFrame:
    def __init__(self, editor):
        self.active_editor = editor

class MockEditor(object):
    def __init__(self, segment):
        self.frame = MockFrame(self)
        self.segment = segment
        self.document = null

    def change_bytes(self, start, end, bytes):
        print("changing bytes %d-%d to %s" % (start, end, repr(bytes)))

class MockHexEditor(MockEditor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.font_map = MockWindowSink()
        self.bitmap = MockWindowSink()

    update_fonts = null
    update_segments_ui = null
    update_emulator = null

    def view_document(self, doc):
        self.document = doc
        self.find_segment()
