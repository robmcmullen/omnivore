#!/usr/bin/env python
import sys
import ctypes
import time

import numpy as np

from atrip import Container, Segment

import omnivore.disassembler.dtypes as ud
from omnivore.disassembler import ParsedDisassembly, DisassemblyConfig


nops = np.zeros(256, dtype=np.uint8) + 0xea

repeat_test = np.asarray([1,1,1,1,1,1,1,0, 0,0,0,0,0,0,0,0, 0,1,1,1,1,1,0,0, 0,0,0,0,0,0,0,0, 0,0,0,0,0,0,0,0], dtype=np.uint8)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'rb') as fh:
            data = np.frombuffer(fh.read(), dtype=np.uint8)
            data = data.astype(dtype=np.uint8)  # prevents data.base from being a 'bytes' object
    else:
        data = repeat_test
    print("raw data: ", type(data), data)
    d2 = Container(data)
    segment = Segment(d2, origin=0x6000)
    print("data", segment.data, segment.data.tobytes())
    print("style", segment.style, segment.style.tobytes())
    print("disasm_type", segment.disasm_type, segment.disasm_type.tobytes())

    if False:
        p = ParsedDisassembly(1000, 0x6000)
        print(p)
        p.parse_test("6502", data)
        print(p.entries)
        e = p.entries.view(dtype=ud.HISTORY_ENTRY_DTYPE)
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
