import os

import pytest

from omnivore.udis_fast import miniasm


cputests = [
    ("65816", "6f67726182f61c82fdff8298e910f882a27182ee7e", 0),
    ("z80", "0e25dd21aae6dd3655ff384022804cdd39fd39ddcbf0f5ddcb0101ddcb0102ddcb0202ddcb7f02fdcbe2a9ddcbe2a9", 8),
    ]

class TestMiniasm(object):
    def setup(self):
        self.start_pc = 0xa000

    @pytest.mark.parametrize("cpu,binary,expected_failures", cputests)
    def test_cpu(self, cpu, binary, expected_failures):
        source = bytes.fromhex(binary)
        success, failure = miniasm.process(source, cpu, self.start_pc, cpu)
        assert failure == expected_failures

if __name__ == "__main__":
    t = TestMiniasm()
    t.setup()
    for cpu, binary in cputests:
        t.test_cpu(cpu, binary)
