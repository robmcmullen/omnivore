import numpy as np

from . import errors
from .segments import SegmentData


class DiskImageContainer:
    def __init__(self, data):
        self.unpacked = self.unpack_raw_data(data)

    def unpack_raw_data(self, data):
        pass
