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
                    func = self.decode_block_type_func[block_type & 0x7f]
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


    decode_block_type_func = {
        0x41: decode_41,
        0x42: decode_42,
        0x43: decode_43,
        0x44: decode_44,
        0x46: decode_46,
        0x47: decode_47,
    }

    #### compression

    def put_byte(self, value):
        self.pass_buffer[self.pass_buffer_index] = value
        self.pass_buffer_index += 1

    def calc_packed_data(self, byte_data, media):
        try:
            self.sector_size = media.sector_size
            self.num_sectors = media.num_sectors
        except AttributeError:
            raise errors.InvalidMediaSize("DCM Compressor only works with disk images")
        s = (self.num_sectors, self.sector_size)
        for density_flag, size in self.valid_densities:
            if s == size:
                self.density_flag = density_flag
                break
        else:
            raise errors.InvalidMediaSize("DCM Compressor only works with standard size Atari disk images")
        self.index = 0
        self.count = len(data)
        self.raw = data
        self.output = np.zeros(200000, dtype=np.uint8)  # max is 1 DD image
        self.current = np.zeros(256, dtype=np.uint8)
        self.previous = np.zeros(256, dtype=np.uint8)
        self.pass_buffer = np.zeros(6500, dtype=np.uint8)
        self.pass_buffer_index = 0
        self.record_start_index = 0
        self.pass_number = 1
        current_sector = 1
        previous_sector = 0

        while self.current_sector <= self.num_sectors:
            self.encode_fa(self.current_sector)
            first_sector_in_pass = 0

            while self.pass_buffer_index < 0x5e00:
                if self.current_sector > self.num_sectors:
                    break
                pos, size = media.get_index_of_sector(current_sector)
                self.current[:size] = media[pos:pos + size]
                if np.count_nonzero(self.current[:size]) == 0:  # empty
                    current_sector += 1
                else:
                    if first_sector_in_pass == 0:
                        first_sector_in_pass = current_sector
                        previous_sector = current_sector
                    if current_sector - previous_sector > 1:
                        # save the first non-blank sector if there is a run of
                        # blank sectors
                        self.encode_sector(current_sector)
                    else:
                        self.encode_implicit_next_sector()

                    if current_sector == first_sector_in_pass:
                        self.encode_best(True)
                    else:
                        if np.array_equal(self.current[:size], self.previous[:size]):
                            self.encode_46()
                        else:
                            self.encode_best(False)

                    # save current sector data so it can be compared
                    self.previous[:size] = self.current[:size]
                    previous_sector = current_sector
                    current_sector += 1

            # force next block to not attempt to read a sector number
            self.encode_implicit_next_sector()

            self.encode_45()

            pass_length = self.pass_buffer_index

            # rerecord FA block to show if it is the final pass
            last_pass = current_sector > self.num_sectors
            self.encode_fa(self.current_sector, last_pass)

            self.output[output_index:output_index + pass_length] = self.pass_buffer[:pass_length]
            self.pass_number += 1

    def encode_sector(self, sector):
        self.put_byte(sector & 0xff)
        self.put_byte(sector >> 8)

    def encode_implicit_next_sector(self):
        self.pass_buffer[self.record_start_index] |= 0x80

    def encode_fa(self, sector, last_pass=False):
        self.record_start_index = 0
        self.pass_buffer_index = 0
        self.put_byte(0xfa)
        flag = self.density_flag << 5 | self.pass_number & 0x1f
        if last_pass:
            flag |= 80
        self.put_byte(flag)
        self.encode_sector(sector)

    def encode_45(self):
        self.record_start_index = self.pass_buffer_index
        self.put_byte(0x45)
