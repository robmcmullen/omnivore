#!/usr/bin/env python
import sys
import ctypes
import time

import numpy as np

from atrcopy import DefaultSegment

from omnivore.disassembler import DisassemblyConfig


if __name__ == "__main__":
    if len(sys.argv) > 1:
        pathname = sys.argv[1]
    else:
        pathname = "testrts.bin"
    print(f"Booting from {pathname}")
    data = np.fromfile(pathname, dtype=np.uint8)

    driver = DisassemblyConfig()
    driver.register_parser("6502", 0)
    driver.register_parser("data", 1)
    driver.register_parser("antic_dl", 2)
    driver.register_parser("jumpman_level", 3)
    driver.register_parser("jumpman_harvest", 4)

    segment = DefaultSegment(data)
    current = driver.parse(segment, 1000)
    parsed = current.stringify(0, 512)

    for text in parsed:
        print(text)
