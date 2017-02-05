from __future__ import print_function

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

from traits.api import HasTraits, Str, Event

import numpy as np
from numpy.testing import assert_almost_equal

from omnivore.tasks.hex_edit.hex_editor import HexEditor

def null(self, *args, **kwargs):
    pass

class MockTask(HasTraits):
    id = Str("mock")
    machine_menu_changed = Event

class MockEditorArea(HasTraits):
    task = MockTask()

class MockWindowSink(object):
    recalc_view = null
    set_font = null
    Refresh = null

class MockHexEditor(HexEditor):
    editor_area = MockEditorArea()
    font_map = MockWindowSink()
    bitmap = MockWindowSink()

    update_fonts = null
    update_segments_ui = null
    update_emulator = null
    
    def view_document(self, doc):
        self.document = doc
        self.find_segment()
