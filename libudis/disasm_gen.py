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
from collections import defaultdict

import numpy as np

import sys
sys.path[0:0] = [os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))]

from disasm_gen_utils import *

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

class DataGenerator(object):
    def __init__(self, cpu, cpu_name, formatter_class, hex_lower=True, mnemonic_lower=False, cases_in_filename=False, function_name_root="", **kwargs):
        self.disassembler_type = disassembler_type[cpu]
        self.cpu_name = cpu_name
        self.formatter_class = formatter_class
        self.set_case(hex_lower, mnemonic_lower, cases_in_filename)
        if not function_name_root:
            function_name_root = "parse_history_entry_c_"
        self.function_name_root = function_name_root
        self.setup(**kwargs)
        self.generate()

    def set_case(self, hex_lower, mnemonic_lower, cases):
        self.hex_lower = hex_lower
        self.mnemonic_lower = mnemonic_lower
        self.cases_in_filename = cases
        self.data_op = "%02x" if hex_lower else "%02X"
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
        text = "%s%s%s" % (self.function_name_root, self.cpu_name, suffix)
        return text

    def generate(self):
        # lines = ["def parse_instruction(pc, src, last_pc):"]
        # lines.append("    opcode = src[0]")
        # lines.append("    print '%04x' % pc,")
        # self.gen_switch(lines, self.opcode_table)
        text = self.formatter_class.preamble
        if "%s" in text:
            text = text.replace("%s", self.function_name)
        lines = text.splitlines()

        self.start_formatter(lines)

        self.lines = lines

class AnticDataGenerator(DataGenerator):
    def setup(self, bytes_per_line=16, **kwargs):
        self.bytes_per_line = bytes_per_line

class DisassemblerGenerator(DataGenerator):
    def __init__(self, cpu, cpu_name, formatter_class, hex_lower=True, mnemonic_lower=False, r_mnemonics=None, w_mnemonics=None, rw_modes=None, cases_in_filename=False):
        self.formatter_class = formatter_class
        self.set_case(hex_lower, mnemonic_lower, cases_in_filename)
        self.setup(cpu, cpu_name, r_mnemonics, w_mnemonics, rw_modes)
        self.generate()

    def setup(self, cpu, cpu_name, r_mnemonics, w_mnemonics, rw_modes):
        self.r_mnemonics = r_mnemonics
        self.w_mnemonics = w_mnemonics
        self.rw_modes = rw_modes
        self.cpu = cpu
        self.cpu_name = cpu_name
        self.setup_cpu(cpu)

    def setup_cpu(self, cpu):
        self.disassembler_type = disassembler_type[cpu]
        cpu = cputables.processors[cpu]
        self.address_modes = {}
        table = cpu['addressModeTable']
        if self.rw_modes is None:
            self.rw_modes = set()
        for mode, fmt in list(table.items()):
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

        formatter.start_subroutine()

        for opcode, optable in list(table.items()):
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

            log.debug("Processing %x, %s" % (opcode, formatter.fmt))
            if z80_2nd_byte is not None:
                formatter.z80_4byte(z80_2nd_byte, opcode)
                continue

            formatter.process(opcode)

        for leadin, group in list(multibyte.items()):
            formatter.start_multibyte_leadin(leadin)
            log.debug("starting multibyte with leadin %x" % leadin)
            log.debug(group)
            self.gen_numpy_single_print(lines, group, leadin, 1, indent=indent+"    ")

        if not z80_2nd_byte:
            formatter.unknown_opcode()
        formatter.end_subroutine()

    def start_formatter(self, lines):
        self.gen_numpy_single_print(lines, self.opcode_table)

