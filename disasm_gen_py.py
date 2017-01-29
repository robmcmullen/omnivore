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
    def __init__(self, cpu_name, asm_syntax=None, memory_map=None, allow_undocumented=False, hex_lower=True, mnemonic_lower=False, r_mnemonics=None, w_mnemonics=None, rw_modes=None):
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

    def gen_numpy_single_print(self, lines, table, leadin=0, leadin_offset=0, indent="    ", z80_2nd_byte=None, formatter_class=None):
        """Store in numpy array of strings:

        0000 00 00 00 00       lda #$30
                         ^^^^^ space for a 5 character label, to be placed later
        """
        formatter = formatter_class(lines, indent, leadin, leadin_offset)
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
                self.gen_numpy_single_print(lines, optable, leadin, 2, indent=indent+"    ", z80_2nd_byte=opcode, formatter_class=formatter_class)

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
            self.gen_numpy_single_print(lines, group, leadin, 1, indent=indent+"    ", formatter_class=formatter_class)

        if not z80_2nd_byte:
            formatter.unknown_opcode()
        formatter.end_subroutine()

    def generate(self):
        # lines = ["def parse_instruction(pc, src, last_pc):"]
        # lines.append("    opcode = src[0]")
        # lines.append("    print '%04x' % pc,")
        # self.gen_switch(lines, self.opcode_table)
        preamble = """
def put_bytes(str, loc, dest):
    for a in str:
        dest[loc] = ord(a)
        loc += 1

def parse_instruction_numpy(wrap, pc, src, last_pc):
    opcode = src[0]
    put_bytes('%04x' % pc, 0, wrap)
"""
        lines = preamble.splitlines()
        self.gen_numpy_single_print(lines, self.opcode_table, formatter_class=PrintNumpy)

        self.lines = lines

