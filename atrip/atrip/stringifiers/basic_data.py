import textwrap

import numpy as np

from .. import errors
from ..stringifier import Stringifier


class BasicData(Stringifier):
    text_type = "basic_data"
    ui_name = "BASIC DATA statements"

    def calc_text(self, byte_data):
        lines = []
        start_line = "DATA "
        line_length = 38 - len(start_line)
        values = " ".join([str(int(i)) for i in byte_data])
        lines = textwrap.wrap(values, line_length)
        lines = [start_line + line.replace(" ", ",") for line in lines]
        text = "\n".join(lines)
        return text
