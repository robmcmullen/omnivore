#!/usr/bin/env python
import sys
import ctypes
import time

import numpy as np

from atrip.container import Container
from atrip.segment import Segment

from omnivore.emulators.libemu import Disassembler


def show_op_history(ops):
    print(f"malloc size: {int(ops[0])}")
    print(f"frame number: {int(ops[1])}")
    print(f"records: max={int(ops[2])}, count={int(ops[3])}")
    print(f"line lookup: max={int(ops[4])}, count={int(ops[5])}")
    print(f"byte lookup: max={int(ops[6])}, count={int(ops[7])}")
    for i in range(30):
        line = ops[8 + ops[2] + i]
        next_line = ops[8 + ops[2] + i + 1]
        print(f"{i:4}: {line:5}", end="")
        for j in range(line, next_line):
            print(f" {int(ops[8 + j]):08x}", end="")
        print()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        pathname = sys.argv[1]
    else:
        pathname = "samples/air_defense_v18.xex"
    print(f"Booting from {pathname}")
    data = np.fromfile(pathname, dtype=np.uint8)
    container = Container(data)
    segment = Segment(container)
    segment.disasm_type[:12] = 0
    segment.disasm_type[12:] = 10
    print(segment.data[0:16])
 
    driver = Disassembler()

    driver.parse(segment, 100)
    show_op_history(driver.op_history)
