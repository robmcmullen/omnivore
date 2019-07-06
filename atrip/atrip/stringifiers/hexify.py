import numpy as np

from .. import errors
from ..stringifier import Stringifier


class Hexify(Stringifier):
    text_type = "hexify"
    ui_name = "Hex String"

    def calc_text(self, byte_data):
        text = " ".join(["%02x" % i for i in byte_data])
        return text
