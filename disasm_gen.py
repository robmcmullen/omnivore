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
    def __init__(self, cpu, cpu_name, formatter_class, hex_lower=True, mnemonic_lower=False, first_of_set=True, **kwargs):
        self.cpu_name = cpu_name
        self.formatter_class = formatter_class
        self.set_case(hex_lower, mnemonic_lower)
        self.setup(**kwargs)
        self.generate(first_of_set)

    def set_case(self, hex_lower, mnemonic_lower):
        self.hex_lower = hex_lower
        self.mnemonic_lower = mnemonic_lower
        self.data_op = ".byte" if mnemonic_lower else ".BYTE"
        self.fmt_op = "$%02x" if hex_lower else "$%02X"
        self.fmt_2op = "$%02x%02x" if hex_lower else "$%02X%02X"

    def setup(self, bytes_per_line=4, **kwargs):
        self.bytes_per_line = bytes_per_line

    def gen_numpy_single_print(self, lines, *args, **kwargs):
        formatter = self.formatter_class(lines)
        formatter.gen_cases(self)
        formatter.end_subroutine()

    def start_formatter(self, lines):
        self.gen_numpy_single_print(lines)

    @property
    def function_name(self):
        c1 = "L" if self.mnemonic_lower else "U"
        c2 = "L" if self.hex_lower else "U"
        text = "parse_instruction_c_%s_%s%s" % (self.cpu_name, c1, c2)
        return text

    def generate(self, first_of_set):
        # lines = ["def parse_instruction(pc, src, last_pc):"]
        # lines.append("    opcode = src[0]")
        # lines.append("    print '%04x' % pc,")
        # self.gen_switch(lines, self.opcode_table)
        text = self.formatter_class.preamble
        if "%s" in text:
            text = text.replace("%s", self.function_name)
        if first_of_set:
            text = self.formatter_class.preamble_header + text
        lines = text.splitlines()

        self.start_formatter(lines)

        self.lines = lines

class DisassemblerGenerator(DataGenerator):
    def __init__(self, cpu, cpu_name, formatter_class, allow_undocumented=False, hex_lower=True, mnemonic_lower=False, r_mnemonics=None, w_mnemonics=None, rw_modes=None, first_of_set=True):
        self.formatter_class = formatter_class
        self.set_case(hex_lower, mnemonic_lower)
        self.setup(cpu, cpu_name, allow_undocumented, r_mnemonics, w_mnemonics, rw_modes)
        self.generate(first_of_set)

    def setup(self, cpu, cpu_name, allow_undocumented, r_mnemonics, w_mnemonics, rw_modes):
        self.r_mnemonics = r_mnemonics
        self.w_mnemonics = w_mnemonics
        self.allow_undocumented = allow_undocumented
        self.rw_modes = rw_modes
        self.cpu = cpu
        self.cpu_name = cpu_name

        cpu = cputables.processors[cpu]
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

def get_file(cpu_name, ext, monolithic, first=False):
    if monolithic:
        file_root = "udis_fast/hardcoded_parse_monolithic"
        if first:
            mode = "w"
        else:
            mode = "a"
    else:
        file_root = "udis_fast/hardcoded_parse_%s" % cpu_name
        mode = "w"
    if cpu_name is not None:
        print("Generating %s in %s" % (cpu_name, file_root))
    return open("%s.%s" % (file_root, ext), mode)

def gen_cpu(pyx, cpu, undoc=False, all_case_combos=False, do_py=False, do_c=True, monolithic=False):
    cpu_name = "%sundoc" % cpu if undoc else cpu
    for ext, formatter, do_it in [("py", PrintNumpy, do_py), ("c", RawC, do_c)]:
        if not do_it:
            continue
        pyx.cpus.add(cpu)
        with get_file(cpu_name, ext, monolithic) as fh:
            first = not monolithic
            if all_case_combos:
                for mnemonic_lower, hex_lower in [(True, True), (True, False), (False, True), (False, False)]:
                    disasm = DisassemblerGenerator(cpu, cpu_name, formatter, allow_undocumented=undoc, mnemonic_lower=mnemonic_lower, hex_lower=hex_lower, first_of_set=first)
                    fh.write("\n".join(disasm.lines))
                    fh.write("\n")
                    first = False
                    pyx.function_name_list.append(disasm.function_name)
            else:
                disasm = DisassemblerGenerator(cpu, cpu_name, formatter, allow_undocumented=undoc, first_of_set=first)
                fh.write("\n".join(disasm.lines))
                fh.write("\n")
                pyx.function_name_list.append(disasm.function_name)


def gen_others(pyx, all_case_combos=False, monolithic=False):
    for name, ext, formatter, generator in [("data", "c", DataC, DataGenerator), ("antic_dl", "c", AnticC, DataGenerator), ("jumpman_harvest", "c", JumpmanHarvestC, DataGenerator)]:
        pyx.cpus.add(name)
        with get_file(name, ext, monolithic) as fh:
            first = not monolithic
            if all_case_combos:
                for mnemonic_lower, hex_lower in [(True, True), (True, False), (False, True), (False, False)]:
                    disasm = generator(name, name, formatter, mnemonic_lower=mnemonic_lower, hex_lower=hex_lower, first_of_set=first)
                    fh.write("\n".join(disasm.lines))
                    fh.write("\n")
                    first = False
                    pyx.function_name_list.append(disasm.function_name)
            else:
                disasm = generator(name, name, formatter, first_of_set=first)
                fh.write("\n".join(disasm.lines))
                fh.write("\n")
                pyx.function_name_list.append(disasm.function_name)

