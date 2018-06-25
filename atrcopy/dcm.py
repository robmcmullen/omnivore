import numpy as np

from . import errors
from .container import DiskImageContainer
from .segments import SegmentData


class DCMContainer(DiskImageContainer):
    valid_densities = {
        0: (720, 128),
        1: (720, 256),
        2: (1040, 128),
    }

    def get_next(self):
        try:
            data = self.raw[self.index]
        except IndexError:
            raise errors.InvalidContainer
        else:
            self.index += 1
        return data

    def unpack_raw_data(self, data):
        self.index = 0
        self.count = len(data)
        self.raw = data
        archive_type = self.get_next()
        if archive_type == 0xf9 or archive_type == 0xfa:
            archive_flags = self.get_next()
            if archive_flags & 0x1f != 1:
                if archive_type == 0xf9:
                    raise errors.InvalidContainer("DCM multi-file archive combined in the wrong order")
                else:
                    raise errors.InvalidContainer("Expected pass one of DCM archive first")
            density_flag = (archive_flags >> 5) & 3
            if density_flag not in self.valid_densities:
                raise errors.InvalidContainer(f"Unsupported density flag {density_flag} in DCM")
        else:
            raise errors.InvalidContainer("Not a DCM file")
        raise errors.UnsupportedContainer("DCM archives are not yet supported")
