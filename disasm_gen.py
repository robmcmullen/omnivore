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

disclaimer = """Warning! This is generated code.

Any edits will be overwritten with the next call to disasm_gen.py
"""
c_disclaimer = "/***************************************************************\n%s***************************************************************/\n\n\n" % disclaimer
py_disclaimer = "\n".join("# %s" % line for line in disclaimer.splitlines()) + "\n\n"

class DataGenerator(object):
    def __init__(self, cpu, cpu_name, formatter_class, hex_lower=True, mnemonic_lower=False, first_of_set=True, cases_in_filename=False, **kwargs):
        self.cpu_name = cpu_name
        self.formatter_class = formatter_class
        self.set_case(hex_lower, mnemonic_lower, cases_in_filename)
        self.setup(**kwargs)
        self.generate(first_of_set)

    def set_case(self, hex_lower, mnemonic_lower, cases):
        self.hex_lower = hex_lower
        self.mnemonic_lower = mnemonic_lower
        self.cases_in_filename = cases
        self.data_op = ".db" if mnemonic_lower else ".DB"
        self.fmt_op = "$%02x" if hex_lower else "$%02X"
        self.fmt_2op = "$%02x%02x" if hex_lower else "$%02X%02X"

    def setup(self, bytes_per_line=4, **kwargs):
        self.bytes_per_line = bytes_per_line

    def gen_numpy_single_print(self, lines, *args, **kwargs):
        formatter = self.formatter_class(self, lines)
        formatter.gen_cases()
        formatter.end_subroutine()

    def start_formatter(self, lines):
        self.gen_numpy_single_print(lines)

    @property
    def function_name(self):
        if self.cases_in_filename:
            suffix = "_"
            suffix += "L" if self.mnemonic_lower else "U"
            suffix += "L" if self.hex_lower else "U"
        else:
            suffix = ""
        text = "parse_instruction_c_%s%s" % (self.cpu_name, suffix)
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
    def __init__(self, cpu, cpu_name, formatter_class, allow_undocumented=False, hex_lower=True, mnemonic_lower=False, r_mnemonics=None, w_mnemonics=None, rw_modes=None, first_of_set=True, cases_in_filename=False):
        self.formatter_class = formatter_class
        self.set_case(hex_lower, mnemonic_lower, cases_in_filename)
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
            if "'" in fmt:
                print(fmt)
        self.opcode_table = cpu['opcodeTable']

    def gen_numpy_single_print(self, lines, table, leadin=0, leadin_offset=0, indent="    ", z80_2nd_byte=None):
        """Store in numpy array of strings:

        0000 00 00 00 00       lda #$30
                         ^^^^^ space for a 5 character label, to be placed later
        """
        formatter = self.formatter_class(self, lines, indent, leadin, leadin_offset)
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
                length, mnemonic, mode, flag = optable
                # check for placeholder z80 instructions & ignore them the
                # real instructions for ddcb and fdcb will have 4 byte
                # opcodes
                if flag & z80bit and (opcode == 0xddcb or opcode == 0xfdcb):
                    continue
                log.debug("found multibyte %x, l=%d" % (opcode, leadin_offset))
                leadin = opcode // 256
                opcode = opcode & 0xff
                if leadin not in multibyte:
                    multibyte[leadin] = dict()
                multibyte[leadin][opcode] = optable
                continue
            try:
                formatter.set_current(optable)
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

