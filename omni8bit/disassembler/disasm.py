import os
import glob

import numpy as np

from . import cputables
from .flags import *
from . import dtypes as ud
from . import libudis


class ParsedDisassembly(libudis.ParsedDisassembly):
    @property
    def entries(self):
        return self.raw_entries.view(dtype=ud.HISTORY_ENTRY_DTYPE)


class DisassemblyConfig(libudis.DisassemblyConfig):
    def get_parser(self, num_entries, origin, num_bytes):
        return ParsedDisassembly(num_entries, origin, num_bytes)


class Disassembler(object):
    def __init__(self, cpu_name, asm_syntax=None, memory_map=None, allow_undocumented=False, hex_lower=True, mnemonic_lower=False, r_mnemonics=None, w_mnemonics=None, rw_modes=None):
        self.source = None
        self.pc = 0
        self.pc_offset = 0
        self.origin = None
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
    
    def setup(self, cpu_name, allow_undocumented, r_mnemonics, w_mnemonics, rw_modes):
        cpu = cputables.processors[cpu_name]
        modes = {}
        table = cpu['addressModeTable']
        if rw_modes is None:
            rw_modes = set()
        for mode, fmt in list(table.items()):
            if self.hex_lower:
                fmt = fmt.replace(":02X", ":02x").replace(":04X", ":04x")
            modes[mode] = fmt
        d = {}
        table = cpu['opcodeTable']
        for opcode, optable in list(table.items()):
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
            d[opcode] = (length, mnemonic, modes[mode], flag)
        self.ops = d
        self.leadin = cpu['leadInBytes']
        self.maxlen = cpu['maxLength']
        self.undocumented = allow_undocumented
    
    def get_data_byte_string(self, bytes):
        fmt = "$%02" + ("x" if self.hex_lower else "X")
        text = ",".join([fmt % b for b in bytes])
        return "%s %s" % (self.data_byte_opcode, text)
        
    def set_pc(self, source, pc):
        self.source = source
        self.length = len(source)
        self.pc = pc
        if self.origin is None:
            self.origin = pc
            self.pc_offset = -pc  # index into source array of pc
        
    def get_next(self):
        if self.pc >= self.origin + self.length:
            raise StopIteration
        opcode = int(self.source[self.pc + self.pc_offset])
        self.pc += 1
        return opcode
    
    def put_back(self):
        self.pc -= 1
    
    def get_style(self):
        return 0
    
    def is_data(self):
        """Check if the current PC location is a data byte"""
        return False
    
    def is_same_data_style(self, style, first_style, bytes):
        """Check if current PC is the same style of data as the first data byte
        in this block of data
        """
        return style == first_style
    
    def get_data_comment(self, style, bytes):
        comment = "%s $%x data byte" % (self.comment_char, len(bytes))
        if len(bytes) > 1:
            comment += "s"
        return comment
    
    def disasm_data(self):
        pc = self.pc
        # Read first byte to allow for StopIteration to signal end of file
        first_style = self.get_style()
        opcode = self.get_next()
        bytes = [opcode]
        try:
            # after first byte, read until bytes run out, end of data region,
            # or comment within data region
            while True:
                next_style = self.get_style()
                opcode = self.get_next()
                bytes.append(opcode)
                if not self.is_same_data_style(next_style, first_style, bytes):
                    self.put_back()
                    bytes.pop()
                    break
        except StopIteration:
            pass
        opstr = self.get_data_byte_string(bytes)
        comment = self.get_data_comment(first_style, bytes)
        return pc, bytes, opstr, comment, 0, None
    
    def disasm(self):
        pc = self.pc
        if self.is_data():
            return self.disasm_data()
        opcode = self.get_next()
        bytes = [opcode]
        
        try:
            # Handle if opcode is a leadin byte
            if opcode in self.leadin:
                next_pc = self.pc
                opcode2 = self.get_next()
                bytes.append(opcode2)
                opcode = (opcode << 8) + opcode2
                leadin = True
            else:
                leadin = False

            try:
                length, opstr, fmt, flag = self.ops[opcode]
            except KeyError:
                if len(bytes) == 2:
                    self.put_back()
                    opcode = bytes[0]
                    bytes = (opcode, )
                length, opstr, fmt, flag = 0, self.get_data_byte_string([opcode]), "", 0
            #print("0x%x" % opcode, fmt, length, opstr, mode, flag)
            if leadin:
                extra = length - 2
            else:
                extra = length - 1
        
            if flag & und and not self.undocumented:
                if len(bytes) == 2:
                    self.put_back()
                    opcode = bytes[0]
                    bytes = (opcode, )
                extra, opstr, fmt, flag = 0, self.get_data_byte_string([opcode]), "", 0
            
            next_pc = self.pc
            if extra == 1:
                operand1 = self.get_next()
                bytes.append(operand1)
                if flag & pcr:
                    signed = operand1 - 256 if operand1 > 127 else operand1
                    rel = (pc + 2 + signed) & 0xffff  # limit to 64k address space
                    opstr = opstr + " " + fmt.format(rel)
                    memloc = rel
                    dest_pc = rel
                else:
                    opstr = opstr + " " + fmt.format(operand1)
                    memloc = operand1
                    dest_pc = memloc
            elif extra == 2:
                operand1 = self.get_next()
                bytes.append(operand1)
                operand2 = self.get_next()
                bytes.append(operand2)
                if flag & z80bit:
                    opcode = (opcode << 16) + operand2
                    # reread opcode table for real format string
                    length, opstr, fmt, flag = self.ops[opcode]
                    signed = operand1 - 256 if operand1 > 127 else operand1
                    opstr = opstr + " " + fmt.format(signed)
                    memloc = None
                elif flag & pcr:
                    addr = operand1 + 256 * operand2
                    signed = addr - 0x10000 if addr > 32768 else addr
                    rel = (pc + 2 + signed) & 0xffff  # limit to 64k address space
                    memloc = rel
                    dest_pc = rel
                    try:
                        opstr = opstr + " " + fmt.format(rel)
                    except IndexError:
                        # maybe it's the 65c02 zeropagerelative where it's
                        # actually two separate operands
                        signed = operand2 - 256 if operand2 > 127 else operand2
                        rel = (pc + 2 + signed) & 0xffff  # limit to 64k address space
                        opstr = opstr + " " + fmt.format(operand1, rel)
                        memloc = rel
                        dest_pc = rel
                else:
                    opstr = opstr + " " + fmt.format(operand1, operand2)
                    memloc = operand1 + 256 * operand2
                dest_pc = memloc
            elif extra == 3:
                operand1 = self.get_next()
                bytes.append(operand1)
                operand2 = self.get_next()
                bytes.append(operand2)
                operand3 = self.get_next()
                bytes.append(operand3)
                opstr = opstr + " " + fmt.format(operand1, operand2, operand3)
                memloc = operand1 + 256 * operand2 + 256 * 256 * operand3
                dest_pc = memloc
            else:
                if fmt:
                    opstr = opstr + " " + fmt
                memloc = None
                dest_pc = None
            
        except StopIteration:
            self.pc = next_pc
            opstr, extra, flag = self.get_data_byte_string([opcode]), 0, 0
            memloc = None
            dest_pc = None
        if flag & r:
            rw = "r"
        elif flag & w:
            rw = "w"
        else:
            rw = ""
        
        bytes = tuple(bytes)
        comment = self.get_memloc_name(memloc, rw)
        is_und = self.flag_as_undefined(flag)
        return pc, bytes, opstr, comment, is_und, dest_pc
    
    get_instruction = disasm

    def get_disassembly(self):
        while True:
            result = self.disasm()
            print(f"disassembly result: {result}")
            yield result
    
    def get_memloc_name(self, memloc, rw):
        if rw == "" or self.memory_map is None:
            return ""
        flag = rw == "w"
        name = self.memory_map.get_name(memloc, flag)
        if name:
            return self.comment_char + " " + name
        return ""
    
    def flag_as_undefined(self, flag):
        return False


if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--cpu", help="Specify CPU type (defaults to 6502)", default="6502")
    parser.add_argument("-u", "--undocumented", help="Allow undocumented opcodes", action="store_true")
    parser.add_argument("-x", "--hex", help="Disassemble a string version of hex digits")
    parser.add_argument("filenames", metavar="filenames", nargs='*',
                   help="Binary files(s) to disassemble")
    args = parser.parse_args()

    def process(binary):
        pc = 0;
        disasm = Disassembler(args.cpu, allow_undocumented=args.undocumented)
        disasm.set_pc(binary, 0)
        for addr, bytes, opstr, comment, flag, dest_pc in disasm.get_disassembly():
            print("0x%04x %-12s ; %s   %s %s" % (addr, opstr, comment, bytes, flag))

    if args.hex:
        try:
            binary = args.hex.decode("hex")
        except TypeError:
            print("Invalid hex digits!")
            sys.exit()
        binary = np.fromstring(binary, dtype=np.uint8)
        process(binary)
    else:
        for filename in args.filenames:
            with open(filename, 'rb') as fh:
                binary = fh.read()
            binary = np.fromstring(binary, dtype=np.uint8)
            process(binary)
