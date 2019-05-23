import os

import pytest

import numpy as np
np.set_printoptions(formatter={'int': lambda x: f"{x:02x}"})

from mock import globbed_sample_atari_files

from atrip.container import Container, guess_container
from atrip.compressors import dcm
from atrip.media_type import Media, guess_media_type
from atrip.media_types.atari_disks import AtariSingleDensity

compressor = dcm.DCMCompressor()



class TestDCMBlocks:
    def setup(self):
        data = np.empty(92160, dtype=np.uint8)
        data[:] = np.repeat(np.arange(720, dtype=np.uint8), 128)
        data[::100] = 0xff
        self.byte_data = data.tobytes()
        self.container = Container(self.byte_data)
        self.media = AtariSingleDensity(self.container)
        compressor.init_packing(self.media)
        compressor.raw = compressor.pass_buffer
        compressor.index = 0

    def validate_block(self, value):
        c = compressor
        c.current[:] = c.previous[:]
        print("starting from")
        print(c.current[:128])
        code = c.get_next()
        print("using code", hex(code))
        func = c.decode_block_type_func[code]
        func(c)
        print("produced")
        print(c.current[:128])
        assert np.array_equal(c.current[:128], value)

    def test_42(self):
        c = compressor
        c.current[:124] = 0
        c.current[124] = 124
        c.current[125] = 125
        c.current[126] = 126
        c.current[127] = 127
        value = c.current[:128].copy()
        c.encode_42(-1)
        r = c.pass_buffer[0:c.pass_buffer_index]
        print(r)

        # assert len(r) == 6
        # assert r[0] == 0x42
        # assert np.array_equal(r[1:6], c.current[123:128])

        # c.previous[:] = c.current[:]
        # c.decode_42()
        # print(c.current[:128])
        # assert np.array_equal(c.current[:128], c.previous[:128])
        self.validate_block(value)

    def test_47(self):
        c = compressor
        c.current[:128] = np.arange(128, dtype=np.uint8)
        value = c.current[:128].copy()
        c.encode_47(-1)
        r = c.pass_buffer[0:c.pass_buffer_index]
        print(r)

        assert len(r) == 129
        assert r[0] == 0x47
        assert np.array_equal(r[1:129], c.current[0:128])

        # c.previous[:] = c.current[:]
        # c.current[:] = 255
        # c.decode_47()
        # print(c.current[:128])
        # assert np.array_equal(c.current[:128], c.previous[:128])
        self.validate_block(value)

    def test_41(self):
        c = compressor
        m = self.media
        c.current[:128] = m[256:384]
        c.previous[:128] = m[128:256]
        c.current[80:] = c.previous[80:]
        value = c.current[:128].copy()
        c.encode_best(False, [0x41])
        r = c.pass_buffer[0:c.pass_buffer_index]
        print("previous")
        print(c.previous[:128])
        print("current")
        print(c.current[:128])
        print("encoded")
        print(r, len(r))

        # assert len(r) == 129
        assert r[0] == 0x41
        # assert np.array_equal(r[1:129], c.current[0:128])

        # c.current[:] = c.previous[:]
        # print("starting from")
        # print(c.current[:128])
        # c.decode_41()
        # print("produced")
        # print(c.current[:128])
        # assert np.array_equal(c.current[:128], value)
        self.validate_block(value)

    def test_44(self):
        c = compressor
        m = self.media
        c.current[:128] = m[256:384]
        c.previous[:128] = m[128:256]
        c.current[:80] = c.previous[:80]
        value = c.current[:128].copy()
        c.encode_best(False, [0x44])
        r = c.pass_buffer[0:c.pass_buffer_index]
        print("previous")
        print(c.previous[:128])
        print("current")
        print(c.current[:128])
        print("encoded")
        print(r, len(r))

        # assert len(r) == 129
        assert r[0] == 0x44
        # assert np.array_equal(r[1:129], c.current[0:128])

        # c.current[:] = c.previous[:]
        # print("starting from")
        # print(c.current[:128])
        # c.decode_44()
        # print("produced")
        # print(c.current[:128])
        # assert np.array_equal(c.current[:128], value)

        self.validate_block(value)

    def test_43(self):
        c = compressor
        m = self.media
        m[256:384] = np.arange(128, dtype=np.uint8)
        c.current[:128] = m[256:384]
        c.previous[:128] = m[128:256]
        c.current[20:40] = 10
        c.current[50:60] = 99
        c.current[60:80] = 4
        value = c.current[:128].copy()
        c.encode_best(False, [0x43])
        r = c.pass_buffer[0:c.pass_buffer_index]
        print("previous")
        print(c.previous[:128])
        print("current")
        print(c.current[:128])
        print("encoded")
        print(r, len(r))

        # assert len(r) == 129
        assert r[0] == 0x43
        self.validate_block(value)

    def test_43_failure(self):
        c = compressor
        m = self.media

        # No consecutive bytes, so 43 encoding should fail
        m[256:384] = np.arange(128, dtype=np.uint8)
        c.current[:128] = m[256:384]
        c.previous[:128] = m[128:256]
        value = c.current[:128].copy()
        print("previous")
        print(c.previous[:128])
        print("current")
        print(c.current[:128])
        c.encode_best(False, [0x43])
        r = c.pass_buffer[0:c.pass_buffer_index]
        print("encoded")
        print(r, len(r))
        assert r[0] == 0x47
        self.validate_block(value)



