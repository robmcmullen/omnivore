import numpy as np

from .. import errors
from ..compressor import Compressor

import logging
# logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)
# log.setLevel(logging.DEBUG)


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
            raise errors.InvalidAlgorithm("Incomplete DCM file")
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
                        raise errors.InvalidAlgorithm("DCM multi-file archive combined in the wrong order")
                    else:
                        raise errors.InvalidAlgorithm("Expected pass one of DCM archive first")
                density_flag = (archive_flags >> 5) & 3
                try:
                    self.num_sectors, self.sector_size = self.valid_densities[density_flag]
                except KeyError:
                    raise errors.InvalidAlgorithm(f"Unsupported density flag {density_flag} in DCM")
                log.debug(f"sectors: {self.num_sectors}x{self.sector_size}B")
            else:
                raise errors.InvalidAlgorithm("Not a DCM file")
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
                        raise errors.InvalidAlgorithm(f"Found section start byte but previous section never ended")
                    else:
                        raise errors.InvalidAlgorithm(f"Unsupported block type {block_type} in DCM")
                func(self)
                self.copy_current_to_sector()

                if block_type > 0x80:
                    self.current_sector += 1
                else:
                    self.get_current_sector()

        return self.output[:self.num_sectors * self.sector_size].tobytes()

    def get_current_sector(self):
        lo = self.get_next()
        hi = self.get_next()
        self.current_sector = hi * 256 + lo
        log.debug(f"index {self.index-2}: found sector {self.current_sector}")

    def copy_current_to_sector(self):
        pos = (self.current_sector - 1) * self.sector_size
        self.output[pos:pos + self.sector_size] = self.current[:self.sector_size]

    def decode_41(self):
        """Change beginning of sector"""
        index = self.get_next()
        while index >= 0:
            self.current[index] = self.get_next()
            index -= 1

    def decode_42(self):
        """DOS sector?"""
        self.current[0:124] = self.get_next()
        self.current[124] = self.get_next()
        self.current[125] = self.get_next()
        self.current[126] = self.get_next()
        self.current[127] = self.get_next()

    def decode_43(self):
        """Run-length encoded block"""
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
        """Change the end of the sector"""
        index = self.get_next()
        while index < self.sector_size:
            self.current[index] = self.get_next()
            index += 1

    def decode_46(self):
        """Same as last sector"""
        return

    def decode_47(self):
        """Uncompressed"""
        log.debug(f"index {self.index}-{self.index+self.sector_size}: uncompressed sector")
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

    def init_packing(self, media):
        try:
            self.sector_size = media.sector_size
            self.num_sectors = media.num_sectors
        except AttributeError:
            raise errors.InvalidMediaSize("DCM Compressor only works with disk images")
        s = (self.num_sectors, self.sector_size)
        for density_flag, size in self.valid_densities.items():
            if s == size:
                self.density_flag = density_flag
                break
        else:
            raise errors.InvalidMediaSize("DCM Compressor only works with standard size Atari disk images")
        self.index = 0
        self.output = np.zeros(200000, dtype=np.uint8)  # max is 1 DD image
        self.current = np.zeros(256, dtype=np.uint8)
        self.previous = np.zeros(256, dtype=np.uint8)
        self.pass_buffer = np.zeros(0x6500, dtype=np.uint8)
        self.pass_buffer_index = 0
        self.record_start_index = 0
        self.pass_number = 1

    def put_byte(self, value):
        self.pass_buffer[self.pass_buffer_index] = value
        self.pass_buffer_index += 1

    def calc_packed_data(self, byte_data, media, block_restrictions=None):
        self.init_packing(media)
        output_index = 0
        current_sector = 1
        previous_sector = 0

        while current_sector <= self.num_sectors:
            log.debug(f"dcm: starting pass {self.pass_number} at sector {current_sector}")
            self.encode_fa(current_sector)
            first_sector_in_pass = 0

            while self.pass_buffer_index < 0x5e00:
                if current_sector > self.num_sectors:
                    break
                pos, size = media.get_index_of_sector(current_sector)
                self.current[:size] = media[pos:pos + size]
                if np.count_nonzero(self.current[:size]) == 0:  # empty
                    log.debug(f"dcm: skipping empty sector {current_sector}")
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
                    log.debug(f"dcm: encoding sector {current_sector} at buffer index {self.pass_buffer_index}")

                    self.encode_best(current_sector == first_sector_in_pass, block_restrictions)

                    # save current sector data so it can be compared
                    self.previous[:size] = self.current[:size]
                    previous_sector = current_sector
                    current_sector += 1

            log.debug(f"dcm: filled buffer for pass {self.pass_number}")

            # force next pass to not attempt to read a sector number
            self.encode_implicit_next_sector()

            self.encode_45()

            pass_length = self.pass_buffer_index

            # rerecord FA block to show if it is the final pass
            last_pass = current_sector > self.num_sectors
            self.encode_fa(first_sector_in_pass, last_pass)

            self.output[output_index:output_index + pass_length] = self.pass_buffer[:pass_length]
            output_index += pass_length
            self.pass_number += 1

        return self.output[:output_index].tobytes()

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
            flag |= 0x80
        self.put_byte(flag)
        self.encode_sector(sector)

    def encode_45(self):
        self.record_start_index = self.pass_buffer_index
        self.put_byte(0x45)

    def encode_best(self, first=False, block_restrictions=None):
        # NOTE: 0x46, 0x47 always allowed
        if block_restrictions is None:
            allowed_blocks = set([0x41, 0x42, 0x43, 0x44])
        else:
            allowed_blocks = block_restrictions
        size = self.sector_size
        best_size = size
        best_block = 0x47
        encoder_arg = 0

        if not first:
            same = self.current[:size] - self.previous[:size]
            where_diff = np.where(same != 0)[0]
            # print("same", same)
            # print("where_diff", where_diff)
            try:
                first_diff = where_diff[0]
            except IndexError:
                # no differences!
                best_block = 0x46
                best_size = 0
            else:
                last_diff = where_diff[-1]
                len_41 = last_diff + 1
                if len_41 < best_size and 0x41 in allowed_blocks:
                    # print(f"41: {last_diff}, {where_diff}")
                    best_size = len_41
                    best_block = 0x41
                    encoder_arg = last_diff

                len_44 = size - first_diff + 1
                if len_44 < best_size and 0x44 in allowed_blocks:
                    # print("current", self.current[:size])
                    # print("previous", self.previous[:size])
                    # print("same", same)
                    # print("same", self.current[:size] - self.previous[:size])
                    # print("where_diff", where_diff)
                    # print(f"44: {first_diff}, {where_diff}")
                    best_size = len_44
                    best_block = 0x44
                    encoder_arg = first_diff

        same = np.diff(self.current[:size] - self.current[0])
        where_diff = np.where(same != 0)[0]
        try:
            first_diff = where_diff[0] + 1
        except IndexError:
            # no differences anywhere
            first_diff = self.sector_size
        if first_diff > 123 and best_size > 6 and 0x42 in allowed_blocks:
            best_block = 0x42
            best_size = 6
        if 0x43 in allowed_blocks:
            len_43, groups_43 = self.prepare_43()
            if len_43 < best_size and 0x43 in allowed_blocks:
                best_size = len_43
                best_block = 0x43
                encoder_arg = groups_43

        log.debug(f"dcm: encoding as block type ${best_block:x}, size={best_size}")
        func = self.encode_block_type_func[best_block]
        func(self, encoder_arg)

    def encode_41(self, index):
        """Change beginning of sector"""
        self.record_start_index = self.pass_buffer_index
        self.put_byte(0x41)
        self.put_byte(index)
        while index >= 0:
            self.put_byte(self.current[index])
            index -= 1

    def encode_42(self, unused):
        """DOS sector? Single density only, apparently"""
        self.record_start_index = self.pass_buffer_index
        self.put_byte(0x42)
        self.put_byte(self.current[123])
        self.put_byte(self.current[124])
        self.put_byte(self.current[125])
        self.put_byte(self.current[126])
        self.put_byte(self.current[127])

    def prepare_43(self):
        size = self.sector_size

        # find where the values are the same
        d = np.diff(self.current[:size])
        # [  1,   1,   1,   1,   1,   1,   1,   1,   1,   1,   1,   1,   1,
        #    1,   1,   1,   1,   1,   1,  -9,   0,   0,   0,   0,   0,   0,
        #    0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,
        #   30,   1,   1,   1,   1,   1,   1,   1,   1,   1,  50,   0,   0,
        #    0,   0,   0,   0,   0,   0,   0, -95,   0,   0,   0,   0,   0,
        #    0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,
        #    0,  76,   1,   1,   1,   1,   1,   1,   1,   1,   1,   1,   1,
        #    1,   1,   1,   1,   1,   1,   1,   1,   1,   1,   1,   1,   1,
        #    1,   1,   1,   1,   1,   1,   1,   1,   1,   1,   1,   1,   1,
        #    1,   1,   1,   1,   1,   1,   1,   1,   1,   1]

        # The index before the first zero in a group of zeros is the start of a
        # group of the same values. This gives a list of indexes of the groups
        same = np.where(d == 0)[0]
        # [20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36,
        #  37, 38, 50, 51, 52, 53, 54, 55, 56, 57, 58, 60, 61, 62, 63, 64, 65,
        #  66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78]

        # If no consecutive bytes have the same value, abort!
        if len(same) == 0:
            return 100000, None

        # The changes in same are the breaks in groups:
        changes=np.diff(same)
        # [ 1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1,
        #   1, 12,  1,  1,  1,  1,  1,  1,  1,  1,  2,  1,  1,  1,  1,  1,  1,
        #   1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1]

        # each 1 represents the same value as the next item in the array, so
        # values > 1 are where there are gaps, i.e. the start of a new group
        starts = np.where(changes > 1)[0] + 1
        # [19, 28]
        ends = starts - 1
        # [18, 27]

        # but it doesn't include the start of the first group or the end of the
        # last group
        starts = list(starts)
        starts[0:0] = [0]
        ends = list(ends)
        ends.append(-1)

        rle_starts = same[starts]
        # [20, 50, 60]
        rle_ends = same[ends] + 1 + 1  # inclusive, so need extra to form slice
        # [40, 60, 80]
        rle_groups = list(zip(rle_starts, rle_ends))

        # start with verbatim copy, then alternate with rle
        length = 0
        index = 0
        for start, end in rle_groups:
            length += 1 + start - index  # verbatim
            index = start
            if index < size:
                length += 2  # rle blocks always encoded in 2 bytes
            index = end
        if index < size:
            length += 1 + size - index
            rle_groups.append((size, size))
        return length, rle_groups

    def encode_43(self, groups):
        """Run-length encoded block"""
        self.record_start_index = self.pass_buffer_index
        self.put_byte(0x43)
        index = 0
        size = self.sector_size
        for rle_start, rle_end in groups:
            self.put_byte(rle_start)
            while index < rle_start:
                self.put_byte(self.current[index])
                index += 1

            if index < size:
                self.put_byte(rle_end)
                self.put_byte(self.current[index])
                index += rle_end - rle_start

    def encode_44(self, index):
        """Change beginning of sector"""
        self.record_start_index = self.pass_buffer_index
        self.put_byte(0x44)
        self.put_byte(index)
        while index < self.sector_size:
            self.put_byte(self.current[index])
            index += 1

    def encode_46(self, unused):
        self.record_start_index = self.pass_buffer_index
        self.put_byte(0x46)

    def encode_47(self, index):
        """Uncompressed"""
        self.record_start_index = self.pass_buffer_index
        self.put_byte(0x47)
        index = 0
        while index < self.sector_size:
            self.put_byte(self.current[index])
            index += 1


    encode_block_type_func = {
        0x41: encode_41,
        0x42: encode_42,
        0x43: encode_43,
        0x44: encode_44,
        0x46: encode_46,
        0x47: encode_47,
    }

