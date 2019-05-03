import numpy as np

from .. import errors
from ..compressor import Compressor

import logging
log = logging.getLogger(__name__)


class DCMCompressor(Compressor):
    compression_algorithm = "dcm"

    valid_densities = {
        0: (720, 128),
        1: (720, 256),
        2: (1040, 128),
    }

    def get_next(self):
        try:
            data = self.raw[self.index]
        except IndexError:
            raise errors.InvalidCompressor("Incomplete DCM file")
        else:
            self.index += 1
        return data

    def calc_unpacked_data(self, data):
        self.sector_size = 0
        self.num_sectors = 0
        self.current_sector = 0
        self.index = 0
        self.count = len(data)
        self.raw = data
        self.output = np.zeros(200000, dtype=np.uint8)  # max is 1 DD image
        self.current = np.zeros(256, dtype=np.uint8)
        expected_pass = 1
        last_pass = False
        while not last_pass:
            archive_type = self.get_next()
            log.debug(f"index {self.index-1}: archive_type={archive_type:02x}")
            if archive_type == 0xf9 or archive_type == 0xfa:
                archive_flags = self.get_next()
                pass_num = archive_flags & 0x1f
                last_pass = bool(archive_flags & 0x80)
                log.debug(f"index {self.index-1}: pass number={pass_num} last={last_pass}")
                if archive_flags & 0x1f != expected_pass:
                    if archive_type == 0xf9:
                        raise errors.InvalidCompressor("DCM multi-file archive combined in the wrong order")
                    else:
                        raise errors.InvalidCompressor("Expected pass one of DCM archive first")
                density_flag = (archive_flags >> 5) & 3
                try:
                    self.num_sectors, self.sector_size = self.valid_densities[density_flag]
                except KeyError:
                    raise errors.InvalidCompressor(f"Unsupported density flag {density_flag} in DCM")
                log.debug(f"sectors: {self.num_sectors}x{self.sector_size}B")
            else:
                raise errors.InvalidCompressor("Not a DCM file")
            self.get_current_sector()

            while True:
                block_type = self.get_next()
                log.debug(f"index {self.index-1}: processing sector {self.current_sector}, type=${block_type & 0x7f:02x}")

                if block_type == 0x45:
                    # pass end, start next pass
                    expected_pass = (expected_pass + 1) % 32
                    log.debug(f"pass end; next pass should be {expected_pass}")
                    break
                try:
                    func = self.block_type_func[block_type & 0x7f]
                except KeyError:
                    if block_type == 0xfa or block_type == 0xf9:
                        raise errors.InvalidCompressor(f"Found section start byte but previous section never ended")
                    else:
                        raise errors.InvalidCompressor(f"Unsupported block type {block_type} in DCM")
                func(self)
                self.copy_current_to_sector()

                if block_type > 0x80:
                    self.current_sector += 1
                else:
                    self.get_current_sector()

        return self.output[:self.num_sectors * self.sector_size]

    def get_current_sector(self):
        lo = self.get_next()
        hi = self.get_next()
        self.current_sector = hi * 256 + lo
        log.debug(f"index {self.index-2}: found sector {self.current_sector}")

    def copy_current_to_sector(self):
        pos = (self.current_sector - 1) * self.sector_size
        self.output[pos:pos + self.sector_size] = self.current[:self.sector_size]

    def decode_41(self):
        index = self.get_next()
        while index > 0:
            self.current[index] = self.get_next()
            index -= 1

    def decode_42(self):
        self.current[0:124] = self.get_next()
        self.current[124] = self.get_next()
        self.current[125] = self.get_next()
        self.current[126] = self.get_next()
        self.current[127] = self.get_next()

    def decode_43(self):
        # run-length encoded block
        index = 0

        while index < self.sector_size:
            # 1. starts with copying a string verbatim: find end
            end = self.get_next()
            if index > 0 and end == 0:
                end = 256

            # 2: copy bytes verbatim until end offset
            log.debug(f"0x43: copying verbatim {index}-{end}")
            while index < end:
                self.current[index] = self.get_next()
                index += 1

            if index < self.sector_size:
                # 3: run-length encoding
                end = self.get_next()
                if index > 0 and end == 0:
                    end = 256
                fill_byte = self.get_next()
                log.debug(f"0x43: rle: ${fill_byte:02x} {index}-{end}")
                while index < end:
                    self.current[index] = fill_byte
                    index += 1

    def decode_44(self):
        index = self.get_next()
        while index < self.sector_size:
            self.current[index] = self.get_next()
            index += 1

    def decode_46(self):
        # same as last sector!
        return

    def decode_47(self):
        log.debug(f"index {self.index}-{self.index+self.sector_size}: uncompressed sector {self.current_sector}")
        index = 0
        while index < self.sector_size:
            self.current[index] = self.get_next()
            index += 1


    block_type_func = {
        0x41: decode_41,
        0x42: decode_42,
        0x43: decode_43,
        0x44: decode_44,
        0x46: decode_46,
        0x47: decode_47,
    }
