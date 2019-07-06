import textwrap

import numpy as np

from .. import errors
from ..stringifier import Stringifier


class CBytes(Stringifier):
    text_type = "c_bytes"
    ui_name = "C bytes"

    def calc_text(self, byte_data):
        text = ",\n".join([",".join(["0x%02x" % d for d in c]) for c in [byte_data[i:i+8] for i in range(0, len(byte_data), 8)]])
        return text