class HistoryParser(DataGenerator):
    def __init__(self, cpu, cpu_name, formatter_class):
        self.formatter_class = formatter_class
        self.setup(cpu, cpu_name)
        self.generate()

    def setup(self, cpu, cpu_name):
        self.set_case(False, False, False)
        self.rw_modes = set()
        self.cpu = cpu
        self.cpu_name = cpu_name
        self.disassembler_type = disassembler_type[cpu]

        cpu = cputables.processors[cpu]
        self.address_modes = {}
        table = cpu['addressModeTable']
        for mode, fmt in list(table.items()):
            self.address_modes[mode] = fmt
            if "'" in fmt:
                print(fmt)
        self.opcode_table = cpu['opcodeTable']

    @property
    def function_name(self):
        text = "parse_history_entry_c_%s" % (self.cpu_name)
        return text

    def gen_numpy_single_print(self, lines, table, leadin=0, leadin_offset=0, indent="    ", z80_2nd_byte=None):
        """Store in numpy array of strings:

        0000 00 00 00 00       lda #$30
                         ^^^^^ space for a 5 character label, to be placed later
        """
        formatter = self.formatter_class(self, lines, indent, leadin, leadin_offset)
        multibyte = dict()
        groups = defaultdict(list)
        group_code = dict()

        for opcode, optable in list(table.items()):
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

            log.debug("Processing %x, %s" % (opcode, formatter.fmt))
            if z80_2nd_byte is not None:
                formatter.z80_4byte(z80_2nd_byte, opcode)
                continue

            save = formatter.lines
            formatter.lines = []
            formatter.process(opcode)
            case = formatter.lines.pop(0)  # get the case statement
            print("CASE", case)
            mode = formatter.mode
            if formatter.undocumented:
                mode += "-undoc"
            groups[mode].append(case)
            group_code[mode] = formatter.lines
            print("OSUHRECHUS", formatter.fmt, opcode, mode, formatter.lines)
            formatter.lines = save

        for leadin, group in list(multibyte.items()):
            formatter.start_multibyte_leadin(leadin)
            log.debug("starting multibyte with leadin %x" % leadin)
            log.debug(group)
            self.gen_numpy_single_print(lines, group, leadin, 1, indent=indent+"    ")

        formatter.start_subroutine()

        for m, lines in group_code.items():
            groups[m][0] += f" /* {m} */"
            formatter.lines.extend(groups[m])
            formatter.lines.extend(lines)

        if not z80_2nd_byte:
            formatter.unknown_opcode()

        formatter.end_subroutine()

    def start_formatter(self, lines):
        self.gen_numpy_single_print(lines, self.opcode_table)


class HistoryToText(DisassemblerGenerator):
    @property
    def function_name(self):
        if self.cases_in_filename:
            suffix = "_"
            suffix += "L" if self.mnemonic_lower else "U"
            suffix += "L" if self.hex_lower else "U"
        else:
            suffix = ""
        text = "to_string_c_%s%s" % (self.cpu_name, suffix)
        return text


class HistoryOtherToText(HistoryToText):
    def setup_cpu(self, cpu):
        pass



