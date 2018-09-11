#!/usr/bin/env python
""" Python code generator for a hardcoded disassembler based on the udis
universal disassembler

This is mostly a toy generator in that it generates really inefficient code. It
is research for a future version that will output C code.

Code generator: Copyright (c) 2017 by Rob McMullen <feedback@playermissile.com>

udis: Copyright (c) 2015-2016 Jeff Tranter
Licensed under the Apache License 2.0
"""


import os
import glob
from collections import defaultdict, namedtuple

import numpy as np

import sys
sys.path[0:0] = [os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))]

# mnemonic flags
from omni8bit.udis_fast.flags import und, z80bit, lbl, pcr

import logging
log = logging.getLogger(__name__)

from omni8bit.udis_fast.flags import *
from omni8bit.udis_fast import cputables

# This is declared here so that CPUs will have consistent types for backward
# compatibility. Do not reuse ID numbers if CPUs are removed from this list.
disassembler_type = {
    "data": 0,
    "6502": 10,
    "6502undoc": 11,
    "65816": 12,
    "65c02": 13,
    "6800": 14,
    "6809": 15,
    "6811": 16,
    "8051": 17,
    "8080": 18,
    "z80": 19,
    "antic_dl": 30,
    "jumpman_harvest": 31,
    "jumpman_level": 32,
}
disassembler_type_max = max(disassembler_type.values())


disclaimer = """Warning! This is generated code.

Any edits will be overwritten with the next call to disasm_gen.py
"""
c_disclaimer = "/***************************************************************\n%s***************************************************************/\n\n\n" % disclaimer
py_disclaimer = "\n".join("# %s" % line for line in disclaimer.splitlines()) + "\n\n"



class UnimplementedZ80Opcode(RuntimeError):
    pass


def convert_fmt(fmt):
    fmt = fmt.lower()
    if "{0:02x}" in fmt and "{1:02x}" and "{2:02x}" in fmt:
        # determine order of args by which comes first in the format string
        indexes = [
            (fmt.index("{0:02x}"), "op1"),
            (fmt.index("{1:02x}"), "op2"),
            (fmt.index("{2:02x}"), "op3"),
            ]
        indexes.sort()
        argorder = [i[1] for i in indexes]
        fmt = fmt.replace("{0:02x}", "%02x").replace("{1:02x}", "%02x").replace("{2:02x}", "%02x")
    elif "{0:02x}" in fmt and "{1:02x}" in fmt:
        # determine order of args by which comes first in the format string
        i0 = fmt.index("{0:02x}")
        i1 = fmt.index("{1:02x}")
        if i0 < i1:
            argorder = ["op1", "op2"]
        else:
            argorder = ["op2", "op1"]
        fmt = fmt.replace("{0:02x}", "%02x").replace("{1:02x}", "%02x")
    elif "{0:02x}" in fmt:
        fmt = fmt.replace("{0:02x}", "%02x")
        argorder = ["op1"]
    elif "{0:04x}" in fmt:
        fmt = fmt.replace("{0:04x}", "%04x")
        argorder = ["rel"]
    else:
        argorder = []
    return fmt, argorder


ParserCategory = namedtuple('ParserCategory', ['length', 'mode', 'leadin', 'undoc', 'pcr', 'target_addr', 'operation_type'])


class Opcode:
    def __init__(self, opcode, optable_entry):
        self.leadin = None
        self.opcode = opcode
        self.fourth_byte = None
        self.leadin_offset = 0
        self.length, self.mnemonic, self.mode, self.flag = optable_entry
        if opcode > 65536:
            self.leadin = opcode >> 16
            self.fourth_byte = opcode & 0xff
            self.leadin_offset = 2
            log.debug("found z80 multibyte %x, l=%d" % (opcode, self.leadin_offset))
        elif opcode > 255:
            # check for placeholder z80 instructions & ignore them the
            # real instructions for ddcb and fdcb will have 4 byte
            # opcodes
            if self.flag & z80bit and (opcode == 0xddcb or opcode == 0xfdcb):
                raise UnimplementedZ80Opcode(f"{hex(opcode)} is a placeholder")
            self.leadin_offset = 1
            log.debug("found multibyte %x, l=%d" % (opcode, self.leadin_offset))
            self.leadin = opcode // 256
            self.opcode = opcode & 0xff
        else:
            self.leadin_offset = 0

    def __str__(self):
        return f"{self.mnemonic}: {hex(self.opcode)} {self.length} {self.mode}"

    def __repr__(self):
        return f"{self.mnemonic}: {hex(self.opcode)}"

    @property
    def undoc(self):
        return bool(self.flag & und)

    @property
    def target_addr(self):
        return bool(self.flag & lbl)

    @property
    def pcr(self):
        return bool(self.flag & pcr)

    @property
    def operation_type(self):
        return "FLAG_BRANCH" if self.pcr else ""

    @property
    def parser_category(self):
        return ParserCategory(self.length, self.mode, self.leadin, self.undoc, self.pcr, self.target_addr, self.operation_type)


