from ._metadata import __author__, __author_email__, __url__, __download_url__, __bug_report_url__

try:
    from ._version import __version__
except ImportError:
    __version__ = "dev"

from .application import OmnivoreFrameworkApp
from .frame import OmnivoreFrame
from .editor import OmnivoreEditor
from .action import OmnivoreAction, OmnivoreActionRadioMixin
from . import errors

import logging
log = logging.getLogger(__name__)