# Notes:
#
# 
# >>> current=np.arange(128, dtype=np.uint8)
# >>> previous=np.arange(128, dtype=np.uint8)
# >>> previous[80:100]=0xff
# >>> d=np.diff(current-previous)
# >>> d
# array([  0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,
#          0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,
#          0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,
#          0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,
#          0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,
#          0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,
#          0,  81,   1,   1,   1,   1,   1,   1,   1,   1,   1,   1,   1,
#          1,   1,   1,   1,   1,   1,   1,   1, 156,   0,   0,   0,   0,
#          0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,
#          0,   0,   0,   0,   0,   0,   0,   0,   0,   0], dtype=uint8)
# >>> np.where(d!=0)[0]
# array([79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95,
#        96, 97, 98, 99])
# >>> w=np.where(d!=0)[0]
# >>> w
# array([79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95,
#        96, 97, 98, 99])
# >>> first_diff = w[0] + 1
# >>> last_diff = w[-1] + 1
# >>> previous[0:first_diff]
# array([ 0,  1,  2,  3,  4,  5,  6,  7,  8,  9, 10, 11, 12, 13, 14, 15, 16,
#        17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33,
#        34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50,
#        51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67,
#        68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79], dtype=uint8)
# >>> previous[first_diff:last_diff]
# array([255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255,
#        255, 255, 255, 255, 255, 255, 255], dtype=uint8)
# >>> previous[last_diff:]
# array([100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112,
#        113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125,
#        126, 127], dtype=uint8)
# >>> 