class CPU:
    def __init__(self, cpu):
        self.cpu = cpu
        self.disassembler_type = disassembler_type[cpu]
        self.disassembler_type_name = f"DISASM_{cpu}".upper()
        c = cputables.processors[cpu]
        self.address_modes = {}
        self.argorder = {}
        table = c['addressModeTable']
        for mode, fmt in list(table.items()):
            fmt = fmt.replace(":02X", ":02x").replace(":04X", ":04x")
            fmt, argorder = convert_fmt(fmt)
            self.address_modes[mode] = fmt
            self.argorder[mode] = argorder
            if "'" in fmt:
                print(f"WARNING in {self.cpu}! ' char in {fmt}")
        self.opcode_table = c['opcodeTable']
        self.opcodes = []
        self.leadin_opcodes = defaultdict(list)
        self.gen_opcodes()
        self.gen_stringifier()

    def __str__(self):
        return f"{self.cpu}: {len(self.opcodes)} opcodes, {len(self.leadin_opcodes)} leadin opcodes {tuple([hex(a) for a in self.leadin_opcodes.keys()])}"

    def gen_opcodes(self):
        for value, optable in list(self.opcode_table.items()):
            try:
                opcode = Opcode(value, optable)
            except UnimplementedZ80Opcode:
                continue
            print(opcode, self.address_modes[opcode.mode], self.argorder[opcode.mode])
            if opcode.leadin is not None:
                self.leadin_opcodes[opcode.leadin].append(opcode)
            else:
                self.opcodes.append(opcode)

    def gen_parser_combos(self, opcodes):
        combos = defaultdict(list)
        for opcode in opcodes:
            cat = opcode.parser_category
            combos[cat].append(opcode)
        for cat, opcodes in combos.items():
            print(f"category {cat}: opcodes:{opcodes}")
        return combos

    def gen_stringifier(self):
        pass


