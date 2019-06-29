#!/usr/bin/env python
""" Mini-assembler that uses the formatting strings and opcode tables from
udis (the Universal Disassembler for 8-bit microprocessors by Jeff Tranter) to
perform pattern matching to determine the opcode and addressing mode.

Copyright (c) 2016 by Rob McMullen <feedback@playermissile.com>
Licensed under the Apache License 2.0
"""


import os
import re
from collections import defaultdict

import numpy as np

try:
    from .cputables import processors
except ImportError:
    raise RuntimeError("Generate cputables.py using cpugen.py before using the miniassembler")

from .disasm import DisassemblyConfig
from .flags import pcr, z80bit

import logging
logging.basicConfig(level=logging.WARNING)
log = logging.getLogger(__name__)


valid_cpus = sorted([k for k in processors.keys() if processors[k]['nop'] >= 0])


class FormatSpec(object):
    """ Format specifier that combines info from the udis addressModeTable and
    the opcodeTable.
    
    During the brute force decoding, the patterns contained in the
    addressModeTable format string are checked against the arguments decoded
    from the text to be assembled. The first match is returned as the
    assembled bytes.
    """
    
    # regex to find the argument number in the format string
    fmtargre = re.compile(r'\{[0-9]:')

    def __init__(self, format, opcode, num_bytes, mode_name, flag):
        self.format = format
        self.mode_name = mode_name
        self.num_args = len(re.findall(self.fmtargre, format))
        self.length = len(format)
        if opcode is not None:
            if opcode >= 256 * 256 * 256:
                op1 = (opcode & 0xff000000) >> 24
                op2 = (opcode & 0xff0000) >> 16
                op3 = (opcode & 0xff00) >> 8
                op4 = opcode & 0xff
                self.opcode_bytes = [op1, op2, op3, op4]
            elif opcode > 255:
                op1, op2 = divmod(opcode, 256)
                self.opcode_bytes = [op1, op2]
            else:
                self.opcode_bytes = [opcode]
        else:
            self.opcode_bytes = []
        self.num_bytes = num_bytes
        self.flag = flag
    
    def __str__(self):
        return "%s: %s" % (self.mode_name, self.format)
    
    def __repr__(self):
        return "%s: %s" % (self.mode_name, self.format)
    
    def __lt__(self, other):
        # Only need to implement 'less than' for sorting to work
        return (self.length, self.format) < (other.length, other.format)
    
    def get_bytes(self, data=None):
        out = list(self.opcode_bytes)
        if data is not None:
            out.extend(data)
        return tuple(out)
    
    def check_exact(self, operands):
        """ Check all the format strings that have no extra arguments, like
        "NOP" or even 6502's "ASL A"
        
        """
        log.debug(" check_exact: %s -> %s" % (self.mode_name, self.format))
        if self.format == operands:
            return self.get_bytes()
    
    def check_hex_1x8(self, operands, pc, byte):
        """ Check all the format strings that have one 8-bit hex value
        
        """
        if self.num_args == 0:
            # z80 has some hardcoded values in static opcodes, like $ff = "rst
            # $38" that get parsed as an opcode and a byte value, so we ignore
            # the byte value here because of it being hardcoded.
            gen = self.format
            log.debug(" check_hex_1x8(0): " + gen + " -> " + operands)
            if gen == operands:
                return self.get_bytes()
        elif self.num_args == 1:
            gen = self.format.format(byte)
            log.debug(" check_hex_1x8(1): " + gen + " -> " + operands)
            if gen == operands:
                if self.flag & z80bit:
                    out = list(self.opcode_bytes)
                    out[2:3] = [byte]
                    return tuple(out)
                else:
                    return self.get_bytes([byte])
    
    def check_hex_1x16(self, operands, pc, low_byte, high_byte):
        """ Check all the format strings that have one 16-bit hex value,
        typically the PC-relative instructions.
        
        """
        if self.flag & pcr:
            addr = low_byte + 256 * high_byte
            offset = addr - (pc + 2)
            # offset is limited by signed 16 bit size, so find the positive or
            # negative value that clamps to that range
            if offset > 32767:
                offset -= 0x10000
            elif offset < -32768:
                offset += 0x10000
            if self.num_bytes == 2:
                log.debug(" check_hex_1x16(1): %s -> %04x (pc=%x, offset=%x)" % (self.mode_name, addr, pc, offset))
                if -128 <= offset <= 127:
                    gen = self.format.format(addr)
                    log.debug("  gen=%s operands=%s" % (gen, operands))
                    if gen == operands:
                        return self.get_bytes([offset & 0xff])  # convert to unsigned representation
            elif self.num_bytes == 3:
                log.debug(" check_hex_1x16(2): %s -> %04x (pc=%x, offset=%x)" % (self.mode_name, addr, pc, offset))
                if -32768 <= offset <= 32767:
                    gen = self.format.format(addr)
                    log.debug("  gen=%s operands=%s" % (gen, operands))
                    if gen == operands:
                        unsigned = offset & 0xffff  # convert to unsigned representation
                        high, low = divmod(unsigned, 256)
                        return self.get_bytes([low, high])
    
    def check_hex_2x8(self, operands, pc, low_byte, high_byte):
        """ Check all the format strings that have two 8-bit hex values
        
        """
        if self.num_args == 2:
            log.debug(" check_hex_2x8(2): %s -> %02x, %02x" % (self.mode_name, low_byte, high_byte))
            gen = self.format.format(low_byte, high_byte)
            log.debug("  " + gen + ":" + operands)
            if gen == operands:
                return self.get_bytes([low_byte, high_byte])
    
    def check_hex_3x8(self, operands, pc, low_byte, high_byte, bank_byte):
        """ Check all the format strings that have two 8-bit hex values
        
        """
        if self.num_args == 3:
            log.debug(" check_hex_3x8(3): %s -> %02x, %02x, %02x" % (self.mode_name, low_byte, high_byte, bank_byte))
            gen = self.format.format(low_byte, high_byte, bank_byte)
            log.debug("  " + gen + ":" + operands)
            if gen == operands:
                return self.get_bytes([low_byte, high_byte, bank_byte])