# RLE notes:
#
# >>> a=np.arange(128)
# >>> a[20:40]=10
# >>> a[50:60]=99
# >>> a[60:80]=4
# >>> a
# array([  0,   1,   2,   3,   4,   5,   6,   7,   8,   9,  10,  11,  12,
#         13,  14,  15,  16,  17,  18,  19,  10,  10,  10,  10,  10,  10,
#         10,  10,  10,  10,  10,  10,  10,  10,  10,  10,  10,  10,  10,
#         10,  40,  41,  42,  43,  44,  45,  46,  47,  48,  49,  99,  99,
#         99,  99,  99,  99,  99,  99,  99,  99,   4,   4,   4,   4,   4,
#          4,   4,   4,   4,   4,   4,   4,   4,   4,   4,   4,   4,   4,
#          4,   4,  80,  81,  82,  83,  84,  85,  86,  87,  88,  89,  90,
#         91,  92,  93,  94,  95,  96,  97,  98,  99, 100, 101, 102, 103,
#        104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116,
#        117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127])

# >>> d=np.diff(a)
# >>> d
# array([  1,   1,   1,   1,   1,   1,   1,   1,   1,   1,   1,   1,   1,
#          1,   1,   1,   1,   1,   1,  -9,   0,   0,   0,   0,   0,   0,
#          0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,
#         30,   1,   1,   1,   1,   1,   1,   1,   1,   1,  50,   0,   0,
#          0,   0,   0,   0,   0,   0,   0, -95,   0,   0,   0,   0,   0,
#          0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,
#          0,  76,   1,   1,   1,   1,   1,   1,   1,   1,   1,   1,   1,
#          1,   1,   1,   1,   1,   1,   1,   1,   1,   1,   1,   1,   1,
#          1,   1,   1,   1,   1,   1,   1,   1,   1,   1,   1,   1,   1,
#          1,   1,   1,   1,   1,   1,   1,   1,   1,   1])
# >>> 
#
# The index before the first zero in a group of zeros is the start of a group
# of the same values. This gives a list of indexes of the groups:
#
# >>> same=np.where(d==0)[0]
# >>> same
# array([20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36,
#        37, 38, 50, 51, 52, 53, 54, 55, 56, 57, 58, 60, 61, 62, 63, 64, 65,
#        66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78])
#
# and where it is different:
#
# >>> changes=np.diff(same)
# >>> changes
# array([ 1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1,
#         1, 12,  1,  1,  1,  1,  1,  1,  1,  1,  2,  1,  1,  1,  1,  1,  1,
#         1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1])
#
# should be the start of a new group.
#
# >>> starts=np.where(changes > 1)[0] + 1
# >>> starts
# array([19, 28])
# >>> same[0:19]
# array([20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36,
#        37, 38])
# >>> same[19:28]
# array([50, 51, 52, 53, 54, 55, 56, 57, 58])
# >>> same[28:]
# array([60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76,
#        77, 78])
