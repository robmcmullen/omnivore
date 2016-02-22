#!/usr/bin/env python
""" Python 2 version of udis

"""
import os
import glob

import numpy as np

# flags
pcr = 1
und = 2
r = 4
w = 8

def read_udis(pathname):
    """ Read all the processor-specific opcode info and pull into a container
    dictionary keyed on the processor name.
    
    The udis files have module level data, so this pulls the data from multiple
    cpus into a single structure that can then be refereced by processor name.
    For example, to find the opcode table in the generated dictionary for the
    6502 processor, use:
    
    cpus['6502']['opcodeTable']
    """
    files = glob.glob("%s/*.py" % pathname)
    cpus = {}
    for filename in files:
        with open(filename, "r") as fh:
            source = fh.read()
            if "addressModeTable" in source and "opcodeTable" in source:
                localfile = os.path.basename(filename)
                cpu_name, _ = os.path.splitext(localfile)
                g = {"pcr": 1}
                d = {}
                try:
                    exec(source, g, d)
                    if 'opcodeTable' in d:
                        cpus[cpu_name] = d
                except SyntaxError:
                    # ignore any python 3 files
                    pass
    return cpus


class Disassembler(object):
    supported_cpus = {}
    
    def __init__(self, cpu_name, memory_map=None, hex_lower=True, mnemonic_lower=False):
        self.source = None
        self.pc = 0
        self.pc_offset = 0
        self.origin = None
        if memory_map is not None:
            self.memory_map = memory_map
        else:
            self.memory_map = {}
        self.setup(cpu_name, hex_lower, mnemonic_lower)
    
    def setup(self, cpu_name, hex_lower, mnemonic_lower):
        cpu = self.supported_cpus[cpu_name]
        modes = {}
        table = cpu['addressModeTable']
        for mode, fmt in table.iteritems():
            if hex_lower:
                fmt = fmt.replace("%02X", "%02x").replace("%04X", "%04x")
            modes[mode] = fmt
        d = {}
        table = cpu['opcodeTable']
        for opcode, optable in table.iteritems():
            try:
                length, mnemonic, mode, flag = optable
            except ValueError:
                length, mnemonic, mode = optable
                flag = 0
            if not mnemonic_lower:
                mnemonic = mnemonic.upper()
            d[opcode] = (length, mnemonic, modes[mode], flag)
        self.ops = d
        self.leadin = cpu['leadInBytes']
        self.maxlen = cpu['maxLength']
        self.data_byte = ".db $%02" + ("x" if hex_lower else "X")
        
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
    
    def disasm(self):
        pc = self.pc
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
                length, opstr, fmt, flag = 0, self.data_byte % opcode, "", 0
            #print "0x%x" % opcode, fmt, length, opstr, mode, flag
            if leadin:
                extra = length - 2
            else:
                extra = length - 1
            
            next_pc = self.pc
            if extra == 1:
                operand1 = self.get_next()
                bytes.append(operand1)
                if flag == pcr:
                    signed = operand1 - 256 if operand1 > 127 else operand1
                    rel = pc + 2 + signed
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
            opstr, extra, rw = self.data_byte % opcode, 0, ""
            memloc = None
            dest_pc = None
        if flag == r:
            rw = "r"
        elif flag == w:
            rw = "w"
        else:
            rw = ""
        
        bytes = tuple(bytes)
        return pc, opcode, bytes, opstr, memloc, rw, dest_pc

    def get_disassembly(self):
        while True:
            addr, opcode, bytes, opstr, memloc, rw, dest_pc = self.disasm()
            comment = self.get_memloc_name(memloc, rw)
            flag = self.get_flag(opcode)
            yield (addr, bytes, opstr, comment, flag)
    
    def get_instruction(self):
        addr, opcode, bytes, opstr, memloc, rw, dest_pc = self.disasm()
        comment = self.get_memloc_name(memloc, rw)
        flag = self.get_flag(opcode)
        return (addr, bytes, opstr, comment, flag)
    
    def get_memloc_name(self, memloc, rw):
        if rw == "":
            return ""
        elif rw == "w" and -memloc in self.memory_map:
            return "; " + self.memory_map[-memloc]
        elif memloc in self.memory_map:
            return "; " + self.memory_map[memloc]
        return ""
    
    def get_flag(self, opcode):
        return 0


if __name__ == "__main__":
    import sys
    import argparse
    
    Disassembler.supported_cpus = read_udis(".")
    
    parser = argparse.ArgumentParser()
    parser.add_argument("filename", help="Binary file to disassemble")
    parser.add_argument("-c", "--cpu", help="Specify CPU type (defaults to 6502)", default="6502")
    args = parser.parse_args()

    with open(args.filename, 'rb') as fh:
        binary = fh.read()
    binary = np.fromstring(binary, dtype=np.uint8)
    print len(binary)
    
    pc = 0;
    disasm = Disassembler(args.cpu)
    disasm.set_pc(binary, 0)
    for addr, bytes, opstr, comment, flag in disasm.get_disassembly():
        print "0x%04x %-12s ; %s   %s %s" % (addr, opstr, comment, bytes, flag)
