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

import logging
log = logging.getLogger(__name__)

# flags
pcr = 1
und = 2
z80bit = 4
lbl = 8 # subroutine/jump target; candidate for a label
r = 64
w = 128

class DataGenerator(object):
    def __init__(self, formatter_class, hex_lower=True, mnemonic_lower=False, first_of_set=True, **kwargs):
        self.formatter_class = formatter_class
        self.set_case(hex_lower, mnemonic_lower)
        self.setup(**kwargs)
        self.generate(first_of_set)

    def set_case(self, hex_lower, mnemonic_lower):
        self.hex_lower = hex_lower
        self.mnemonic_lower = mnemonic_lower
        self.data_op = ".byte" if mnemonic_lower else ".BYTE"
        self.fmt_op = "$%02x" if hex_lower else "$%02X"

    def setup(self, bytes_per_line=4, **kwargs):
        self.bytes_per_line = bytes_per_line

    def gen_numpy_single_print(self, lines, *args, **kwargs):
        formatter = self.formatter_class(lines)
        formatter.gen_cases(self)
        formatter.end_subroutine()

    def start_formatter(self, lines):
        self.gen_numpy_single_print(lines)

    def generate(self, first_of_set):
        # lines = ["def parse_instruction(pc, src, last_pc):"]
        # lines.append("    opcode = src[0]")
        # lines.append("    print '%04x' % pc,")
        # self.gen_switch(lines, self.opcode_table)
        text = self.formatter_class.preamble
        if "%s" in text:
            c1 = "L" if self.mnemonic_lower else "U"
            c2 = "L" if self.hex_lower else "U"
            suffix = "_%s%s" % (c1, c2)
            print(suffix)
            text = text.replace("%s", suffix)
        if first_of_set:
            text = self.formatter_class.preamble_header + text
        lines = text.splitlines()

        self.start_formatter(lines)

        self.lines = lines

class DisassemblerGenerator(DataGenerator):
    def __init__(self, cpu_name, formatter_class, allow_undocumented=False, hex_lower=True, mnemonic_lower=False, r_mnemonics=None, w_mnemonics=None, rw_modes=None, first_of_set=True):
        self.formatter_class = formatter_class
        self.set_case(hex_lower, mnemonic_lower)
        self.setup(cpu_name, allow_undocumented, r_mnemonics, w_mnemonics, rw_modes)
        self.generate(first_of_set)

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
                log.debug("found z80 multibyte %x, l=%d" % (opcode, leadin_offset))
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
                log.debug("found multibyte %x, l=%d" % (opcode, leadin_offset))
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
                log.debug("z80 4 byte: %x %x" % (leadin, opcode))
                formatter.z80_4byte_intro(opcode)
                self.gen_numpy_single_print(lines, optable, leadin, 2, indent=indent+"    ", z80_2nd_byte=opcode)
                formatter.z80_4byte_outro()
                continue

            if formatter.undocumented and not self.allow_undocumented:
                continue

            log.debug("Processing %x, %s" % (opcode, formatter.fmt))
            if z80_2nd_byte is not None:
                formatter.z80_4byte(z80_2nd_byte, opcode)
                continue

            formatter.process(opcode)

        for leadin, group in multibyte.items():
            formatter.start_multibyte_leadin(leadin)
            log.debug("starting multibyte with leadin %x" % leadin)
            log.debug(group)
            self.gen_numpy_single_print(lines, group, leadin, 1, indent=indent+"    ")

        if not z80_2nd_byte:
            formatter.unknown_opcode()
        formatter.end_subroutine()

    def start_formatter(self, lines):
        self.gen_numpy_single_print(lines, self.opcode_table)


def gen_cpu(cpu, undoc=False, all_case_combos=False):
    if undoc:
        file_root = "udis_fast/hardcoded_parse_%sundoc" % cpu
    else:
        file_root = "udis_fast/hardcoded_parse_%s" % cpu
    print("Generating %s" % file_root)
    for ext, formatter in [("py", PrintNumpy), ("c", RawC)]:
        with open("%s.%s" % (file_root, ext), "w") as fh:
            if all_case_combos:
                first = True
                for mnemonic_lower, hex_lower in [(True, True), (True, False), (False, True), (False, False)]:
                    disasm = DisassemblerGenerator(cpu, formatter, allow_undocumented=undoc, mnemonic_lower=mnemonic_lower, hex_lower=hex_lower, first_of_set=first)
                    fh.write("\n".join(disasm.lines))
                    fh.write("\n")
                    first = False
            else:
                disasm = DisassemblerGenerator(cpu, formatter, allow_undocumented=undoc)
                fh.write("\n".join(disasm.lines))
                fh.write("\n")


def gen_others(all_case_combos=False):
    for name, ext, formatter, generator in [("data", "c", DataC, DataGenerator), ("antic_dl", "c", AnticC, DataGenerator)]:
        file_root = "udis_fast/hardcoded_parse_%s" % name
        print("Generating %s" % file_root)
        with open("%s.%s" % (file_root, ext), "w") as fh:
            if all_case_combos:
                first = True
                for mnemonic_lower, hex_lower in [(True, True), (True, False), (False, True), (False, False)]:
                    disasm = generator(formatter, mnemonic_lower=mnemonic_lower, hex_lower=hex_lower, first_of_set=first)
                    fh.write("\n".join(disasm.lines))
                    fh.write("\n")
                    first = False
            else:
                disasm = generator(formatter)
                fh.write("\n".join(disasm.lines))
                fh.write("\n")

def gen_all(all_case_combos=False):
    for cpu in cputables.processors.keys():
        gen_cpu(cpu, False, all_case_combos)
    gen_cpu("6502", True, all_case_combos)

if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--cpu", help="Specify CPU type (defaults to 6502)", default="")
    parser.add_argument("-u", "--undocumented", help="Allow undocumented opcodes", action="store_true")
    parser.add_argument("-a", "--all-cases", help="Generate 4 separate functions for the lower/upper combinations", action="store_true", default=False)
    args = parser.parse_args()

    if args.cpu is None or args.cpu.lower() == "none":
        pass
    elif args.cpu:
        gen_cpu(args.cpu, args.undocumented, args.all_cases)
    else:
        gen_all(args.all_cases)
    gen_others(args.all_cases)
