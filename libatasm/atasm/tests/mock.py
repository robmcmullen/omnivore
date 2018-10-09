import os

# Include package directory so that modules can be imported normally
import sys
parent_dir = os.path.realpath(os.path.abspath(".."))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

import pytest

# Turn logging on by default at the DEBUG level for tests
import logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
