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
from slugify import slugify

import sys
sys.path[0:0] = [os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))]

# mnemonic flags
from omni8bit.disassembler.flags import und, z80bit, lbl, pcr

import logging
log = logging.getLogger(__name__)

# from omni8bit.disassembler.flags import *
from omni8bit.disassembler import cputables

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

CustomEntry = namedtuple('CustomStringifier', ['cpu_name', 'function_name', 'function_return_type', 'function_signature'])

parser_signature = "history_entry_t *entry, unsigned char *src, unsigned int pc, unsigned int last_pc, unsigned short *labels"
custom_parsers = [
    CustomEntry('data', 'parse_entry_data', 'int', parser_signature),
    CustomEntry('antic_dl', 'parse_entry_antic_dl', 'int', parser_signature),
    CustomEntry('jumpman_harvest', 'parse_entry_jumpman_harvest', 'int', parser_signature),
]

stringifier_signature = "history_entry_t *entry, char *t, char *hexdigits, int lc, unsigned short *labels"
custom_stringifiers = [
    CustomEntry('data', 'stringify_entry_data', 'int', stringifier_signature),
    CustomEntry('antic_dl', 'stringify_entry_antic_dl', 'int', stringifier_signature),
    CustomEntry('jumpman_harvest', 'stringify_entry_jumpman_harvest', 'int', stringifier_signature),
]


disclaimer = """Warning! This is generated code.

Any edits will be overwritten with the next call to parse_gen.py
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
    def __init__(self, name):
        self.name = name
        self.disassembler_type = disassembler_type[name]
        self.disassembler_type_name = f"DISASM_{name}".upper()
        c = cputables.processors[name]
        self.address_modes = {}
        self.argorder = {}
        table = c['addressModeTable']
        for mode, fmt in list(table.items()):
            fmt, argorder = convert_fmt(fmt)
            self.address_modes[mode] = fmt
            self.argorder[mode] = argorder
            if "'" in fmt:
                print(f"WARNING in {self.name}! ' char in {fmt}")
        self.opcode_table = c['opcodeTable']
        self.opcodes = []
        self.leadin_opcodes = defaultdict(list)
        self.gen_opcodes()
        self.gen_stringifier()

    def __str__(self):
        return f"{self.name}: {len(self.opcodes)} opcodes, {len(self.leadin_opcodes)} leadin opcodes {tuple([hex(a) for a in self.leadin_opcodes.keys()])}"

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


def merge_cases_to_text(cases):
    same_body = defaultdict(list)
    for case in cases:
        case_text, body_text = case
        same_body[body_text].append(case_text)

    text = ""
    for body, case in same_body.items():
        group_cases = "\n".join(case)
        text += group_cases + body
        print(f"GROUPED CASES, {group_cases}\nBODY, {body}")
    return text


class HistoryParser:
    escape_strings = False

    function_return_type = "int"
    function_name_template = "parse_entry_%s"
    function_signature = parser_signature

    template = """
