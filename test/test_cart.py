from __future__ import print_function
from __future__ import division
from builtins import object
from mock import *

from atrcopy import AtariCartImage, SegmentData
from atrcopy import errors


class TestAtariCart:
    def setup(self):
        pass

    def get_cart(self, k_size, cart_type):
        data = np.zeros((k_size * 1024)+16, dtype=np.uint8)
        data[0:4].view("|a4")[0] = b'CART'
        data[4:8].view(">u4")[0] = cart_type
        return data

    def test_unbanked(self):
        carts = [
            (8, 1),
            (16, 2),
            (8, 21),
            (2, 57),
            (4, 58),
            (4, 59),
        ]
        for k_size, cart_type in carts:
            data = self.get_cart(k_size, cart_type)
            rawdata = SegmentData(data)
            image = AtariCartImage(rawdata, cart_type)
            image.parse_segments()
            assert len(image.segments) == 2
            assert len(image.segments[0]) == 16
            assert len(image.segments[1]) == k_size * 1024

    def test_banked(self):
        carts = [
            (32, 8, 8, 12),
            (64, 8, 8, 13),
            (64, 8, 8, 67),
            (128, 8, 8, 14),
            (256, 8, 8, 23),
            (512, 8, 8, 24),
            (1024, 8, 8, 25),
        ]
        for k_size, main_size, banked_size, cart_type in carts:
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




if __name__ == "__main__":
    print("\n".join(mime_parse_order))

    t = TestAtariCart()
    t.setup()
    #t.test_segment()

