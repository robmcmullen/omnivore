#!/usr/bin/env python

# 6502 disassembler based on opcode listing from http://www.emulator101.com/

import sys

import machine_atari800
import machine_atari5200

opdict = {
0x00: ("BRK", 0, ""),
0x01: ("ORA ($%02x,X)", 1, "r"),
0x05: ("ORA $%02x", 1, "r"),
0x06: ("ASL $%02x", 1, "w"),
0x08: ("PHP", 0, ""),
0x09: ("ORA #$%02x", 1, ""),
0x0a: ("ASL A", 0, ""),
0x0d: ("ORA $%02x%02x", 2, "r"),
0x0e: ("ASL $%02x%02x", 2, "w"),
0x10: ("BPL $%04x", -1, ""),
0x11: ("ORA ($%02x),Y", 1, "r"),
0x15: ("ORA $%02x,X", 1, "r"),
0x16: ("ASL $%02x,X", 1, "w"),
0x18: ("CLC", 0, ""),
0x19: ("ORA $%02x%02x,Y", 2, "r"),
0x1d: ("ORA $%02x%02x,X", 2, "r"),
0x1e: ("ASL $%02x%02x,X", 2, "w"),
0x20: ("JSR $%02x%02x", 2, "r"),
0x21: ("AND ($%02x,X)", 1, "r"),
0x24: ("BIT $%02x", 1, "r"),
0x25: ("AND $%02x", 1, "r"),
0x26: ("ROL $%02x", 1, "w"),
0x28: ("PLP", 0, ""),
0x29: ("AND #$%02x", 1, ""),
0x2a: ("ROL A", 0, ""),
0x2c: ("BIT $%02x%02x", 2, "r"),
0x2d: ("AND $%02x%02x", 2, "r"),
0x2e: ("ROL $%02x%02x", 2, "w"),
0x30: ("BMI $%04x", -1, ""),
0x31: ("AND ($%02x),Y", 1, "r"),
0x35: ("AND $%02x,X", 1, "r"),
0x36: ("ROL $%02x,X", 1, "w"),
0x38: ("SEC", 0, ""),
0x39: ("AND $%02x%02x,Y", 2, "r"),
0x3d: ("AND $%02x%02x,X", 2, "r"),
0x3e: ("ROL $%02x%02x,X", 2, "w"),
0x40: ("RTI", 0, ""),
0x41: ("EOR ($%02x,X)", 1, "r"),
0x45: ("EOR $%02x", 1, "r"),
0x46: ("LSR $%02x", 1, "w"),
0x48: ("PHA", 0, ""),
0x49: ("EOR #$%02x", 1, ""),
0x4a: ("LSR A", 0, ""),
0x4c: ("JMP $%02x%02x", 2, "r"),
0x4d: ("EOR $%02x%02x", 2, "r"),
0x4e: ("LSR $%02x%02x", 2, "t"),
0x50: ("BVC $%04x", -1, ""),
0x51: ("EOR ($%02x),Y", 1, "r"),
0x55: ("EOR $%02x,X", 1, "r"),
0x56: ("LSR $%02x,X", 1, "t"),
0x58: ("CLI", 0, ""),
0x59: ("EOR $%02x%02x,Y", 2, "r"),
0x5d: ("EOR $%02x%02x,X", 2, "r"),
0x5e: ("LSR $%02x%02x,X", 2, "t"),
0x60: ("RTS", 0, ""),
0x61: ("ADC ($%02x,X)", 1, "r"),
0x65: ("ADC $%02x", 1, "r"),
0x66: ("ROR $%02x", 1, "r"),
0x68: ("PLA", 0, ""),
0x69: ("ADC #$%02x", 1, ""),
0x6a: ("ROR A", 0, ""),
0x6c: ("JMP ($%02x%02x)", 2, "r"),
0x6d: ("ADC $%02x%02x", 2, "r"),
0x6e: ("ROR $%02x%02x,X", 2, "w"),
0x70: ("BVS $%04x", -1, ""),
0x71: ("ADC ($%02x),Y", 1, "r"),
0x75: ("ADC $%02x,X", 1, "r"),
0x76: ("ROR $%02x,X", 1, "w"),
0x78: ("SEI", 0, ""),
0x79: ("ADC $%02x%02x,Y", 2, "r"),
0x7d: ("ADC $%02x%02x,X", 2, "r"),
0x7e: ("ROR $%02x%02x", 2, "w"),
0x81: ("STA ($%02x,X)", 1, "w"),
0x84: ("STY $%02x", 1, "w"),
0x85: ("STA $%02x", 1, "w"),
0x86: ("STX $%02x", 1, "w"),
0x88: ("DEY", 0, ""),
0x8a: ("TXA", 0, ""),
0x8c: ("STY $%02x%02x", 2, "w"),
0x8d: ("STA $%02x%02x", 2, "w"),
0x8e: ("STX $%02x%02x", 2, "w"),
0x90: ("BCC $%04x", -1, ""),
0x91: ("STA ($%02x),Y", 1, "w"),
0x94: ("STY $%02x,X", 1, "w"),
0x95: ("STA $%02x,X", 1, "w"),
0x96: ("STX $%02x,Y", 1, "w"),
0x98: ("TYA", 0, ""),
0x99: ("STA $%02x%02x,Y", 2, "w"),
0x9a: ("TXS", 0, ""),
0x9d: ("STA $%02x%02x,X", 2, "w"),
0xa0: ("LDY #$%02x", 1, ""),
0xa1: ("LDA ($%02x,X)", 1, "r"),
0xa2: ("LDX #$%02x", 1, ""),
0xa4: ("LDY $%02x", 1, "r"),
0xa5: ("LDA $%02x", 1, "r"),
0xa6: ("LDX $%02x", 1, "r"),
0xa8: ("TAY", 0, ""),
0xa9: ("LDA #$%02x", 1, ""),
0xaa: ("TAX", 0, ""),
0xac: ("LDY $%02x%02x", 2, "r"),
0xad: ("LDA $%02x%02x", 2, "r"),
0xae: ("LDX $%02x%02x", 2, "r"),
0xb0: ("BCS $%04x", -1, ""),
0xb1: ("LDA ($%02x),Y", 1, "r"),
0xb4: ("LDY $%02x,X", 1, "r"),
0xb5: ("LDA $%02x,X", 1, "r"),
0xb6: ("LDX $%02x,Y", 1, "r"),
0xb8: ("CLV", 0, ""),
0xb9: ("LDA $%02x%02x,Y", 2, "r"),
0xba: ("TSX", 0, ""),
0xbc: ("LDY $%02x%02x,X", 2, "r"),
0xbd: ("LDA $%02x%02x,X", 2, "r"),
0xbe: ("LDX $%02x%02x,Y", 2, "r"),
0xc0: ("CPY #$%02x", 1, ""),
0xc1: ("CMP ($%02x,X)", 1, "r"),
0xc4: ("CPY $%02x", 1, "r"),
0xc5: ("CMP $%02x", 1, "r"),
0xc6: ("DEC $%02x", 1, "w"),
0xc8: ("INY", 0, ""),
0xc9: ("CMP #$%02x", 1, ""),
0xca: ("DEX", 0, ""),
0xcc: ("CPY $%02x%02x", 2, "r"),
0xcd: ("CMP $%02x%02x", 2, "r"),
0xce: ("DEC $%02x%02x", 2, "w"),
0xd0: ("BNE $%04x", -1, ""),
0xd1: ("CMP ($%02x),Y", 1, "r"),
0xd5: ("CMP $%02x,X", 1, "r"),
0xd6: ("DEC $%02x,X", 1, "w"),
0xd8: ("CLD", 0, ""),
0xd9: ("CMP $%02x%02x,Y", 2, "r"),
0xdd: ("CMP $%02x%02x,X", 2, "r"),
0xde: ("DEC $%02x%02x,X", 2, "w"),
0xe0: ("CPX #$%02x", 1, ""),
0xe1: ("SBC ($%02x,X)", 1, "r"),
0xe4: ("CPX $%02x", 1, "r"),
0xe5: ("SBC $%02x", 1, "r"),
0xe6: ("INC $%02x", 1, "w"),
0xe8: ("INX", 0, ""),
0xe9: ("SBC #$%02x", 1, ""),
0xea: ("NOP", 0, ""),
0xec: ("CPX $%02x%02x", 2, "r"),
0xed: ("SBC $%02x%02x", 2, "r"),
0xee: ("INC $%02x%02x", 2, "w"),
0xf0: ("BEQ $%04x", -1, ""),
0xf1: ("SBC ($%02x),Y", 1, "r"),
0xf5: ("SBC $%02x,X", 1, "r"),
0xf6: ("INC $%02x,X", 1, "w"),
0xf8: ("SED", 0, ""),
0xf9: ("SBC $%02x%02x,Y", 2, "r"),
0xfd: ("SBC $%02x%02x,X", 2, "r"),
0xfe: ("INC $%02x%02x,X", 2, "w"),
    }

