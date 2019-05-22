import os
import glob

# Include maproom directory so that maproom modules can be imported normally
import sys
module_dir = os.path.realpath(os.path.abspath(".."))
if module_dir not in sys.path:
    sys.path.insert(0, module_dir)

# print(sys.path)

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

sample_atari_files = [
    "../samples/dos_sd_test1.atr",
    "../samples/dos_ed_test1.atr",
    "../samples/dos_dd_test1.atr",
    "../samples/mydos_sd_mydos4534.dcm",
]

globbed_sample_atari_files = []
for s in sample_atari_files:
    possiblities = glob.glob(s + "*")
    globbed_sample_atari_files.extend(possiblities)
