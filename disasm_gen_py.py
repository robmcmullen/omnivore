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
            
        self.generate(cpu_name, allow_undocumented, r_mnemonics, w_mnemonics, rw_modes)
    
    def generate(self, cpu_name, allow_undocumented, r_mnemonics, w_mnemonics, rw_modes):
        code = []
        cpu = cputables.processors[cpu_name]
        modes = {}
        table = cpu['addressModeTable']
        if rw_modes is None:
            rw_modes = set()
        for mode, fmt in table.items():
            if self.hex_lower:
                fmt = fmt.replace(":02X", ":02x").replace(":04X", ":04x")
            modes[mode] = fmt
        table = cpu['opcodeTable']

        lines = ["def parse_instruction(pc, src, last_pc):"]
        lines.append("    opcode = src[0]")
        lines.append("    print '%04x' % pc,")
        first = True
        for opcode, optable in table.items():
            try:
                length, mnemonic, mode, flag = optable
            except ValueError:
                length, mnemonic, mode = optable
                flag = 0
            if mode in rw_modes:
                if mnemonic in r_mnemonics:
                    flag |= r
                if mnemonic in w_mnemonics:
                    flag |= w
            if not self.mnemonic_lower:
                mnemonic = mnemonic.upper()

            fmt = modes[mode]
            if first:
                iftext = "if"
            else:
                iftext = "elif"
            lines.append("    %s opcode == 0x%x:" % (iftext, opcode))
            if length == 1:
                lines.append("        count = %d" % length)
                lines.append("        print '%02x __ __ __'," % opcode)
                lines.append("        print 'L0000',")
                lines.append("        print '%s'" % mnemonic)
                if fmt:
                    lines.append("        print '%s'" % fmt)
            elif length == 2:
                lines.append("        count = %d" % length)
                lines.append("        op1 = src[1]")
                lines.append("        print '%02x %%02x __ __' %% op1," % opcode)
                lines.append("        print 'L0000',")
                if fmt:
                    lines.append("        print '%s'," % mnemonic)
                    if flag & pcr:
                        lines.append("        signed = op1 - 256 if op1 > 127 else op1")
                        lines.append("        rel = (pc + 2 + signed) & 0xffff  # limit to 64k address space")
                        lines.append("        print '%s'.format(rel)" % fmt)
                    else:
                        lines.append("        print '%s'.format(op1)" % fmt)
                else:
                    lines.append("        print '%s'" % mnemonic)
            elif length == 3:
                lines.append("        count = %d" % length)
                lines.append("        op1 = src[1]")
                lines.append("        op2 = src[2]")
                lines.append("        print '%02x %%02x %%02x __' %% (op1, op2)," % opcode)
                lines.append("        print 'L0000',")
                lines.append("        print '%s'," % mnemonic)
                if fmt:
                    if flag & pcr:
                        lines.append("        addr = op1 + 256 * op2")
                        lines.append("        signed = addr - 0x10000 if addr > 32768 else addr")
                        lines.append("        rel = (pc + 2 + signed) & 0xffff  # limit to 64k address space")
                    else:
                        lines.append("        print '%s'.format(op1, op2)" % fmt)
            first = False
        lines.append("    else:")
        lines.append("        count = 1")
        lines.append("        print '%02x __ __ __'," % opcode)
        lines.append("        print 'L0000',")
        lines.append("        print '.byte %%02x' % opcode")
        lines.append("    return count")
        
        self.lines = lines



if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--cpu", help="Specify CPU type (defaults to 6502)", default="6502")
    parser.add_argument("-u", "--undocumented", help="Allow undocumented opcodes", action="store_true")
    args = parser.parse_args()

    disasm = DisassemblerGenerator(args.cpu, allow_undocumented=args.undocumented)
    with open("hardcoded_parse_%s.py" % args.cpu, "w") as fh:
        fh.write("\n".join(disasm.lines))
        fh.write("\n")