class BaseDisassembler(object):
    menu_name = "Base Disassembler"
    
    memloc_name = {}
    
    def __init__(self, source, pc=0, pc_source_offset=0):
        self.set_pc(source, pc)
        self.pc_offset = pc_source_offset  # index into source array of pc
        self.origin = self.pc
        
    def set_pc(self, source, pc):
        self.source = source
        self.length = len(source)
        self.pc = pc
        
    def get_next(self):
        raise RuntimeError("abstract method")
    
    def disasm(self):
        pc = self.pc
        opcode = self.get_next()
        
        try:
            opstr, extra, rw = opdict[opcode]
        except KeyError:
            opstr, extra, rw = ".db $%02x" % opcode, 0, ""
        
        try:
            next_pc = self.pc
            if extra == 1:
                operand1 = self.get_next()
                bytes = (opcode, operand1)
                opstr = opstr % operand1
                memloc = operand1
                dest_pc = memloc
            elif extra == 2:
                operand1 = self.get_next()
                operand2 = self.get_next()
                bytes = (opcode, operand1, operand2)
                opstr = opstr % (operand2, operand1)
                memloc = operand1 + 256 * operand2
                dest_pc = memloc
            elif extra == -1:
                operand1 = self.get_next()
                bytes = (opcode, operand1)
                signed = operand1 - 256 if operand1 > 127 else operand1
                rel = pc + 2 + signed
                opstr = opstr % rel
                memloc = None
                dest_pc = rel
            else:
                bytes = (opcode,)
                memloc = None
                dest_pc = None
        except StopIteration:
            self.pc = next_pc
            opstr, extra, rw = ".db $%02x" % opcode, 0, ""
            bytes = (opcode,)
            memloc = None
            dest_pc = None
        
        return pc, bytes, opstr, memloc, rw, dest_pc

    def get_disassembly(self):
        while True:
            addr, bytes, opstr, memloc, rw, dest_pc = self.disasm()
            comment = self.get_memloc_name(memloc, rw)
            yield (addr, bytes, opstr, comment)
    
    def get_instruction(self):
        addr, bytes, opstr, memloc, rw, dest_pc = self.disasm()
        comment = self.get_memloc_name(memloc, rw)
        return (addr, bytes, opstr, comment)
    
    def get_memloc_name(self, memloc, rw):
        if rw == "":
            return ""
        elif rw == "w" and -memloc in self.memloc_name:
            return "; " + self.memloc_name[-memloc]
        elif memloc in self.memloc_name:
            return "; " + self.memloc_name[memloc]
        return ""

class TextDisassembler(BaseDisassembler):
    def get_next(self):
        if self.pc >= self.origin + self.length:
            raise StopIteration
        opcode = ord(self.source[self.pc + self.pc_offset])
        self.pc += 1
        return opcode

class Basic6502Disassembler(BaseDisassembler):
    menu_name = "Generic 6502"
    
    def set_source(self, source):
        self.source = source
        self.length = source.size
        
    def get_next(self):
        if self.pc >= self.origin + self.length:
            raise StopIteration
        opcode = int(self.source[self.pc + self.pc_offset])
        self.pc += 1
        return opcode

class Atari800Disassembler(Basic6502Disassembler):
    menu_name = "Atari 800"
    
    memloc_name = machine_atari800.memmap

class Atari5200Disassembler(Basic6502Disassembler):
    menu_name = "Atari 5200"
    
    memloc_name = machine_atari5200.memmap


if __name__ == "__main__":
    with open(sys.argv[1], 'rb') as fh:
        binary = fh.read()
    print len(binary)
    
    pc = 0;
    disasm = TextDisassembler(binary, pc)
    for line in disasm.get_disassembly():
        print line
