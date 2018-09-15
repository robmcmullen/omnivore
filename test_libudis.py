#!/usr/bin/env python
import sys
import ctypes
import time

import numpy as np

from atrcopy import find_diskimage, DefaultSegment, SegmentData

import omni8bit.udis_fast.dtypes as ud
from omni8bit.udis_fast import libudis


nops = np.zeros(256, dtype=np.uint8) + 0xea


if __name__ == "__main__":
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'rb') as fh:
            data = np.frombuffer(fh.read(), dtype=np.uint8)
            data = data.astype(dtype=np.uint8)  # prevents data.base from being a 'bytes' object
    else:
        data = nops
    print(type(data), data)
    d2 = SegmentData(data)
    segment = DefaultSegment(d2, 0x6000)

    if False:
        p = libudis.ParsedDisassembly(1000, 0x6000)
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

    driver = libudis.DisassemblyConfig()
    driver.register_parser("6502", 0)
    driver.register_parser("data", 1)
    driver.register_parser("antic_dl", 2)
    driver.register_parser("jumpman_level", 3)
    driver.register_parser("jumpman_harvest", 4)
    segment.style[20:40] = 2
    segment.style[40:80] = 3
    segment.style[80:100] = 4
    p = driver.parse(segment, 8000)
    e = p.entries.view(dtype=ud.HISTORY_ENTRY_DTYPE)
    print(p)
    print(len(p))
    for i in range(len(p)):
        print(e[i])

    t = p.stringify(100,100)
    print(t)
    for i in range(len(t)):
        start = t.text_starts[i]
        count = t.line_lengths[i]
        text = t.text_buffer[start:start + count].tostring()
        print(f"text[{start}:{start + count}] = {text}, {e[i+100]}")

    del p
    print("deleted")
