from udis import miniasm, cputables
import udis.udis_fast

from atrcopy import match_bit_mask, comment_bit_mask, selected_bit_mask, user_bit_mask

from memory_map import EmptyMemoryMap


class BaseDisassembler(object):
    name = "generic disassembler"
    cpu = "undefined"
    read_instructions = set()
    write_instructions = set()
    rw_modes = set()
    default_assembler = {
        'comment char': ';',
        'origin': '*=',
        'data byte': '.byte',
        'name': "MAC/65",
        }
    
    cached_miniassemblers = {}
    
    def __init__(self, asm_syntax=None, memory_map=None, hex_lower=True, mnemonic_lower=False, byte_mnemonic=".byte"):
        if asm_syntax is None:
            asm_syntax = self.default_assembler
        self.hex_lower = hex_lower
        self.mnemonic_lower = mnemonic_lower
        if mnemonic_lower:
            case_func = lambda a:a.lower()
        else:
            case_func = lambda a:a.upper()
        self.data_byte_opcode = case_func(asm_syntax['data byte'])
        self.asm_origin = case_func(asm_syntax['origin'])
        self.comment_char = case_func(asm_syntax['comment char'])
        self.fast = udis.udis_fast.DisassemblerWrapper(self.cpu, fast=True, mnemonic_lower=mnemonic_lower, hex_lower=hex_lower)
        self.memory_map = memory_map if memory_map is not None else memory_map.EmptyMemoryMap()

    @classmethod
    def get_nop(cls):
        cpu = cputables.processors[cls.cpu]
        return cpu['nop']
    
    @classmethod
    def get_miniassembler(cls, cpu):
        if not cpu in cls.cached_miniassemblers:
            asm = miniasm.MiniAssembler(cpu)
            cls.cached_miniassemblers[cpu] = asm

        return cls.cached_miniassemblers[cpu]
    
    def assemble_text(self, pc, cmd):
        miniasm = self.get_miniassembler(self.cpu)
        bytes = miniasm.asm(pc, cmd)
        if not bytes:
            raise RuntimeError("Unknown addressing mode")
        return bytes


class Basic6502Disassembler(BaseDisassembler):
    name = "6502"
    cpu = "6502"
    read_instructions = {"adc", "and", "asl", "bit", "cmp", "cpx", "cpy", "dec", "eor", "inc", "lda", "ldx", "ldy", "lsr", "ora", "rol", "ror", "sbc", "jsr", "jmp"}
    write_instructions = {"sax", "shx", "shy", "slo", "sre", "sta", "stx", "sty"}
    rw_modes = {"absolute", "absolutex", "absolutey", "indirect", "indirectx", "indirecty", "relative", "zeropage", "zeropagex", "zeropagey"}


class Undocumented6502Disassembler(Basic6502Disassembler):
    name = "6502 (with undocumented opcodes)"
    cpu = "6502undoc"


class Flagged6502Disassembler(Undocumented6502Disassembler):
    name = "6502 (highlighted undocumented opcodes)"
    
    def get_flag(self, flag):
        return flag & disasm.und


class Basic65C02Disassembler(Basic6502Disassembler):
    name = "65c02"
    cpu = "65c02"


class Basic65816Disassembler(Basic6502Disassembler):
    name = "65816"
    cpu = "65816"


class Basic6800Disassembler(BaseDisassembler):
    name = "6800"
    cpu = "6800"


class Basic6809Disassembler(BaseDisassembler):
    name = "6809"
    cpu = "6809"


class Basic6811Disassembler(BaseDisassembler):
    name = "6811"
    cpu = "6811"


class Basic8051Disassembler(BaseDisassembler):
    name = "8051"
    cpu = "8051"


class Basic8080Disassembler(BaseDisassembler):
    name = "8080"
    cpu = "8080"


class BasicZ80Disassembler(BaseDisassembler):
    name = "Z80"
    cpu = "z80"

# Style numbers for other disassemblers
ANTIC_DISASM = 2
JUMPMAN_LEVEL = 3
JUMPMAN_HARVEST = 4
