from __future__ import print_function
from __future__ import division
from builtins import object
from mock import *

from atrip import AtariCartImage, SegmentData, RomImage, errors
from atrip.cartridge import known_cart_types


class TestAtariCart:
    def setup(self):
        pass

    def get_cart(self, k_size, cart_type):
        data = np.zeros((k_size * 1024)+16, dtype=np.uint8)
        data[0:4].view("|a4")[0] = b'CART'
        data[4:8].view(">u4")[0] = cart_type
        return data

    @pytest.mark.parametrize("k_size,cart_type", [
            (8, 1),
            (16, 2),
            (8, 21),
            (2, 57),
            (4, 58),
            (4, 59),
        ])
    def test_unbanked(self, k_size, cart_type):
        data = self.get_cart(k_size, cart_type)
        rawdata = SegmentData(data)
        image = AtariCartImage(rawdata, cart_type)
        image.parse_segments()
        assert len(image.segments) == 2
        assert len(image.segments[0]) == 16
        assert len(image.segments[1]) == k_size * 1024

    @pytest.mark.parametrize("k_size,main_size,banked_size,cart_type", [
            (32, 8, 8, 12),
            (64, 8, 8, 13),
            (64, 8, 8, 67),
            (128, 8, 8, 14),
            (256, 8, 8, 23),
            (512, 8, 8, 24),
            (1024, 8, 8, 25),
        ])
    def test_banked(self, k_size, main_size, banked_size, cart_type):
        data = self.get_cart(k_size, cart_type)
        rawdata = SegmentData(data)
        image = AtariCartImage(rawdata, cart_type)
        image.parse_segments()
        assert len(image.segments) == 1 + 1 + (k_size - main_size) //banked_size
        assert len(image.segments[0]) == 16
        assert len(image.segments[1]) == main_size * 1024
        assert len(image.segments[2]) == banked_size * 1024

    def test_bad(self):
        k_size = 32

        # check for error because invalid data in cart image itself
        data = self.get_cart(k_size, 1337)
        rawdata = SegmentData(data)
        with pytest.raises(errors.InvalidDiskImage):
            image = AtariCartImage(rawdata, 1337)
        with pytest.raises(errors.InvalidDiskImage):
            image = AtariCartImage(rawdata, 12)

        # check for error with valid cart image, but invalid cart type supplied
        # to the image parser
        data = self.get_cart(k_size, 12)
        rawdata = SegmentData(data)
        with pytest.raises(errors.InvalidDiskImage):
            image = AtariCartImage(rawdata, 1337)


class TestRomCart:
    def setup(self):
        pass

    def get_rom(self, k_size):
        data = np.zeros((k_size * 1024), dtype=np.uint8)
        return data

    @pytest.mark.parametrize("k_size", [1, 2, 4, 8, 16, 32, 64])
    def test_typical_rom_sizes(self, k_size):
        data = self.get_rom(k_size)
        rawdata = SegmentData(data)
        rom_image = RomImage(rawdata)
        rom_image.strict_check()
        rom_image.parse_segments()
        assert len(rom_image.segments) == 1
        assert len(rom_image.segments[0]) == k_size * 1024

    @pytest.mark.parametrize("k_size", [1, 2, 4, 8, 16, 32, 64])
    def test_invalid_rom_sizes(self, k_size):
        data = np.zeros((k_size * 1024) + 17, dtype=np.uint8)
        rawdata = SegmentData(data)
        with pytest.raises(errors.InvalidDiskImage):
            rom_image = RomImage(rawdata)

    @pytest.mark.parametrize("cart", known_cart_types)
    def test_conversion_to_atari_cart(self, cart):
        cart_type = cart[0]
        name = cart[1]
        k_size = cart[2]
        if "Bounty" in name:
            return
        data = self.get_rom(k_size)
        rawdata = SegmentData(data)
        rom_image = RomImage(rawdata)
        rom_image.strict_check()
        rom_image.parse_segments()
        new_cart_image = AtariCartImage(rawdata, cart_type)
        new_cart_image.relaxed_check()
        new_cart_image.parse_segments()
        assert new_cart_image.header.valid
        s = new_cart_image.create_emulator_boot_segment()
        assert len(s) == len(rawdata) + new_cart_image.header.nominal_length
        assert s[0:4].tobytes() == b'CART'
        assert s[4:8].view(dtype=">u4") == cart_type


if __name__ == "__main__":
    from atrip.parsers import mime_parse_order
    print("\n".join(mime_parse_order))

    t = TestAtariCart()
    t.setup()
    #t.test_segment()

