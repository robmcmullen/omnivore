import os

from omnivore.arch.disasm import parse_antic_dl, get_antic_dl


class TestDisplayList(object):
    def setup(self):
        self.items = [
            ([0x70, 0x70, 0x70], 1),
            ([0x70, 0x70, 0x70, 7, 7, 7, 8, 7, 0x41, 02, 44], 5),
            ([0x70, 0x70, 0x70, 0x48, 0x0, 0x10, 8, 8, 8, 8, 8, 0x70, 0x70, 0x2, 0x41, 0xee, 0x8], 6),
            ]

    def test_simple(self):
        for before, count in self.items:
            groups = parse_antic_dl(before)
            for group in groups:
                text = get_antic_dl(group)
                print text
            print groups
            assert len(groups) == count

if __name__ == "__main__":
    t = TestDisplayList()
    t.setup()
    t.test_simple()
