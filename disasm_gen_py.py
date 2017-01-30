#!/usr/bin/env python
""" Python code generator for a hardcoded disassembler based on the udis
universal disassembler

This is mostly a toy generator in that it generates really inefficient code. It
is research for a future version that will output C code.

Code generator: Copyright (c) 2017 by Rob McMullen <feedback@playermissile.com>

udis: Copyright (c) 2015-2016 Jeff Tranter
Licensed under the Apache License 2.0
"""
from __future__ import print_function

import os
import glob

import numpy as np

import cputables

from disasm_gen_utils import *

# flags
pcr = 1
und = 2
z80bit = 4
lbl = 8 # subroutine/jump target; candidate for a label
r = 64
w = 128

class DisassemblerGenerator(object):
    def __init__(self, cpu_name, formatter_class, asm_syntax=None, memory_map=None, allow_undocumented=False, hex_lower=True, mnemonic_lower=False, r_mnemonics=None, w_mnemonics=None, rw_modes=None):
        self.formatter_class = formatter_class
        self.memory_map = memory_map
        if asm_syntax is None:
            asm_syntax = {
                'comment char': ';',
                'origin': '.org',
                'data byte': '.db',
             }
        self.hex_lower = hex_lower
        self.mnemonic_lower = mnemonic_lower
        if mnemonic_lower:
            case_func = lambda a:a.lower()
        else:
            case_func = lambda a:a.upper()
        self.data_byte_opcode = case_func(asm_syntax['data byte'])
        self.asm_origin = case_func(asm_syntax['origin'])
        self.comment_char = case_func(asm_syntax['comment char'])
        
        self.setup(cpu_name, allow_undocumented, r_mnemonics, w_mnemonics, rw_modes)
        self.generate()

    def setup(self, cpu_name, allow_undocumented, r_mnemonics, w_mnemonics, rw_modes):
        self.r_mnemonics = r_mnemonics
        self.w_mnemonics = w_mnemonics
        self.allow_undocumented = allow_undocumented
        self.rw_modes = rw_modes
        self.cpu_name = cpu_name

        cpu = cputables.processors[cpu_name]
        self.address_modes = {}
        table = cpu['addressModeTable']
        if self.rw_modes is None:
            self.rw_modes = set()
        for mode, fmt in table.items():
            if self.hex_lower:
                fmt = fmt.replace(":02X", ":02x").replace(":04X", ":04x")
            self.address_modes[mode] = fmt
        self.opcode_table = cpu['opcodeTable']

    def gen_numpy_single_print(self, lines, table, leadin=0, leadin_offset=0, indent="    ", z80_2nd_byte=None):
        """Store in numpy array of strings:

        0000 00 00 00 00       lda #$30
                         ^^^^^ space for a 5 character label, to be placed later
        """
        formatter = self.formatter_class(lines, indent, leadin, leadin_offset)
        multibyte = dict()

        for opcode, optable in table.items():
            if opcode > 65536:
                print("found z80 multibyte %x, l=%d" % (opcode, leadin_offset))
                leadin = opcode >> 24
                second_byte = (opcode >> 16) & 0xff
                if leadin not in multibyte:
                    multibyte[leadin] = dict()
                if second_byte not in multibyte[leadin]:
                    multibyte[leadin][second_byte] = dict()
                fourth_byte = opcode & 0xff
                multibyte[leadin][second_byte][fourth_byte] = optable
                continue
            elif opcode > 255:
                try:
                    length, mnemonic, mode, flag = optable
                    # check for placeholder z80 instructions & ignore them the
                    # real instructions for ddcb and fdcb will have 4 byte
                    # opcodes
                    if flag & z80bit and (opcode == 0xddcb or opcode == 0xfdcb):
                        continue
                except ValueError:
                    # no flag, can't have the z80bit set, so it's a valid
                    # opcode
                    pass
                print("found multibyte %x, l=%d" % (opcode, leadin_offset))
                leadin = opcode // 256
                opcode = opcode & 0xff
                if leadin not in multibyte:
                    multibyte[leadin] = dict()
                multibyte[leadin][opcode] = optable
                continue
            try:
                formatter.set_current(optable, self)
            except ValueError:
                # process z80 4-byte commands
                print("z80 4 byte: %x %x" % (leadin, opcode))
                formatter.z80_4byte_intro(opcode)
                self.gen_numpy_single_print(lines, optable, leadin, 2, indent=indent+"    ", z80_2nd_byte=opcode)
                formatter.z80_4byte_outro()
                continue

            if formatter.undocumented and not self.allow_undocumented:
                continue

            print("Processing %x, %s" % (opcode, formatter.fmt))
            if z80_2nd_byte is not None:
                formatter.z80_4byte(z80_2nd_byte, opcode)
                continue

            formatter.process(opcode)

        for leadin, group in multibyte.items():
            formatter.start_multibyte_leadin(leadin)
            print("starting multibyte with leadin %x" % leadin)
            print(group)
            self.gen_numpy_single_print(lines, group, leadin, 1, indent=indent+"    ")

        if not z80_2nd_byte:
            formatter.unknown_opcode()
        formatter.end_subroutine()

    def generate(self):
        # lines = ["def parse_instruction(pc, src, last_pc):"]
        # lines.append("    opcode = src[0]")
        # lines.append("    print '%04x' % pc,")
        # self.gen_switch(lines, self.opcode_table)
        lines = self.formatter_class.preamble.splitlines()
        self.gen_numpy_single_print(lines, self.opcode_table)

        self.lines = lines


def gen_cpu(cpu, undoc=False):
    if undoc:
        file_root = "hardcoded_parse_%sundoc" % cpu
    else:
        file_root = "hardcoded_parse_%s" % cpu
    disasm = DisassemblerGenerator(cpu, PrintNumpy, allow_undocumented=undoc)
    with open("%s.py" % file_root, "w") as fh:
        fh.write("\n".join(disasm.lines))
        fh.write("\n")
    disasm = DisassemblerGenerator(cpu, PrintC, allow_undocumented=undoc)
    with open("%s.c" % file_root, "w") as fh:
        fh.write("\n".join(disasm.lines))
        fh.write("\n")

def gen_all():
    for cpu in cputables.processors.keys():
        gen_cpu(cpu)
    gen_cpu("6502", True)

if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--cpu", help="Specify CPU type (defaults to 6502)", default="")
    parser.add_argument("-u", "--undocumented", help="Allow undocumented opcodes", action="store_true")
    args = parser.parse_args()

    if args.cpu:
        gen_cpu(args.cpu)
    else:
        gen_all()