class HistoryParserC:
    escape_strings = False

    template = """
int history_parse_entry_c_%s(history_entry_t *entry, unsigned char *src, unsigned int pc, unsigned int last_pc, unsigned short *labels) {
	int dist;
	unsigned int rel;
	unsigned short addr;
	unsigned char opcode, leadin, op1, op2, op3;
	
	opcode = *src++;
	entry->instruction[0] = opcode;
	entry->pc = (unsigned short)pc;
	entry->target_addr = 0;
	switch(opcode) {
$CASES
	default:
		goto truncated;
	}
	return entry->num_bytes;
truncated:
	entry->num_bytes = 1;
truncated2:
	entry->flag = 0;
	entry->disassembler_type = DISASM_DATA;
	return entry->num_bytes;
}
"""

    leadin_template = """
	case 0x%x:
		opcode = *src++;
		entry->instruction[1] = opcode;
		switch(opcode) {
%s
		default:
			entry->num_bytes = 2;
			goto truncated2;
		}
		break;
"""

    def __init__(self, cpu):
        self.cpu = cpu
        self.cases = self.create_cases()

    @property
    def text(self):
        text = (self.template % self.cpu.cpu).replace("$CASES", "\n".join(self.cases))
        return text

    def create_cases(self):
        cases = []
        for cat, opcodes in self.cpu.gen_parser_combos(cpu.opcodes).items():
            print(f"{self.cpu}: {cat}, opcodes:{opcodes}")
            case = self.gen_case(cat, opcodes, "\t")
            cases.append(case)

        for leadin, leadin_opcodes in self.cpu.leadin_opcodes.items():
            subcases = []
            for cat, opcodes in self.cpu.gen_parser_combos(leadin_opcodes).items():
                subcase = self.gen_case(cat, opcodes, "\t\t")
                subcases.append(subcase)
            case = self.leadin_template % (leadin, "\n".join(subcases))
            cases.append(case)

        #print("\n".join(cases))
        return cases

    def gen_case(self, cat, opcodes, extra_indent=""):
        case = []
        case.append(f"/* {cat.mode} {'(undocumented) ' if cat.undoc else ''}*/")
        for op in opcodes:
            case.append(f"case {hex(op.opcode)}: /* {op.mnemonic} {self.cpu.address_modes[cat.mode]} */")
        case.append(f"\tentry->num_bytes = {cat.length};")
        case.extend(self.create_category(cat))
        flags = []
        if cat.operation_type:
            flags.append(cat.operation_type)
        if cat.undoc:
            flags.append("FLAG_UNDOC")
        if cat.target_addr:
            flags.append("FLAG_TARGET_ADDR")
        if flags:
            case.append(f"\tentry->flag = {' | '.join(flags)};")
        case.append(f"\tentry->disassembler_type = {self.cpu.disassembler_type_name};")
        case.append("\tbreak;")
        text = "\n".join([extra_indent + line for line in case]) + "\n"
        print(text)
        return text


    def create_category(self, cat):
        body = []
        if cat.length == 1:
            pass # nothing extra to add to length and disassembler type
        else:
            body.append(f"\tif (pc + {cat.length} > last_pc) goto truncated;")
            if cat.length == 2:
                if cat.leadin is None:
                    if cat.pcr:
                        body.append(f"\top1 = *src;")
                        body.append(f"\tentry->instruction[1] = op1;")
                        body.append(f"\tif (op1 > 127) dist = op1 - 256; else dist = op1;")
                        body.append(f"\trel = (pc + 2 + dist) & 0xffff;")
                        body.append(f"\tlabels[rel] = 1;")
                        body.append(f"\tentry->target_addr = rel;")
                    elif cat.target_addr:
                        body.append(f"\top1 = *src;")
                        body.append(f"\tentry->instruction[1] = op1;")
                        body.append(f"\tlabels[op1] = 1;")
                        body.append(f"\tentry->target_addr = op1;")
                    else:
                        body.append(f"\tentry->instruction[1] = *src;")
                else:
                    pass
            elif cat.length == 3:
                if cat.leadin is None:
                    order = self.cpu.argorder[cat.mode]
                    print(f"\t/* {order} */")
                    body.append(f"\top1 = *src++;")
                    body.append(f"\tentry->instruction[1] = op1;")
                    body.append(f"\top2 = *src;")
                    body.append(f"\tentry->instruction[2] = op2;")
                    if cat.target_addr:
                        body.append(f"\taddr = (256 * {order[0]}) + {order[1]};")
                        body.append(f"\tlabels[addr] = 1;")
                        body.append(f"\tentry->target_addr = addr;")
                elif cat.leadin < 256:
                    if cat.pcr:
                        body.append(f"\top1 = *src;")
                        body.append(f"\tentry->instruction[2] = op1;")
                        body.append(f"\tif (op1 > 127) dist = op1 - 256; else dist = op1;")
                        body.append(f"\trel = (pc + 2 + dist) & 0xffff;")
                        body.append(f"\tlabels[rel] = 1;")
                        body.append(f"\tentry->target_addr = rel;")
                    elif cat.target_addr:
                        body.append(f"\top1 = *src;")
                        body.append(f"\tentry->instruction[2] = op1;")
                        body.append(f"\tlabels[op1] = 1;")
                        body.append(f"\tentry->target_addr = op1;")
                    else:
                        body.append(f"\tentry->instruction[2] = *src;")
            elif cat.length == 4:
                if cat.leadin is None:
                    order = self.cpu.argorder[cat.mode]
                    print(f"\t/* {order} */")
                    body.append(f"\top1 = *src++;")
                    body.append(f"\tentry->instruction[1] = op1;")
                    body.append(f"\top2 = *src;")
                    body.append(f"\tentry->instruction[2] = op2;")
                    body.append(f"\top3 = *src;")
                    body.append(f"\tentry->instruction[3] = op3;")
                    if cat.target_addr:
                        body.append(f"\taddr = (256 * {order[0]}) + {order[1]};")
                        body.append(f"\tlabels[addr] = 1;")
                        body.append(f"\tentry->target_addr = addr;")
                elif cat.leadin < 256:
                    order = self.cpu.argorder[cat.mode]
                    print(f"\t/* {order} */", cat)
                    body.append(f"\top1 = *src++;")
                    body.append(f"\tentry->instruction[2] = op1;")
                    body.append(f"\top2 = *src;")
                    body.append(f"\tentry->instruction[3] = op2;")
                    if cat.target_addr:
                        body.append(f"\taddr = (256 * {order[0]}) + {order[1]};")
                        body.append(f"\tlabels[addr] = 1;")
                        body.append(f"\tentry->target_addr = addr;")

        return body



if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--cpu", help="Specify CPU type (defaults to 6502)", default="")
    parser.add_argument("-d", "--dev", help="Build for development testing", action="store_true", default=False)
    parser.add_argument("-p", "--py", help="Also create python code", action="store_true", default=False)
    parser.add_argument("-a", "--all-cases", help="Generate 4 separate functions for the lower/upper combinations", action="store_true", default=False)
    parser.add_argument("-m", "--monolithic", help="Put all disassemblers in one file", action="store_true", default=True)
    parser.add_argument("-v", "--verbose", help="Show verbose progress", action="store_true", default=False)
    args = parser.parse_args()

    if args.dev:
        args.monolithic = False

    known = []
    for name in list(cputables.processors.keys()):
        cpu = CPU(name)
        known.append(cpu)

    for cpu in known:
        print(cpu)
        h = HistoryParserC(cpu)
        print(h.text)

