#!/usr/bin/env python

# 6502 disassembler based on opcode listing from http://www.emulator101.com/

import sys

import machine_atari800
import machine_atari5200

documented_mnemonics = {
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

# Undocumented instructions from http://nesdev.com/undocumented_opcodes.txt
undocumented_mnemonics = {
0x0b: ("AAC #$%02x", 1, ""),
0x2b: ("AAC #$%02x", 1, ""),
0x87: ("SAX $%02x", 1, "w"),
0x97: ("SAX $%02x,Y", 1, "r"),
0x83: ("SAX ($%02x,X)", 1, "r"),
0x8f: ("SAX $%02x%02x", 2, "r"),
0x6b: ("ARR #$%02x", 1, ""),
0x4b: ("ASR #$%02x", 1, ""),
0xab: ("ATX #$%02x", 1, ""),
0x9f: ("SHA $%02x%02x,Y", 2, "w"),
0x93: ("SHA ($%02x),Y", 1, "w"),
0xcb: ("SBX #$%02x", 1, ""),
0xc7: ("DCP $%02x", 1, "w"),
0x95: ("DCP $%02x,X", 1, "w"),
0xcf: ("DCP $%02x%02x", 2, "w"),
0xdf: ("DCP $%02x%02x,X", 2, "w"),
0xdb: ("DCP $%02x%02x,Y", 2, "w"),
0xc3: ("DCP ($%02x,X)", 1, "w"),
0xd3: ("DCP ($%02x),Y", 1, "w"),
0x04: ("DOP $%02x", 1, ""),
0x14: ("DOP $%02x,X", 1, ""),
0x34: ("DOP $%02x,X", 1, ""),
0x44: ("DOP $%02x", 1, ""),
0x54: ("DOP $%02x,X", 1, ""),
0x64: ("DOP $%02x", 1, ""),
0x74: ("DOP $%02x,X", 1, ""),
0x80: ("DOP #$%02x", 1, ""),
0x82: ("DOP #$%02x", 1, ""),
0x89: ("DOP #$%02x", 1, ""),
0xc2: ("DOP #$%02x", 1, ""),
0xd4: ("DOP $%02x,X", 1, ""),
0xe2: ("DOP #$%02x", 1, ""),
0xf4: ("DOP $%02x,X", 1, ""),
0xe7: ("ISB $%02x", 1, "w"),
0xf7: ("ISB $%02x,X", 1, "w"),
0xef: ("ISB $%02x%02x", 2, "w"),
0xff: ("ISB $%02x%02x,X", 2, "w"),
0xfb: ("ISB $%02x%02x,Y", 2, "w"),
0xe3: ("ISB ($%02x,X)", 1, "w"),
0xf3: ("ISB ($%02x),Y", 1, "w"),
0x02: ("HLT", 0, ""),
0x12: ("HLT", 0, ""),
0x22: ("HLT", 0, ""),
0x32: ("HLT", 0, ""),
0x42: ("HLT", 0, ""),
0x52: ("HLT", 0, ""),
0x62: ("HLT", 0, ""),
0x72: ("HLT", 0, ""),
0x92: ("HLT", 0, ""),
0xb2: ("HLT", 0, ""),
0xd2: ("HLT", 0, ""),
0xf2: ("HLT", 0, ""),
0xbb: ("LAR $%02x%02x,Y", 2, "w"),
0xa7: ("LAX $%02x", 1, "w"),
0xb7: ("LAX $%02x,Y", 1, "w"),
0xaf: ("LAX $%02x%02x", 2, "w"),
0xbf: ("LAX $%02x%02x,Y", 2, "w"),
0xa3: ("LAX ($%02x,X)", 1, "w"),
0xb3: ("LAX ($%02x),Y", 1, "w"),
0x1a: ("NOP", 0, ""),
0x3a: ("NOP", 0, ""),
0x5a: ("NOP", 0, ""),
0x7a: ("NOP", 0, ""),
0xda: ("NOP", 0, ""),
0xfa: ("NOP", 0, ""),
0x27: ("RLA $%02x", 1, "w"),
0x37: ("RLA $%02x,X", 1, "w"),
0x2f: ("RLA $%02x%02x", 2, "w"),
0x3f: ("RLA $%02x%02x,X", 2, "w"),
0x3b: ("RLA $%02x%02x,Y", 2, "w"),
0x23: ("RLA ($%02x,X)", 1, "w"),
0x23: ("RLA ($%02x),Y", 1, "w"),
0x67: ("RRA $%02x", 1, "w"),
0x77: ("RRA $%02x,X", 1, "w"),
0x6f: ("RRA $%02x%02x", 2, "w"),
0x7f: ("RRA $%02x%02x,X", 2, "w"),
0x7b: ("RRA $%02x%02x,Y", 2, "w"),
0x63: ("RRA ($%02x,X)", 1, "w"),
0x73: ("RRA ($%02x),Y", 1, "w"),
0xeb: ("SBC #$%02x", 1, ""),
0x07: ("SLO $%02x", 1, "w"),
0x17: ("SLO $%02x,X", 1, "w"),
0x0f: ("SLO $%02x%02x", 2, "w"),
0x1f: ("SLO $%02x%02x,X", 2, "w"),
0x1b: ("SLO $%02x%02x,Y", 2, "w"),
0x03: ("SLO ($%02x,X)", 1, "w"),
0x13: ("SLO ($%02x),Y", 1, "w"),
0x47: ("SRE $%02x", 1, "w"),
0x57: ("SRE $%02x,X", 1, "w"),
0x4f: ("SRE $%02x%02x", 2, "w"),
0x5f: ("SRE $%02x%02x,X", 2, "w"),
0x5b: ("SRE $%02x%02x,Y", 2, "w"),
0x43: ("SRE ($%02x,X)", 1, "w"),
0x53: ("SRE ($%02x),Y", 1, "w"),
0x9e: ("SHX $%02x%02x,Y", 2, "w"),
0x9c: ("SHY $%02x%02x,X", 2, "w"),
0x0c: ("TOP $%02x%02x", 2, "r"),
0x1c: ("TOP $%02x%02x,X", 2, "r"),
0x3c: ("TOP $%02x%02x,X", 2, "r"),
0x5c: ("TOP $%02x%02x,X", 2, "r"),
0x7c: ("TOP $%02x%02x,X", 2, "r"),
0xdc: ("TOP $%02x%02x,X", 2, "r"),
0xfc: ("TOP $%02x%02x,X", 2, "r"),
0x8b: ("XAA #$%02x", 1, ""),
0x9b: ("SHS $%02x%02x,Y", 2, "w"),
}

class BaseDisassembler(object):
    mnemonics = documented_mnemonics
    
    def __init__(self, memory_map=None, hex_lower=True, mnemonic_lower=False):
        self.source = None
        self.pc = 0
        self.pc_offset = 0
        self.origin = None
        if memory_map is not None:
            self.memory_map = memory_map
        else:
            self.memory_map = {}
        self.get_opdict(hex_lower, mnemonic_lower)
    
    def get_opdict(self, hex_lower, mnemonic_lower):
        d = {}
        for byte, (opstr, extra, rw) in self.mnemonics.iteritems():
            if " " in opstr:
                op, addr = opstr.split(" ", 1)
                if mnemonic_lower:
                    op = op.lower()
                if not hex_lower:
                    addr = addr.replace("%02x", "%02X").replace("%04x", "%04X")
                opstr = op + " " + addr
            elif mnemonic_lower:
                opstr = opstr.lower()
            d[byte] = opstr, extra, rw
        self.opdict = d
        self.data_byte = ".db $%02" + ("x" if hex_lower else "X")
        
    def set_pc(self, source, pc):
        self.source = source
        self.length = len(source)
        self.pc = pc
        if self.origin is None:
            self.origin = pc
            self.pc_offset = -pc  # index into source array of pc
        
    def get_next(self):
        raise RuntimeError("abstract method")
    
    def disasm(self):
        pc = self.pc
        opcode = self.get_next()
        
        try:
            opstr, extra, rw = self.opdict[opcode]
        except KeyError:
            opstr, extra, rw = self.data_byte % opcode, 0, ""
        
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
            opstr, extra, rw = self.data_byte % opcode, 0, ""
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
        elif rw == "w" and -memloc in self.memory_map:
            return "; " + self.memory_map[-memloc]
        elif memloc in self.memory_map:
            return "; " + self.memory_map[memloc]
        return ""


class Basic6502Disassembler(BaseDisassembler):
    def get_next(self):
        if self.pc >= self.origin + self.length:
            raise StopIteration
        opcode = int(self.source[self.pc + self.pc_offset])
        self.pc += 1
        return opcode


class Undocumented6502Disassembler(Basic6502Disassembler):
    mnemonics = dict(documented_mnemonics)
    mnemonics.update(undocumented_mnemonics)


if __name__ == "__main__":
    with open(sys.argv[1], 'rb') as fh:
        binary = fh.read()
    print len(binary)
    
    pc = 0;
    disasm = Basic6502Disassembler(binary, pc)
    for line in disasm.get_disassembly():
        print line
