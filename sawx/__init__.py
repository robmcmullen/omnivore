from ._metadata import __author__, __author_email__, __url__, __download_url__, __bug_report_url__

try:
    from ._version import __version__
except ImportError:
    __version__ = "dev"

from .application import SawxApp
from .frame import SawxFrame
from .editor import SawxEditor
from .action import SawxAction, SawxActionRadioMixin
from . import errors

import logging
log = logging.getLogger(__name__)