class TestDCM:
    def setup(self):
        data = np.empty(92160, dtype=np.uint8)
        data[:] = np.repeat(np.arange(720, dtype=np.uint8), 128)
        data[::100] = 0xff
        self.byte_data = data.tobytes()
        self.container = Container(self.byte_data)
        self.media = AtariSingleDensity(self.container)

    @pytest.mark.parametrize("allowed_blocks", [
        None,
        [0x44],
        [0x41],
    ])
    def test_encode(self, allowed_blocks):
        packed = compressor.calc_packed_data(self.byte_data, self.media, allowed_blocks)
        assert packed != self.byte_data
        unpacked = compressor.calc_unpacked_data(packed)

        print(len(self.byte_data), len(packed), len(unpacked))
        orig = np.frombuffer(self.byte_data, dtype=np.uint8)
        restored = np.frombuffer(unpacked, dtype=np.uint8)
        if not np.array_equal(orig, restored):
            for i in range(720):
                start = 128 * i
                d1 = orig[start:start + 128]
                d2 = restored[start:start + 128]
                print(f"trying sector {i+1}")
                print(d1)
                print(d2)
                if not np.array_equal(d1, d2):
                    print("failure!")
                    break
        assert np.array_equal(orig, restored)


class TestFileCompression:
    @pytest.mark.parametrize(("pathname"), globbed_sample_atari_files)
    def test_glob(self, pathname):
        sample_data = np.fromfile(pathname, dtype=np.uint8)
        container = guess_container(sample_data)
        container.guess_media_type()
        m = container.media
        # can't use container._data because the container may include a header
        # which is not part of the actual media. DCM, for instance, doesn't use
        # a header while ATR does.
        packed = compressor.calc_packed_data(m.data, m)
        unpacked = compressor.calc_unpacked_data(packed)
        out = np.frombuffer(unpacked, dtype=np.uint8)
        print(len(container.media.data))
        print(len(out))
        if m.sector_size == 256 and len(m) == 183936 and len(out) == 184320:
            # DCM expands DD images full DD boot sectors, so must compare the
            # first 3 SD sectors individually
            assert np.array_equal(m.data[0:128], out[0:128])
            assert np.array_equal(m.data[128:256:], out[256:384])
            assert np.array_equal(m.data[256:384], out[512:640])
            assert np.array_equal(m.data[384:], out[768:])
        else:
            assert np.array_equal(m.data, out)

if __name__ == "__main__":
    t = TestDCMBlocks()
    t.setup()
    t.test_43()
    t.setup()
    t.test_43_failure()
    # # t.test_42()
    # # t.setup()
    # # t.test_47()
    # t.setup()
    # t.test_41()
    # t.setup()
    # t.test_44()

    # t = TestDCM()
    # t.setup()
    # t.test_encode([0x44])

    # t = TestFileCompression()
    # t.test_glob("../samples/dos_dd_test1.atr")