class MiniAssembler(object):
    def __init__(self, cpu_name):
        self.source = None
        self.setup(cpu_name)
    
    def setup(self, cpu_name):
        """ Create the opcode lookup tables that store all the possible
        addressing modes for each opcode.
        """
        cpu = processors[cpu_name]
        self.little = True  # all 8-bit processors little endian???
        
        # Create temporary format dictionary that will be used in the expanded
        # opcode lookup table
        formats = {}
        table = cpu['addressModeTable']
        for mode, fmt in list(table.items()):
            formats[mode] = fmt.lower()
        
        # Create the opcode lookup table that holds a list of possible
        # addressing modes for each opcode. Stores the addressing mode format
        # in each list entry to eliminate a lookup to another table at the
        # cost of some extra space in this lookup table.
        d = defaultdict(list)
        table = cpu['opcodeTable']
        for opcode, optable in list(table.items()):
            try:
                num_bytes, mnemonic, mode_name, flag = optable
            except ValueError:
                num_bytes, mnemonic, mode_name = optable
                flag = 0
            log.debug("%x: %s, %s, %d bytes, %x" % (opcode, mnemonic, mode_name, num_bytes, flag))
            d[mnemonic].append(FormatSpec(formats[mode_name], opcode, num_bytes, mode_name, flag))
        d[".db"].append(FormatSpec("${0:02x}", None, 1, "data_byte", 0))
        
        # Order the lookup table from smallest to largest format specifier for
        # each opcode
        self.ops = {}
        for mnemonic, modelist in sorted(d.items()):
            modelist.sort()
            log.debug("%s: %s" % (mnemonic, modelist))
            self.ops[mnemonic] = modelist

        # Create lookup set to quickly determine if a character can start an
        # opcode (both character and ordinal value of char are valid)
        self.start_char_in_op = set()
        for mnemonic in self.ops.keys():
            self.start_char_in_op.add(mnemonic[0])
            self.start_char_in_op.add(ord(mnemonic[0]))
    
    addrre = re.compile(r'\$[0-9a-fA-F]+')
    immediatere = re.compile(r'#?\$[0-9a-fA-F]+')
    
    def parse_operands(self, opstr, operands, pc):
        try:
            format_specs = self.ops[opstr]
        except KeyError:
            raise RuntimeError("Unknown mnemonic %s" % opstr)
        log.debug("-->%s<--, -->%s<--: %s" % (opstr, operands, self.ops[opstr]))
        
        # Check if a single operand matches an address mode exactly
        for f in format_specs:
            data = f.check_exact(operands)
            if data:
                return data
        
        # Check for hex value
        values = re.findall(self.addrre, operands)
        if values:
            log.debug("HEX!: %s" % str(values))
            num = len(values)
            
            if num == 1:
                hexstr = values[0][1:]
                v = int(hexstr, 16)
                if len(hexstr) == 1 or len(hexstr) == 2:
                    for f in format_specs:
                        data = f.check_hex_1x8(operands, pc, v)
                        if data:
                            return data
                if len(hexstr) > 4:
                    vh, vl = divmod(v, 256)
                    vb, vh = divmod(vh, 256)
                    for f in format_specs:
                        data = f.check_hex_3x8(operands, pc, vl, vh, vb)
                        if data:
                            return data
                elif len(hexstr) > 2:
                    vh, vl = divmod(v, 256)
                    for f in format_specs:
                        data = f.check_hex_1x16(operands, pc, vl, vh)
                        if data:
                            return data
                        data = f.check_hex_2x8(operands, pc, vl, vh)
                        if data:
                            return data
            elif num == 2:
                hexstr = values[0][1:]
                vl = int(hexstr, 16)
                hexstr = values[1][1:]
                vh = int(hexstr, 16)
                for f in format_specs:
                    data = f.check_hex_2x8(operands, pc, vl, vh)
                    if data:
                        return data
        
        return []
    
    def asm(self, origin, text):
        text = text.lower()
        log.debug("input: %s" % text)
        if " " in text:
            opstr, operands = text.split(" ", 1)
        else:
            opstr = text
            operands = ""
        if ";" in operands:
            operands, _ = operands.split(";", 1)
        operands = operands.replace(" ", "")
        opstr = opstr.lower()
        operands = operands.strip()
        log.debug(f"op: {opstr} operands: {operands}, origin: {origin}")
        data = self.parse_operands(opstr, operands, origin)
        return data

    def can_start_edit(self, c):
        """Return True if the specified character is the start of an assembler
        command
        """
        return c in self.start_char_in_op



_miniassemblers = {}

def get_miniasm(cpu):
    global _miniassemblers

    if cpu not in _miniassemblers:
        m = MiniAssembler(cpu)
        _miniassemblers[cpu] = m
    return _miniassemblers[cpu]


def process(cpu, line, pc):
    miniasm = get_miniasm(cpu)
    if line.startswith("0x"):
        addr, line = line.split(" ", 1)
        addr = int(addr, 16)
        line = line.strip()
    else:
        addr = pc
    try:
        data = miniasm.asm(addr, line)
        log.debug(data)
    except KeyError:
        log.debug("unrecognized", line)
        data = []
    print("%s: output=%s" % (line, str(data)))
    return data