def gen_all(pyx, all_case_combos=False, monolithic=False):
    for cpu in cputables.processors.keys():
        gen_cpu(pyx, cpu, False, all_case_combos, monolithic=monolithic)
    gen_cpu(pyx, "6502", True, all_case_combos, monolithic=monolithic)


class PyxGenerator(object):
    def __init__(self):
        self.cpus = set()
        self.function_name_list = []

    def gen_pyx(self):
        filename = "udis_fast/disasm_speedups_monolithic.pyx"
        prototype_arglist = "(char *wrap, char *src, int pc, int last_pc, np.uint16_t *labels, char *instructions, int strpos)"
        externlist = []
        for n in self.function_name_list:
            externlist.append("    int %s%s" % (n, prototype_arglist))
        deftemplate = """
    elif cpu == "$CPU":
        if mnemonic_lower:
            if hex_lower:
                parse_func = parse_instruction_c_$CPU_LL
            else:
                parse_func = parse_instruction_c_$CPU_LU
        else:
            if hex_lower:
                parse_func = parse_instruction_c_$CPU_UL
            else:
                parse_func = parse_instruction_c_$CPU_UU"""
        deflist = []
        for cpu in self.cpus:
            deflist.append(deftemplate.replace("$CPU", cpu))

        text = """from __future__ import division
import cython
import numpy as np
cimport numpy as np

ctypedef int (*parse_func_t)(char *, char *, int, int, np.uint16_t *, char *, int)

cdef extern:
$EXTERNLIST

@cython.boundscheck(False)
@cython.wraparound(False)
def get_disassembled_chunk_fast(cpu, storage_wrapper, np.ndarray[char, ndim=1, mode="c"] binary_array, pc, last, index_of_pc, mnemonic_lower, hex_lower):

    cdef np.ndarray metadata_array = storage_wrapper.metadata
    cdef itemsize = metadata_array.itemsize
    cdef row = storage_wrapper.row
    cdef char *metadata = metadata_array.data
    cdef int c_index = index_of_pc
    cdef char *binary = binary_array.data + c_index
    cdef int c_pc, c_last, count, max_rows, i
    cdef np.ndarray[np.uint16_t, ndim=1] labels_array = storage_wrapper.labels
    cdef np.uint16_t *labels = <np.uint16_t *>labels_array.data
    cdef np.ndarray[np.uint32_t, ndim=1] index_array = storage_wrapper.index
    cdef np.uint32_t *index = <np.uint32_t *>index_array.data + c_index
    cdef np.ndarray instructions_array = storage_wrapper.instructions
    cdef char *instructions = instructions_array.data
    cdef int strpos = storage_wrapper.last_strpos
    cdef int max_strpos = storage_wrapper.max_strpos
    cdef int retval
    cdef parse_func_t parse_func

    if cpu is None:
        raise TypeError("Must specify CPU type")
$DEFLIST
    else:
        raise TypeError("Unknown CPU type %s" % cpu)

    metadata += (row * itemsize)
    instructions += strpos
    c_pc = pc
    c_last = last
    max_rows = storage_wrapper.num_rows

    # fast loop in C
    while c_pc < c_last and row < max_rows and strpos < max_strpos:
        count = parse_func(metadata, binary, c_pc, c_last, labels, instructions, strpos)
        if count == 0:
            break
        elif count == 1:
            index[0] = row
            index += 1
        elif count == 2:
            index[0] = row
            index += 1
            index[0] = row
            index += 1
        elif count == 3:
            index[0] = row
            index += 1
            index[0] = row
            index += 1
            index[0] = row
            index += 1
        elif count == 4:
            index[0] = row
            index += 1
            index[0] = row
            index += 1
            index[0] = row
            index += 1
            index[0] = row
            index += 1
        else:
            for i in range(count):
                index[0] = row
                index += 1
        strlen = <int>metadata[6]
        c_pc += count
        c_index += count
        metadata += itemsize
        binary += count
        strpos += strlen
        instructions += strlen
        row += 1

    # get data back out in python vars
    pc = c_pc
    index_of_pc = c_index
    storage_wrapper.row = row
    storage_wrapper.last_strpos = strpos
    return pc, index_of_pc
""".replace("$EXTERNLIST", "\n".join(externlist)).replace("$DEFLIST", "\n".join(deflist))
        with open(filename, "w") as fh:
            fh.write(text)
        return text


if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--cpu", help="Specify CPU type (defaults to 6502)", default="")
    parser.add_argument("-p", "--py", help="Also create python code", action="store_true", default=False)
    parser.add_argument("-u", "--undocumented", help="Allow undocumented opcodes", action="store_true")
    parser.add_argument("-a", "--all-cases", help="Generate 4 separate functions for the lower/upper combinations", action="store_true", default=False)
    parser.add_argument("-m", "--monolithic", help="Put all disassemblers in one file", action="store_true")
    parser.add_argument("-v", "--verbose", help="Show verbose progress", action="store_true", default=False)
    args = parser.parse_args()

    if args.monolithic:
        with get_file(None, "c", True, True) as fh:
            fh.write(c_preamble_header)

    pyx = PyxGenerator()
    if args.cpu is None or args.cpu.lower() == "none":
        pass
    elif args.cpu:
        gen_cpu(pyx, args.cpu, args.undocumented, args.all_cases, args.py, monolithic=args.monolithic)
    else:
        gen_all(pyx, args.all_cases, args.monolithic)
    gen_others(pyx, args.all_cases, args.monolithic)

    if args.verbose:
        print("generated:\n", "\n".join(pyx.function_name_list))
    if args.monolithic:
        text = pyx.gen_pyx()