def gen_cpu(pyx, cpu, undoc=False, all_case_combos=False, do_py=False, do_c=True, monolithic=False, dev=False):
    if dev:
        cpu_name = "dev"
    else:
        cpu_name = "%sundoc" % cpu if undoc else cpu
    for ext, formatter, do_it in [("py", PrintNumpy, do_py), ("c", UnrolledC, do_c)]:
        if not do_it:
            continue
        pyx.cpus.add(cpu)
        with get_file(cpu_name, ext, monolithic) as fh:
            first = not monolithic
            if first:
                fh.write(c_disclaimer)
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
        prototype_arglist = "(char *wrap, char *src, int pc, int last_pc, np.uint16_t *labels, char *instructions, int strpos, int mnemonic_lower, char *hexdigits, char *lc_byte_mnemonic, char *uc_byte_mnemonic)"
        externlist = []
        for n in self.function_name_list:
            externlist.append("    int %s%s" % (n, prototype_arglist))
        deftemplate = """
    elif cpu == "$CPU":
        parse_func = parse_instruction_c_$CPU"""
        deflist = []
        for cpu in self.cpus:
            deflist.append(deftemplate.replace("$CPU", cpu))

        text = """from __future__ import division
import cython
import numpy as np
cimport numpy as np

ctypedef int (*parse_func_t)(char *, char *, int, int, np.uint16_t *, char *, int, int, char *, char *, char *)

cdef char *hexdigits_lower = "000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f202122232425262728292a2b2c2d2e2f303132333435363738393a3b3c3d3e3f404142434445464748494a4b4c4d4e4f505152535455565758595a5b5c5d5e5f606162636465666768696a6b6c6d6e6f707172737475767778797a7b7c7d7e7f808182838485868788898a8b8c8d8e8f909192939495969798999a9b9c9d9e9fa0a1a2a3a4a5a6a7a8a9aaabacadaeafb0b1b2b3b4b5b6b7b8b9babbbcbdbebfc0c1c2c3c4c5c6c7c8c9cacbcccdcecfd0d1d2d3d4d5d6d7d8d9dadbdcdddedfe0e1e2e3e4e5e6e7e8e9eaebecedeeeff0f1f2f3f4f5f6f7f8f9fafbfcfdfeff"
cdef char *hexdigits_upper = "000102030405060708090A0B0C0D0E0F101112131415161718191A1B1C1D1E1F202122232425262728292A2B2C2D2E2F303132333435363738393A3B3C3D3E3F404142434445464748494A4B4C4D4E4F505152535455565758595A5B5C5D5E5F606162636465666768696A6B6C6D6E6F707172737475767778797A7B7C7D7E7F808182838485868788898A8B8C8D8E8F909192939495969798999A9B9C9D9E9FA0A1A2A3A4A5A6A7A8A9AAABACADAEAFB0B1B2B3B4B5B6B7B8B9BABBBCBDBEBFC0C1C2C3C4C5C6C7C8C9CACBCCCDCECFD0D1D2D3D4D5D6D7D8D9DADBDCDDDEDFE0E1E2E3E4E5E6E7E8E9EAEBECEDEEEFF0F1F2F3F4F5F6F7F8F9FAFBFCFDFEFF"

cdef extern:
$EXTERNLIST

@cython.boundscheck(False)
@cython.wraparound(False)
def get_disassembled_chunk_fast(cpu, storage_wrapper, np.ndarray[char, ndim=1, mode="c"] binary_array, pc, last, index_of_pc, mnemonic_lower, hex_lower, byte_mnemonic):

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
    py_lc_byte_string = byte_mnemonic.lower().encode('UTF-8')
    cdef char *c_lc_byte_mnemonic = py_lc_byte_string
    py_uc_byte_string = byte_mnemonic.upper().encode('UTF-8')
    cdef char *c_uc_byte_mnemonic = py_uc_byte_string
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
    if hex_lower:
        hexdigits_for_case = hexdigits_lower
    else:
        hexdigits_for_case = hexdigits_upper

    # fast loop in C
    while c_pc < c_last and row < max_rows and strpos < max_strpos:
        count = parse_func(metadata, binary, c_pc, c_last, labels, instructions, strpos, mnemonic_lower, hexdigits_for_case, c_lc_byte_mnemonic, c_uc_byte_mnemonic)
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
            fh.write(py_disclaimer)
            fh.write(text)
        return text


if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--cpu", help="Specify CPU type (defaults to 6502)", default="")
    parser.add_argument("-d", "--dev", help="Build for development testing", action="store_true", default=False)
    parser.add_argument("-p", "--py", help="Also create python code", action="store_true", default=False)
    parser.add_argument("-u", "--undocumented", help="Allow undocumented opcodes", action="store_true")
    parser.add_argument("-a", "--all-cases", help="Generate 4 separate functions for the lower/upper combinations", action="store_true", default=False)
    parser.add_argument("-m", "--monolithic", help="Put all disassemblers in one file", action="store_true")
    parser.add_argument("-v", "--verbose", help="Show verbose progress", action="store_true", default=False)
    args = parser.parse_args()

    if args.monolithic:
        with get_file(None, "c", True, True) as fh:
            fh.write(c_disclaimer)
            fh.write(c_preamble_header)

    if args.dev:
        args.all_cases = False
        args.monolithic = False

    pyx = PyxGenerator()
    if args.cpu is None or args.cpu.lower() == "none":
        pass
    elif args.cpu:
        gen_cpu(pyx, args.cpu, args.undocumented, args.all_cases, args.py, monolithic=args.monolithic, dev=args.dev)
    else:
        gen_all(pyx, args.all_cases, args.monolithic)
    gen_others(pyx, args.all_cases, args.monolithic)

    if args.verbose:
        print("generated:\n", "\n".join(pyx.function_name_list))
    if args.monolithic:
        text = pyx.gen_pyx()
