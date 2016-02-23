#!/usr/bin/env python
""" Brute force miniassembler, attempting to use pattern matching to determine
which opcode addressing mode to use.

"""
import os
import re
from collections import defaultdict

try:
    import cputables
except ImportError:
    raise RuntimeError("Generate cputables.py using cpugen.py before using the miniassembler")
# flags
pcr = 1
und = 2
r = 4
w = 8

class FormatSpec(object):
    fmtargre = re.compile(r'\{[0-9]:')

    def __init__(self, format, opcode, num_bytes, mode_name, flag):
        self.format = format
        self.mode_name = mode_name
        self.num_args = len(re.findall(self.fmtargre, format))
        self.length = len(format)
        self.opcode = opcode
        self.num_bytes = num_bytes
        self.flag = flag
    
    def __str__(self):
        return "%s: %s" % (self.mode_name, self.format)
    
    def __repr__(self):
        return "%s: %s" % (self.mode_name, self.format)
    
    def __lt__(self, other):
        # Only need to implement 'less than' for sorting to work
        return (self.length, self.format) < (other.length, other.format)
    
    def check_exact(self, operands):
        print "checking", self.mode_name, "for", self.format
        if self.format == operands:
            return [self.opcode]
    
    def check_hex(self, operands, pc, low_byte, high_byte):
        if self.num_args == 1 and self.flag == pcr:
            addr = low_byte + 256 * high_byte
            offset = addr - (pc + 2)
            print "checking", self.mode_name, "for relative branch to %04x (offset=%d)" % (addr, offset)
            if -128 <= offset <= 127:
                return [self.opcode, offset]
        elif self.num_args == 2:
            print "checking", self.mode_name, "for hex values %02x, %02x" % (low_byte, high_byte)
            gen = self.format.format(low_byte, high_byte)
            if gen == operands:
                return [self.opcode, low_byte, high_byte]

class BruteForceMiniAssembler(object):
    def __init__(self, cpu_name, allow_undocumented=False):
        self.source = None
        self.setup(cpu_name, allow_undocumented)
    
    def setup(self, cpu_name, allow_undocumented):
        cpu = cputables.processors[cpu_name]
        self.little = True  # all 8-bit processor little endian???
        formats = {}
        table = cpu['addressModeTable']
        for mode, fmt in table.iteritems():
            formats[mode] = fmt
            
        d = defaultdict(list)
        table = cpu['opcodeTable']
        for opcode, optable in table.iteritems():
            try:
                num_bytes, mnemonic, mode_name, flag = optable
            except ValueError:
                num_bytes, mnemonic, mode_name = optable
                flag = 0
            d[mnemonic].append(FormatSpec(formats[mode_name], opcode, num_bytes, mode_name, flag))
        self.ops = dict(d)  # convert to regular dict so unknown entries won't put new items into the dict
        self.ops = {}
        for mnemonic, modelist in d.iteritems():
            print mnemonic
            modelist.sort()
            print modelist
            self.ops[mnemonic] = modelist
        self.undocumented = allow_undocumented
    
    addrre = re.compile(r'\$[0-9a-fA-F]+')
    immediatere = re.compile(r'#?\$[0-9a-fA-F]+')
    
    def parse_operands(self, opstr, operands, pc):
        print operands
        format_specs = self.ops[opstr]
        
        # Check if a single operand matches an address mode exactly
        for f in format_specs:
            bytes = f.check_exact(operands)
            if bytes:
                return bytes
        
        # Check for hex value
        values = re.findall(self.addrre, operands)
        if values:
            print "HEX!", values
            num = len(values)
            
            if num == 1:
                v = int(values[0][1:], 16)
                vh, vl = divmod(v, 256)
                for f in format_specs:
                    bytes = f.check_hex(operands, pc, vl, vh)
                    if bytes:
                        return bytes
        
        return []
    
    def asm(self, origin, text):
        opstr, operands = text.lower().split(" ", 1)
        if ";" in operands:
            operands, _ = operands.split(";", 1)
        operands = operands.strip()
        print "-->%s<--, -->%s<--: %s" % (opstr, operands, self.ops[opstr])
        bytes = self.parse_operands(opstr, operands, origin)
        return bytes


if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("filename", help="Binary file to disassemble")
    parser.add_argument("-c", "--cpu", help="Specify CPU type (defaults to 6502)", default="6502")
    parser.add_argument("-u", "--undocumented", help="Allow undocumented opcodes", action="store_true")
    args = parser.parse_args()

    with open(args.filename, 'r') as fh:
        text = fh.read()

    miniasm = BruteForceMiniAssembler(args.cpu, allow_undocumented=args.undocumented)
    pc = 0
    for line in text.splitlines():
        if line.startswith("0x"):
            addr, line = line.split(" ", 1)
            addr = int(addr, 16)
            line = line.strip()
        else:
            addr = pc
        print "processing", line
        try:
            bytes = miniasm.asm(addr, line)
            print bytes
        except KeyError:
            print "unrecognized", line
            bytes = []
        pc += len(bytes)