class CDisassemblerGenerator(DisassemblerGenerator):
    def gen_c(self, lines, table, leadin=0, leadin_offset=0, indent="    "):
        """Store in numpy array of strings:

        0000 00 00 00 00       lda #$30
                         ^^^^^ space for a 5 character label, to be placed later
        """
        first = True
        multibyte = dict()
        byte_loc = 5
        label_loc = 17
        op_loc = 23

        def out(s):
            if not s.endswith(":") and not s.endswith("{") and not s.endswith("}"):
                s += ";"
            lines.append(indent + s)

        def op1():
            out("    op1 = *src++")

        def op2():
            out("    op2 = *src++")

        def op3():
            out("    op3 = *src++")

        def bytes1(opcode):
            if leadin_offset == 0:
                return "%02x __ __ __" % opcode, []
            else:
                return "%02x %02x __ __" % (leadin, opcode), []

        def bytes2(opcode):
            if leadin_offset == 0:
                return "%02x %%02x __ __" % (opcode), ["op1"]
            else:
                return "%02x %02x %%02x __" % (leadin, opcode), ["op1"]

        def bytes3(opcode):
            if leadin_offset == 0:
                return "%02x %%02x %%02x __" % (opcode), ["op1", "op2"]
            else:
                return "%02x %02x %%02x %%02x" % (leadin, opcode), ["op1", "op2"]

        def bytes4(opcode):
            return "%02x %%02x %%02x %%02x" % (leadin, opcode), ["op1", "op2", "op3"]

        out("switch(opcode) {")
        for opcode, optable in table.items():
            if opcode > 65536:
                print("found z80 multibyte %x, l=%d" % (opcode, leadin_offset))
                leadin = opcode >> 16
                opcode = opcode & 0xff
                if leadin not in multibyte:
                    multibyte[leadin] = dict()
                multibyte[leadin][opcode] = optable
                continue
            elif opcode > 255:
                print("found multibyte %x, l=%d" % (opcode, leadin_offset))
                leadin = opcode // 256
                opcode = opcode & 0xff
                if leadin not in multibyte:
                    multibyte[leadin] = dict()
                multibyte[leadin][opcode] = optable
                continue
            try:
                length, mnemonic, mode, flag = optable
            except ValueError:
                length, mnemonic, mode = optable
                flag = 0
            if flag & und and not self.allow_undocumented:
                continue
            if mode in self.rw_modes:
                if mnemonic in self.r_mnemonics:
                    flag |= r
                if mnemonic in self.w_mnemonics:
                    flag |= w
            if not self.mnemonic_lower:
                mnemonic = mnemonic.upper()

            fmt = self.address_modes[mode]
            print("Processing %x, %s" % (opcode, fmt))
            fmt, argorder = convert_fmt(fmt)
            out("case 0x%x:" % (opcode))
            if length - leadin_offset == 1:
                out("    count = %d" % length)
                bstr, bvars = bytes1(opcode)
                if not fmt:
                    fmt = ""
                if bvars:
                    bvars.extend(argorder) # should be null operation; 1 byte length opcodes shouldn't have any arguments
                    outstr = "\"%s       %s %s\", %s" % (bstr, mnemonic, fmt, bvars)
                else:
                    outstr = "\"%s       %s %s\"" % (bstr, mnemonic, fmt)
                out("    sprintf(wrap, %s)" % outstr)
            elif length - leadin_offset == 2:
                out("    count = %d" % length)
                out("    if (pc + count >= last_pc) return 0")
                op1()
                bstr, bvars = bytes2(opcode)
                if fmt:
                    if flag & pcr:
                        out("    if (op1 > 127) dist = op1 - 256; else dist = op1")
                        # limit relative branch to 64k address space
                        out("    rel = (pc + 2 + dist) & 0xffff")
                        out("    labels[rel] = 1")
                if bvars:
                    bvars.extend(argorder)
                    outstr = "\"%s       %s %s\", %s" % (bstr, mnemonic, fmt, ", ".join(bvars))
                else:
                    outstr = "\"%s       %s %s\"" % (bstr, mnemonic, fmt)
                out("    sprintf(wrap, %s)" % outstr)
            elif length - leadin_offset == 3:
                out("    count = %d" % length)
                out("    if (pc + count >= last_pc) return 0")
                op1()
                op2()
                bstr, bvars = bytes3(opcode)
                if fmt:
                    if flag & pcr:
                        out("    addr = op1 + 256 * op2")
                        out("    if (addr > 32768) addr -= 0x10000")
                        # limit relative branch to 64k address space
                        out("    rel = (pc + 2 + addr) & 0xffff")
                        out("    labels[rel] = 1")
                    elif flag & lbl:
                        out("    addr = op1 + 256 * op2")
                        out("    labels[addr] = 1")
                if bvars:
                    bvars.extend(argorder)
                    outstr = "\"%s       %s %s\", %s" % (bstr, mnemonic, fmt, ", ".join(bvars))
                else:
                    outstr = "\"%s       %s %s\"" % (bstr, mnemonic, fmt)
                out("    sprintf(wrap, %s)" % outstr)
            elif length == 4:
                out("    count = %d" % length)
                out("    if (pc + count >= last_pc) return 0")
                op1()
                op2()
                bstr, bvars = bytes4(opcode)
                if flag & z80bit:
                    out("    if (op1 > 127) dist = op1 - 256; else dist = op1")
                    bvars.append("dist")
                else:
                    op3()
                outstr = "\"%s       %s %s\", %s" % (bstr, mnemonic, fmt, ", ".join(bvars))
                out("    sprintf(wrap, %s)" % outstr)
            out("    break")

        for leadin, group in multibyte.items():
            if leadin > 256:
                out("elif (opcode & 0xffff0000) == 0x%x0000:" % (leadin))
                out("    opcode = opcode & 0xff")
            else:
                out("elif (opcode // 256) == 0x%x:" % (leadin))
                out("    opcode = opcode & 0xff")
            print("starting multibyte with leadin %x" % leadin)
            self.gen_c(lines, group, leadin, 1, indent=indent+"    ")

        out("default:")
        out("    count = 1")
        bstr = "%02x __ __ __"
        bvars = ["opcode", "opcode"]
        mnemonic = ".byte"
        fmt = "%02x"
        outstr = "\"%s       %s %s\", %s" % (bstr, mnemonic, fmt, ", ".join(bvars))
        out("    sprintf(wrap, %s)" % outstr)
        out("    break")
        out("}")
        out("return count")
        lines.append("}")

    def generate(self):
        # lines = ["def parse_instruction(pc, src, last_pc):"]
        # lines.append("    opcode = src[0]")
        # lines.append("    print '%04x' % pc,")
        # self.gen_switch(lines, self.opcode_table)
        preamble = """
#include <stdio.h>

int parse_instruction_c(unsigned char *wrap, unsigned int pc, unsigned char *src, unsigned int last_pc, unsigned short *labels) {
    int count, rel, dist;
    short addr;
    unsigned char opcode, op1, op2, op3;

    opcode = *src++;
    sprintf(wrap, "%04x " , pc);
    wrap += 5;
"""
        lines = preamble.splitlines()
        self.gen_c(lines, self.opcode_table)

        self.lines = lines


def gen_cpu(cpu, undoc=False):
    disasm = DisassemblerGenerator(cpu, allow_undocumented=undoc)
    with open("hardcoded_parse_%s.py" % cpu, "w") as fh:
        fh.write("\n".join(disasm.lines))
        fh.write("\n")
    disasm = CDisassemblerGenerator(cpu, allow_undocumented=undoc)
    with open("hardcoded_parse_%s.c" % cpu, "w") as fh:
        fh.write("\n".join(disasm.lines))
        fh.write("\n")


if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--cpu", help="Specify CPU type (defaults to 6502)", default="6502")
    parser.add_argument("-u", "--undocumented", help="Allow undocumented opcodes", action="store_true")
    args = parser.parse_args()

    gen_cpu(args.cpu)