$RETURN_TYPE $NAME($SIGNATURE) {
	int dist;
	unsigned int rel;
	unsigned short addr;
	unsigned char opcode, op1, op2, op3;
	
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
        self.includes = ['#include <stdio.h>','#include <string.h>', '#include "libudis.h"']
        self.cases = self.create_cases()
        self.function_name = self.function_name_template % self.cpu_name

    def add_to_includes(self, include_lookup):
        for i in self.includes:
            if i not in include_lookup:
                include_lookup.add(i)

    @property
    def cpu_name(self):
        return self.cpu.name

    @property
    def text(self):
        text = self.template.replace("$NAME", self.function_name).replace("$CASES", self.cases).replace("$RETURN_TYPE", self.function_return_type).replace("$SIGNATURE", self.function_signature)
        return text

    def create_cases(self):
        single_byte_opcode_cases = []
        for cat, opcodes in self.cpu.gen_parser_combos(self.cpu.opcodes).items():
            print(f"{self.cpu}: {cat}, opcodes:{opcodes}")
            case = self.gen_case(cat, opcodes, "\t")
            single_byte_opcode_cases.append(case)
        text = merge_cases_to_text(single_byte_opcode_cases)

        leadin_byte_opcode_cases = []
        for leadin, leadin_opcodes in self.cpu.leadin_opcodes.items():
            subcases = []
            for cat, opcodes in self.cpu.gen_parser_combos(leadin_opcodes).items():
                subcase = self.gen_case(cat, opcodes, "\t\t")
                subcases.append(subcase)
            subcase_text = merge_cases_to_text(subcases)
            case = self.leadin_template % (leadin, subcase_text)
            text += case

        #print("\n".join(cases))
        return text

    def gen_case(self, cat, opcodes, extra_indent=""):
        case = []
        case.append(f"/* {cat.mode} {'(undocumented) ' if cat.undoc else ''}*/")
        for op in opcodes:
            case.append(f"case {hex(op.opcode)}: /* {op.mnemonic} {self.cpu.address_modes[cat.mode]} */")

        body = []
        body.append(f"\tentry->num_bytes = {cat.length};")
        body.extend(self.create_category(cat))
        flags = []
        if cat.operation_type:
            flags.append(cat.operation_type)
        if cat.undoc:
            flags.append("FLAG_UNDOC")
        if cat.target_addr:
            flags.append("FLAG_TARGET_ADDR")
        if flags:
            body.append(f"\tentry->flag = {' | '.join(flags)};")
        body.append(f"\tentry->disassembler_type = {self.cpu.disassembler_type_name};")
        body.append("\tbreak;\n\n")
        case_text = "\n".join([extra_indent + line for line in case]) + "\n"
        body_text = "\n".join([extra_indent + line for line in body]) + "\n"
        print(f"CASE{case_text}\nBODY{body_text}")
        return case_text, body_text


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
                        body.append(f"\tlabels[rel] = {self.cpu.disassembler_type_name};")
                        body.append(f"\tentry->target_addr = rel;")
                    elif cat.target_addr:
                        body.append(f"\top1 = *src;")
                        body.append(f"\tentry->instruction[1] = op1;")
                        body.append(f"\tlabels[op1] = {self.cpu.disassembler_type_name};")
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
                        body.append(f"\tlabels[addr] = {self.cpu.disassembler_type_name};")
                        body.append(f"\tentry->target_addr = addr;")
                elif cat.leadin < 256:
                    if cat.pcr:
                        body.append(f"\top1 = *src;")
                        body.append(f"\tentry->instruction[2] = op1;")
                        body.append(f"\tif (op1 > 127) dist = op1 - 256; else dist = op1;")
                        body.append(f"\trel = (pc + 2 + dist) & 0xffff;")
                        body.append(f"\tlabels[rel] = {self.cpu.disassembler_type_name};")
                        body.append(f"\tentry->target_addr = rel;")
                    elif cat.target_addr:
                        body.append(f"\top1 = *src;")
                        body.append(f"\tentry->instruction[2] = op1;")
                        body.append(f"\tlabels[op1] = {self.cpu.disassembler_type_name};")
                        body.append(f"\tentry->target_addr = op1;")
                    else:
                        body.append(f"\tentry->instruction[2] = *src;")
            elif cat.length == 4:
                if cat.leadin is None:
                    order = self.cpu.argorder[cat.mode]
                    print(f"\t/* {order} */")
                    body.append(f"\top1 = *src++;")
                    body.append(f"\tentry->instruction[1] = op1;")
                    body.append(f"\top2 = *src++;")
                    body.append(f"\tentry->instruction[2] = op2;")
                    body.append(f"\top3 = *src;")
                    body.append(f"\tentry->instruction[3] = op3;")
                    if cat.target_addr:
                        body.append(f"\taddr = (256 * {order[0]}) + {order[1]};")
                        body.append(f"\tlabels[addr] = {self.cpu.disassembler_type_name};")
                        body.append(f"\tentry->target_addr = addr;")
                elif cat.leadin < 256:
                    order = self.cpu.argorder[cat.mode]
                    print(f"\t/* {order} */", cat)
                    body.append(f"\top1 = *src++;")
                    body.append(f"\tentry->instruction[2] = op1;")
                    body.append(f"\top2 = *src;")
                    body.append(f"\tentry->instruction[3] = op2;")
                    if cat.pcr:
                        body.append("\taddr = op1 + 256 * op2;")
                        body.append("\tif (addr > 32768) addr -= 0x10000;")
                        # limit relative address to 64k address space
                        body.append("\trel = (pc + 2 + addr) & 0xffff;")
                        body.append(f"\tlabels[rel] = {self.cpu.disassembler_type_name};")
                        body.append("\tentry->target_addr = rel;")
                    elif cat.target_addr:
                        body.append(f"\taddr = (256 * {order[0]}) + {order[1]};")
                        body.append(f"\tlabels[addr] = {self.cpu.disassembler_type_name};")
                        body.append(f"\tentry->target_addr = addr;")

        return body


def label_target(cat):
    name = cat.mode.replace("@", "_at_") + "_" + str(cat.length)
    return "L" + slugify(name, separator="_")


class HistoryStringifier(HistoryParser):
    function_return_type = "int"
    function_name_template = "stringify_entry_%s"
    function_signature = stringifier_signature

    template = """
$RETURN_TYPE $NAME($SIGNATURE) {
	int dist;
	unsigned char opcode, leadin, op1, op2, op3;
	char *first_t, *h, *opstr;
	unsigned short rel, addr;

	first_t = t;
	opcode = entry->instruction[0];
	switch(opcode) {
$CASES
	default:
		h = &hexdigits[(opcode & 0xff)*2]; *t++=*h++; *t++=*h++;
		goto last;
	}
$TARGETS
last:
	return (int)(t - first_t);
}
"""

    leadin_template = """
case 0x%x:
	leadin = opcode;
	opcode = entry->instruction[1];
	switch(opcode) {
%s
	default:
		h = &hexdigits[(leadin & 0xff)*2]; *t++=*h++; *t++=*h++;
		h = &hexdigits[(opcode & 0xff)*2]; *t++=*h++; *t++=*h++;
		break;
	}
	break;
"""

    @property
    def text(self):
        text = self.template.replace("$NAME", self.function_name).replace("$CASES", self.cases).replace("$TARGETS", self.targets).replace("$RETURN_TYPE", self.function_return_type).replace("$SIGNATURE", self.function_signature)
        return text

    def create_cases(self):
        self.goto_targets = {}
        text = super().create_cases()
        self.targets = ""
        for target in self.goto_targets.values():
            self.targets += target
        return text

    def gen_case(self, cat, opcodes, extra_indent=""):
        case = []
        case.append(f"/* {cat.mode} {self.cpu.address_modes[cat.mode]} {'(undocumented) ' if cat.undoc else ''}*/")
        slug = label_target(cat)
        for op in opcodes:
            case.append(f"case {hex(op.opcode)}: opstr = lc ? \"{op.mnemonic.lower()}\" : \"{op.mnemonic.upper()}\"; goto {slug};")

        case_text = "\n".join([extra_indent + line for line in case]) + "\n"
        body_text = ""
        if slug not in self.goto_targets:
            print(f"processing opcodes {opcodes}")
            target = self.create_goto_target(cat)
            self.goto_targets[slug] = "\n".join(target) + "\n"
        return case_text, body_text

    def create_goto_target(self, cat):
        body = []
        label = label_target(cat)
        outstr = self.cpu.address_modes[cat.mode]
        argorder = self.cpu.argorder[cat.mode]
        body.append(f"{label}: /* {outstr} {argorder} */")
        print("processing", cat, f"{label}: /* {outstr} {argorder} */")
        body.append("\tdo {*t++ = *opstr++;} while (*opstr);")
        if cat.length == 2:
            if cat.pcr:
                body.append(f"\trel = entry->target_addr;")
            elif cat.leadin is None:
                body.append(f"\top1 = entry->instruction[1];")
            else:
                pass  # no arguments possible if 2 bytes with leadin
        elif cat.length == 3:
            if cat.pcr:
                body.append(f"\trel = entry->target_addr;")
            elif cat.leadin is None:
                body.append(f"\top1 = entry->instruction[1];")
                body.append(f"\top2 = entry->instruction[2];")
            elif cat.leadin < 256:
                body.append(f"\top1 = entry->instruction[2];")
            else:
                raise RuntimeError("length=3, not pcr or leadin")
        elif cat.length == 4:
            if cat.pcr:
                body.append(f"\trel = entry->target_addr;")
            elif cat.leadin is None:
                body.append(f"\top1 = entry->instruction[1];")
                body.append(f"\top2 = entry->instruction[2];")
                body.append(f"\top3 = entry->instruction[3];")
            elif cat.leadin < 256:
                body.append(f"\top1 = entry->instruction[2];")
                body.append(f"\top2 = entry->instruction[3];")
            else:
                raise RuntimeError("length=4, not pcr or leadin")
        if outstr:
            lines = self.opcode_line_out(outstr, argorder)
            body.extend(lines)
        body.append("\tgoto last;")
        return body

    def opcode_line_out(self, outstr, argorder=[], force_case=False):
        argorder = list(argorder)  # operate on copy!
        outstr = " " + outstr.strip()
        print("opcode_line_out: %s %s" % (outstr, argorder))
        lines = []

        def flush_mixed(diffs):
            if force_case:
                for c in diffs:
                    lines.append("\t\t*t++ = '%s';" % c)
            else:
                # lines.append("    if (lc) {")
                # for c in diffs:
                #     lines.append("        *t++ = '%s'" % c.lower())
                # lines.append("    }")
                # lines.append("    else {")
                # for c in diffs:
                #     lines.append("        *t++ = '%s'" % c.upper())
                # lines.append("    }")
                line = "if (lc) "
                ops = ["*t++='%s'" % c.lower() for c in diffs]
                line += ",".join(ops)
                # for c in diffs:
                #     lines.append("        *t++ = '%s'" % c.lower())
                lines.append("\t%s;" % line)
                line = "else "
                ops = ["*t++='%s'" % c.upper() for c in diffs]
                line += ",".join(ops)
                # for c in diffs:
                #     lines.append("        *t++ = '%s'" % c.lower())
                lines.append("\t%s;" % line)
            return []

        def flush_text(text):
            same = []
            diffs = []
            for l, u in zip(text.lower(), text.upper()):
                if l == u:
                    #print "l==u: -->%s<-- -->%s<--: diffs=%s" % (l, u, diffs)
                    if len(diffs) > 0:
                        diffs = flush_mixed(diffs)
                    if u == "'" or u == "\\":
                        same.append("\\%s" %  u)
                    else:
                        same.append(u)
                else:
                    if len(same) > 0:
                        lines.append("\t" + ",".join(["*t++='%s'" % s for s in same]) + ";")
                        same = []
                    diffs.append(u)
                    #print "l!=u: -->%s<-- -->%s<--: diffs=%s" % (l, u, diffs)
            if len(same) > 0:
                lines.append("\t" + ",".join(["*t++='%s'" % s for s in same]) + ";")
            if len(diffs) > 0:
                flush_mixed(diffs)
            return ""

        def flush_nibble(operand):
            lines.append(f"\th = &hexdigits[({operand})*2] + 1; *t++=*h++;")

        def flush_hex(operand, indent="\t"):
            lines.append(f"{indent}h = &hexdigits[({operand})*2]; *t++=*h++; *t++=*h++;")

        def flush_addr(op1, op2):
            lines.append(f"\th = &hexdigits[({operand})*2]; *t++=*h++; *t++=*h++;")

        def flush_label1x8(op1):
            lines.append(f"\taddr = entry->target_addr;")
            lines.append(f"\tif (labels[addr]) {{")
            lines.append(f"\t\t*t++='L';")
            flush_hex(f"addr & 0xff", "\t\t")
            lines.append(f"\t}}")
            lines.append(f"\telse {{")
            lines.append(f"\t\t*t++='$';")
            flush_hex(f"addr & 0xff", "\t\t")
            lines.append(f"\t}}")

        def flush_label2x8(op1, op2):
            lines.append(f"\taddr = entry->target_addr;")
            lines.append(f"\tif (labels[addr]) {{")
            lines.append(f"\t\t*t++='L';")
            flush_hex(f"addr >> 8", "\t\t")
            flush_hex(f"addr & 0xff", "\t\t")
            lines.append(f"\t}}")
            lines.append(f"\telse {{")
            lines.append(f"\t\t*t++='$';")
            flush_hex(f"addr >> 8", "\t\t")
            flush_hex(f"addr & 0xff", "\t\t")
            lines.append(f"\t}}")

        def flush_label16(operand):
            lines.append(f"\tif (labels[{operand}]) {{")
            lines.append(f"\t\t*t++='L';")
            flush_hex(f"{operand} >> 8", "\t\t")
            flush_hex(f"{operand} & 0xff", "\t\t")
            lines.append(f"\t}}")
            lines.append(f"\telse {{")
            lines.append(f"\t\t*t++='$';")
            flush_hex(f"{operand} >> 8")
            flush_hex(f"{operand} & 0xff")
            lines.append(f"\t}}")

        def flush_hex16(operand):
            flush_hex("(%s>>8)" % operand)
            flush_hex("%s" % operand)
            # lines.append("    h = &hexdigits[((%s>>8)&0xff)*2]" % operand)
            # lines.append("    *t++=*h++")
            # lines.append("    *t++=*h++")
            # lines.append("    h = &hexdigits[(%s&0xff)*2]" % operand)
            # lines.append("    *t++=*h++")
            # lines.append("    *t++=*h++")

        def flush_dec(operand):
            lines.append("\tt+=sprintf(t, \"%%d\", %s);" % operand)

        def flush_raw(operand):
            lines.append("\t*t++=%s;" % operand)

        i = 0
        text = ""
        fmt = ""
        while i < len(outstr):
            tail = outstr[i:].lower()
            if tail.startswith("#$%02x%02x"):
                text = text + "#$"
                text = flush_text(text)
                flush_hex(argorder.pop(0))
                flush_hex(argorder.pop(0))
                i += 10
            elif tail.startswith("#$%02x"):
                text = text + "#$"
                text = flush_text(text)
                flush_hex(argorder.pop(0))
                i += 6
            elif tail.startswith("$%02x%02x"):
                text = flush_text(text)
                flush_label2x8(argorder.pop(0), argorder.pop(0))
                i += 9
            elif tail.startswith("$%02x"):
                text = flush_text(text)
                flush_label1x8(argorder.pop(0))
                i += 5
            elif tail.startswith("$%04x"):
                text = flush_text(text)
                flush_label16(argorder.pop(0))
                i += 5
            elif tail.startswith("%02x"):
                text = flush_text(text)
                flush_hex(argorder.pop(0))
                i += 4
            elif tail.startswith("%1x"):
                text = flush_text(text)
                flush_nibble(argorder.pop(0))
                i += 3
            elif tail.startswith("%d"):
                text = flush_text(text)
                flush_dec(argorder.pop(0))
                i += 2
            elif tail.startswith("\\"):
                text = flush_text(text)
                i += 1
                flush_raw(ord(outstr[i]))
                i += 1
            elif tail.startswith("$%"):
                raise RuntimeError("Unsupported operand format: %s" % tail)
            else:
                text += outstr[i]
                i += 1
        flush_text(text)
        return lines


def gen_pyx(filename, parsers, stringifiers):
    externlist = []
    for p in parsers + custom_parsers + stringifiers + custom_stringifiers:
        externlist.append(f"    {p.function_return_type} {p.function_name}({p.function_signature})")

    parsetemplate = """    $IF strcmp(cpu, "$CPU") == 0:
        parse_func = $FUNC"""
    stringtemplate = """    $IF strcmp(cpu, "$CPU") == 0:
        string_func = $FUNC"""
    parselist = []
    stringlist = []
    iftext = "if"
    typelist = []
    for p in parsers + custom_parsers:
        parselist.append(parsetemplate.replace("$CPU", p.cpu_name).replace("$IF", iftext).replace("$FUNC", p.function_name))
        iftext = "elif"
    iftext = "if"
    for p in stringifiers + custom_stringifiers:
        stringlist.append(stringtemplate.replace("$CPU", p.cpu_name).replace("$IF", iftext).replace("$FUNC", p.function_name))
        iftext = "elif"

    header = """
from libc.string cimport strcmp
import cython
import numpy as np
cimport numpy as np

from libudis.libudis cimport parse_func_t, string_func_t, history_entry_t

cdef extern:
$EXTERNLIST

cdef parse_func_t find_parse_function(char *cpu):
    cdef parse_func_t parse_func

$PARSELIST
    else:
        parse_func = NULL
    return parse_func

cdef string_func_t find_string_function(char *cpu):
    cdef string_func_t string_func

$STRINGLIST
    else:
        string_func = NULL
    return string_func

cdef string_func_t stringifier_map[$TYPEMAX]
$TYPELIST
""".replace("$EXTERNLIST", "\n".join(externlist)).replace("$PARSELIST", "\n".join(parselist)).replace("$STRINGLIST", "\n".join(stringlist)).replace("$TYPELIST", "\n".join(typelist)).replace("$TYPEMAX", str(disassembler_type_max))

    with open(filename, "w") as fh:
        fh.write(py_disclaimer)
        fh.write(header)

def gen_map(fh, stringifiers):
    all_stringifiers = stringifiers + custom_stringifiers
    cpu_order = sorted(all_stringifiers, key=lambda p: disassembler_type[p.cpu_name])
    if fh is not None:
        for p in custom_stringifiers:
            fh.write(f"extern {p.function_return_type} {p.function_name}({p.function_signature});\n")
        fh.write("\nvoid *stringifier_map[] = {\n")
        expected = 0
        for p in cpu_order:
            i = disassembler_type[p.cpu_name]
            while i > expected:
                fh.write("NULL, /* %d */\n" % expected)
                expected += 1
            fh.write("%s, /* %d */\n" % (p.function_name, i))
            expected += 1
        fh.write("};\n")

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
        if name == "z80":
            continue
        cpu = CPU(name)
        known.append(cpu)

    generated_parsers = []
    with open("parse_udis_cpu.c", "w") as fh:
        fh.write(c_disclaimer)
        c_includes = set()
        for cpu in known:
            print(f"computing {cpu}")
            h = HistoryParser(cpu)
            h.add_to_includes(c_includes)
            generated_parsers.append(h)

        fh.write("\n".join(list(c_includes)) + "\n\n")
        for h in generated_parsers:
            fh.write(h.text)

    generated_stringifiers = []
    with open("stringify_udis_cpu.c", "w") as fh:
        fh.write(c_disclaimer)
        c_includes = set()
        for cpu in known:
            print(f"computing {cpu}")
            s = HistoryStringifier(cpu)
            s.add_to_includes(c_includes)
            generated_stringifiers.append(s)

        fh.write("\n".join(list(c_includes)) + "\n\n")
        for s in generated_stringifiers:
            fh.write(s.text)

        fh.write("\n\n")
        gen_map(fh, generated_stringifiers)

    gen_pyx("declarations.pyx", generated_parsers, generated_stringifiers)
