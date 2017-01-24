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
# flags
pcr = 1
und = 2
z80bit = 4
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

    def gen_switch(self, lines, table, leadin=0, leadin_offset=0, indent="    "):
        first = True
        multibyte = dict()

        def out(str):
            lines.append(indent + str)

        def op1():
            out("    op1 = src[%d]" % (1 + leadin_offset))

        def op2():
            out("    op2 = src[%d]" % (2 + leadin_offset))

        def op3():
            out("    op3 = src[%d]" % (3 + leadin_offset))

        def bytes1(opcode):
            if leadin_offset == 0:
                out("    print '%02x __ __ __'," % opcode)
            else:
                out("    print '%02x %02x __ __'," % (leadin, opcode))

        def bytes2(opcode):
            if leadin_offset == 0:
                out("    print '%02x %%02x __ __' %% op1," % opcode)
            else:
                out("    print '%02x %02x %%02x __' %% op1," % (leadin, opcode))

        def bytes3(opcode):
            if leadin_offset == 0:
                out("    print '%02x %%02x %%02x __' %% (op1, op2)," % opcode)
            else:
                out("    print '%02x %02x %%02x %%02x' %% (op1, op2)," % (leadin, opcode))

        def bytes4(opcode):
            if leadin_offset == 0:
                out("    print '%02x %%02x %%02x %%02x' %% (op1, op2, op3)," % opcode)
            else: # z80 only
                out("    print '%02x %02x %%02x %%02x' %% (op1, op2)," % (leadin, opcode))

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
            if first:
                iftext = "if"
            else:
                iftext = "elif"
            out("%s opcode == 0x%x:" % (iftext, opcode))
            if length - leadin_offset == 1:
                out("    count = %d" % length)
                bytes1(opcode)
                out("    print 'L0000',")
                if fmt:
                    out("    print '%s %s'" % (mnemonic, fmt))
                else:
                    out("    print '%s'" % mnemonic)
            elif length - leadin_offset == 2:
                out("    count = %d" % length)
                op1()
                bytes2(opcode)
                out("    print 'L0000',")
                if fmt:
                    out("    print '%s'," % mnemonic)
                    if flag & pcr:
                        out("    signed = op1 - 256 if op1 > 127 else op1")
                        out("    rel = (pc + 2 + signed) & 0xffff  # limit to 64k address space")
                        out("    print '%s'.format(rel)" % fmt)
                    else:
                        out("    print '%s'.format(op1)" % fmt)
                else:
                    out("    print '%s'" % mnemonic)
            elif length - leadin_offset == 3:
                out("    count = %d" % length)
                op1()
                op2()
                bytes3(opcode)
                out("    print 'L0000',")
                out("    print '%s'," % mnemonic)
                if fmt:
                    if flag & pcr:
                        out("    addr = op1 + 256 * op2")
                        out("    signed = addr - 0x10000 if addr > 32768 else addr")
                        out("    rel = (pc + 2 + signed) & 0xffff  # limit to 64k address space")
                    else:
                        out("    print '%s'.format(op1, op2)" % fmt)
            elif length == 4:
                out("    count = %d" % length)
                op1()
                op2()
                if flag & z80bit:
                    bytes4(opcode)
                    out("    print 'L0000',")
                    out("    print '%s'," % mnemonic)
                    out("    signed = op1 - 256 if op1 > 127 else op1")
                    out("    print '%s'.format(signed)" % fmt)
                else:
                    op3()
                    bytes4(opcode)
                    out("    print 'L0000',")
                    out("    print '%s'," % mnemonic)
                    out("    print '%s'.format(op1, op2, op3)" % fmt)
            first = False

        for leadin, group in multibyte.items():
            if leadin > 256:
                out("elif (opcode & 0xffff0000) == 0x%x0000:" % (leadin))
                out("    opcode = opcode & 0xff")
            else:
                out("elif (opcode // 256) == 0x%x:" % (leadin))
                out("    opcode = opcode & 0xff")
            print("starting multibyte with leadin %x" % leadin)
            self.gen_switch(lines, group, leadin, 1, indent=indent+"    ")

        out("else:")
        out("    count = 1")
        out("    print '%02x __ __ __' % opcode,")
        out("    print 'L0000',")
        out("    print '.byte $%02x' % opcode")
        out("return count")

    def generate(self):
        lines = ["def parse_instruction(pc, src, last_pc):"]
        lines.append("    opcode = src[0]")
        lines.append("    print '%04x' % pc,")
        self.gen_switch(lines, self.opcode_table)
        
        self.lines = lines

def gen_cpu(cpu, undoc=False):
    disasm = DisassemblerGenerator(cpu, allow_undocumented=undoc)
    with open("hardcoded_parse_%s.py" % cpu, "w") as fh:
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
