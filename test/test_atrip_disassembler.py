import sys
import pytest

import numpy as np

from atrip import Container, Segment
from atrip.memory_map import MemoryMap
from atrip.disassembler import ParsedDisassembly, DisassemblyConfig, dd


class TestNOP:
    cpu_id = 10  # 6502
    data = np.zeros(256, dtype=np.uint8) + 0xea
    expected_count = 256
    expected = [
        b'nop',
        b'nop',
        b'nop',
        b'nop',
    ]
    labels = None

    def setup(self):
        c = Container(self.data)
        segment = Segment(c, origin=0x6000)
        driver = DisassemblyConfig()
        segment.style[:] = 0
        segment.disasm_type[:] = self.cpu_id
        self.parsed = driver.parse(segment, 8000)
        self.entries = self.parsed.entries
        if self.__class__.labels is not None:
            self.labels = MemoryMap.from_list("test labels", self.labels)
        print("raw data: ", type(self.data), self.data)
        print("data", segment.data, segment.data.tobytes())
        print("style", segment.style, segment.style.tobytes())
        print("disasm_type", segment.disasm_type, segment.disasm_type.tobytes())

    def test_disasm(self):
        p = self.parsed
        e = self.entries
        assert len(p) == self.expected_count
        # for i in range(len(p)):
        #     print(e[i])
        # print(p.index_to_row)

        t = p.stringify(0, 100, labels=self.labels)
        # for line in t:
        #     print(line)
        for i, text in enumerate(self.expected):
            assert t[i] == text


class TestORA(TestNOP):
    data = np.asarray([1,1,1,0x80,1,2,1,0xff, 0,0,0,0,0,0,0,0, 0,1,1,1,1,1,0,0, 0,0,0,0,0,0,0,0, 0,0,0,0,0,0,0,0], dtype=np.uint8)
    expected_count = 33
    expected = [
        b'ora (L0001,x)',
        b'ora (L0080,x)',
        b'ora (L0002,x)',
        b'ora (L00ff,x)',
        b'brk',
    ]


class TestLabels(TestORA):
    expected = [
        b'ora (L0001,x)',
        b'ora (ADDR80,x)',
        b'ora (L0002,x)',
        b'ora (ADDRFF,x)',
        b'brk',
    ]
    labels = [(0x80, "ADDR80"), (0xff, "ADDRFF")]


def sample():
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'rb') as fh:
            data = np.frombuffer(fh.read(), dtype=np.uint8)
            data = data.astype(dtype=np.uint8)  # prevents data.base from being a 'bytes' object
    else:
        data = repeat_test
    print("raw data: ", type(data), data)
    c = Container(data)
    segment = Segment(c, origin=0x6000)
    print("data", segment.data, segment.data.tobytes())
    print("style", segment.style, segment.style.tobytes())
    print("disasm_type", segment.disasm_type, segment.disasm_type.tobytes())

    if False:
        p = ParsedDisassembly(1000, 0x6000)
        print(p)
        p.parse_test("6502", data)
        print(p.entries)
        e = p.entries.view(dtype=dd.HISTORY_ENTRY_DTYPE)
        # for i in range(len(e)):
        #     print(e[i])
        # print(f"number of entries: {len(e)}")
        # print(hex(len(p.labels)))
        # used_labels = np.where(p.labels != 0)[0]
        # print(used_labels)
        # for index in used_labels:
        #     print(index, p.labels[index])

        num_lines = 100
        for i in range(num_lines):
            print(e[i])
        p.stringify(0, num_lines, False, True)
        for i in range(num_lines):
            start = p.text_starts[i]
            count = p.line_lengths[i]
            text = p.text_buffer[start:start + count].tostring()
            print(f"text[{start}:{start + count}] = {text}, {e[i]}")

    driver = DisassemblyConfig()
    segment.style[:] = 0
    segment.disasm_type[:] = 10
    p = driver.parse(segment, 8000)
    e = p.entries
    print(p)
    print(len(p))
    for i in range(len(p)):
        print(e[i])
    print(p.index_to_row)

    t = p.stringify(0,100)
    print(t)
    for line in t:
        print(line)

    del p
    print("deleted")

if __name__ == "__main__":
    # t = TestNOP()
    # t = TestORA()
    t = TestLabels()
    t.setup()
    t.test_disasm()
