import os

from omnivore import disassembler as d


class TestDisassemblerTypes(object):
    def setup(self):
        pass

    def test_cpu_list(self):
        v = d.valid_cpus
        print(v)
        assert "6502" in v
        assert "6502undoc" in v
        assert "z80" in v
        assert "jumpman_level" not in v

if __name__ == "__main__":
    t = TestDisassemblerTypes()
    t.setup()
    t.test_cpu_list()
