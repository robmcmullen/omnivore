#!/usr/bin/env python
""" Mini-assembler that uses the formatting strings and opcode tables from
udis (the Universal Disassembler for 8-bit microprocessors by Jeff Tranter) to
perform pattern matching to determine the opcode and addressing mode.

Copyright (c) 2016 by Rob McMullen <feedback@playermissile.com>
Licensed under the Apache License 2.0
"""


import os
import re
from collections import defaultdict

import numpy as np

import logging
logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)

from omnivore.disassembler.miniasm import process



if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--cpu", help="Specify CPU type (defaults to 6502)", default="6502")
    parser.add_argument("-d", "--debug", help="Show debug information as the program runs", action="store_true")
    parser.add_argument("-v", "--verbose", help="Show processed instructions as the program runs", action="store_true")
    parser.add_argument("-x", "--hex", help="Assemble a string version of hex digits")
    parser.add_argument("-s", "--string", help="Assemble a single line opcode (implies -a)")
    parser.add_argument("-p", "--pc", help="Process counter", default="0")
    args, extra = parser.parse_known_args()
    
    if args.debug:
        log.setLevel(logging.DEBUG)
    
    try:
        start_pc = int(args.pc, 16)
    except ValueError:
        start_pc = int(args.pc)
    

    if args.string:
        source = args.string
        args.assemble = True
        process(args.cpu, args.string, start_pc)
    # elif args.hex:
    #     try:
    #         source = args.hex.decode("hex")
    #     except TypeError:
    #         print("Invalid hex digits!")
    #         sys.exit()
    #     process(source, args.string, start_pc, args.cpu, args.assemble, args.verbose)
    else:
        for filename in extra:
            source = []
            with open(filename, 'rb') if filename !="-" else sys.stdin as fh:
                try:
                    chunk_length = 1024
                    while True:
                        chunk = fh.read(chunk_length)
                        source.append(chunk)
                        if len(chunk) < chunk_length:
                            break
                except KeyboardInterrupt:
                    pass
            source = "".join(source)
            if args.verbose:
                print(f"read {len(source)} bytes")
            for line in source.splitlines():
                values = process(args.cpu, line, pc)
                print(f"{line}: {values}")
                pc += len(values)