class PyxGenerator(object):
    def __init__(self, monolithic, dev, all_cases):
        self.monolithic = monolithic
        self.dev = dev
        self.all_case_combos = all_cases
        self.cpus = set()
        self.parse_name_list = []
        self.string_name_list = []
        self.previously_opened_files = set()
        self.previously_used_generators = set()

    def get_file(self, cpu_name, ext):
        if self.monolithic:
            file_root = "hardcoded_parse_monolithic"
        else:
            file_root = "hardcoded_parse_%s" % cpu_name
        if file_root not in self.previously_opened_files:
            mode = "w"
        else:
            mode = "a"
        if cpu_name is not None:
            print("Generating %s in %s" % (cpu_name, file_root))
        self.previously_opened_files.add(file_root)
        pathname = os.path.join(os.path.dirname(__file__), "%s.%s" % (file_root, ext))
        fh = open(pathname, mode)
        if mode == "w":
            fh.write(c_disclaimer)
        return fh

    def gen_cpu(pyx, cpu, do_py=False, do_c=True):
        if pyx.dev:
            cpu_name = "dev"
        else:
            cpu_name = cpu
        for ext, formatter, do_it in [("c", UnrolledC, do_c)]:
            if not do_it:
                continue
            pyx.cpus.add(cpu)
            with pyx.get_file(cpu_name, ext) as fh:
                disasm = HistoryParser(cpu, cpu_name, HistoryEntryC)
                header = disasm.formatter_class.preamble_header
                if header not in pyx.previously_used_generators:
                    fh.write(header)
                pyx.previously_used_generators.add(header)
                fh.write("\n".join(disasm.lines))
                fh.write("\n")
                pyx.parse_name_list.append(disasm.function_name)
                # if pyx.all_case_combos:
                #     for mnemonic_lower, hex_lower in [(True, True), (True, False), (False, True), (False, False)]:
                #         disasm = HistoryToText(cpu, cpu_name, formatter, mnemonic_lower=mnemonic_lower, hex_lower=hex_lower, first_of_set=first)
                #         fh.write("\n".join(disasm.lines))
                #         fh.write("\n")
                #         first = False
                #         pyx.function_name_list.append(disasm.function_name)
                # else:
                if True:
                    disasm = HistoryToText(cpu, cpu_name, formatter)
                    header = disasm.formatter_class.preamble_header
                    if header not in pyx.previously_used_generators:
                        fh.write(header)
                    fh.write("\n".join(disasm.lines))
                    fh.write("\n")
                    pyx.string_name_list.append(disasm.function_name)


    def gen_others(pyx):
        for name, ext, formatter, generator, stringifier in [("data", "c", HistoryEntryDataC, DataGenerator, DataC), ("antic_dl", "c", HistoryEntryAnticC, AnticDataGenerator, AnticC), ("jumpman_harvest", "c", HistoryEntryJumpmanHarvestC, DataGenerator, JumpmanHarvestC)]:
            pyx.cpus.add(name)
            with pyx.get_file(name, ext) as fh:
                if pyx.all_case_combos:
                    first = True
                    for mnemonic_lower, hex_lower in [(True, True), (True, False), (False, True), (False, False)]:
                        disasm = generator(name, name, formatter, mnemonic_lower=mnemonic_lower, hex_lower=hex_lower, first_of_set=first)
                        fh.write("\n".join(disasm.lines))
                        fh.write("\n")
                        first = False
                        pyx.parse_name_list.append(disasm.function_name)
                else:
                    disasm = generator(name, name, formatter)
                    fh.write("\n".join(disasm.lines))
                    fh.write("\n")
                    pyx.parse_name_list.append(disasm.function_name)
                disasm = generator(name, name, stringifier, function_name_root="to_string_c_")
                fh.write("\n".join(disasm.lines))
                fh.write("\n")
                pyx.string_name_list.append(disasm.function_name)


    def gen_all(self):
        for cpu in list(cputables.processors.keys()):
            self.gen_cpu(cpu)

    def gen_pyx(self):
        filename = "disasm_speedups_monolithic.pyx"
        parse_prototype_arglist = "(history_entry_t *entry, unsigned char *src, unsigned int pc, unsigned int last_pc, np.uint16_t *labels)"
        externlist = []
        for n in self.parse_name_list:
            externlist.append("    int %s%s" % (n, parse_prototype_arglist))

        string_prototype_arglist = "(history_entry_t *entry, char *txt, char *hexdigits, int lc)"
        for n in self.string_name_list:
            externlist.append("    int %s%s" % (n, string_prototype_arglist))
        deftemplate = """    elif cpu == "$CPU":
        parse_func = parse_history_entry_c_$CPU"""
        deflist = []
        for cpu in self.cpus:
            deflist.append(deftemplate.replace("$CPU", cpu))
        parsetemplate = """    $IF strcmp(cpu, "$CPU") == 0:
        parse_func = parse_history_entry_c_$CPU"""
        parselist = []
        stringfunc_prefix = "to_string_c_"
        stringtemplate = """    $IF strcmp(cpu, "$CPU") == 0:
        string_func = %s$CPU""" % stringfunc_prefix
        stringlist = []
        iftext = "if"
        typelist = []
        for cpu in self.cpus:
            parselist.append(parsetemplate.replace("$CPU", cpu).replace("$IF", iftext))
            stringlist.append(stringtemplate.replace("$CPU", cpu).replace("$IF", iftext))
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
""".replace("$EXTERNLIST", "\n".join(externlist)).replace("$DEFLIST", "\n".join(deflist)).replace("$PARSELIST", "\n".join(parselist)).replace("$STRINGLIST", "\n".join(stringlist)).replace("$TYPELIST", "\n".join(typelist)).replace("$TYPEMAX", str(disassembler_type_max))

        with open(os.path.join(os.path.dirname(__file__), filename), "w") as fh:
            fh.write(py_disclaimer)
            fh.write(header)

        filename = "hardcoded_parse_stringifiers.c"
        cpu_order = sorted([(disassembler_type[cpu], cpu) for cpu in self.cpus])
        with open(os.path.join(os.path.dirname(__file__), filename), "w") as fh:
            fh.write(c_disclaimer)
            fh.write("#include <stdio.h>\n\n")
            for i, cpu in cpu_order:
                fh.write("extern int %s%s();\n" % (stringfunc_prefix, cpu))
            fh.write("void *stringifier_map[] = {\n")
            expected = 0
            for i, cpu in cpu_order:
                while i > expected:
                    fh.write("NULL, /* %d */\n" % expected)
                    expected += 1
                fh.write("%s%s, /* %d */\n" % (stringfunc_prefix, cpu, i))
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
        args.all_cases = False
        args.monolithic = False

    pyx = PyxGenerator(args.monolithic, args.dev, args.all_cases)
    if args.cpu is None or args.cpu.lower() == "none":
        pass
    elif args.cpu:
        pyx.gen_cpu(args.cpu, args.py)
    else:
        pyx.gen_all()
    pyx.gen_others()

    if args.verbose:
        print("generated:\n", "\n".join(pyx.parse_name_list))
    pyx.gen_pyx()
