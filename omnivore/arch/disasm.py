from udis import disasm, miniasm

from atrcopy import match_bit_mask, comment_bit_mask, data_bit_mask, selected_bit_mask


class BaseDisassembler(disasm.Disassembler):
    name = "generic disassembler"
    cpu = "undefined"
    allow_undocumented = False
    read_instructions = set()
    write_instructions = set()
    rw_modes = set()
    
    cached_miniassemblers = {}
    
    def __init__(self, memory_map=None, hex_lower=True, mnemonic_lower=False):
        disasm.Disassembler.__init__(self, self.cpu, memory_map, self.allow_undocumented, hex_lower, mnemonic_lower, self.read_instructions, self.write_instructions, self.rw_modes)
    
    def get_style(self):
        if self.pc >= self.origin + self.length:
            return 0
        try:
            return self.source.style[self.pc + self.pc_offset]
        except AttributeError:
            # If there is no style parameter, assume it's all code!
            return 0
    
    def is_data(self):
        return self.get_style() & data_bit_mask
    
    def is_same_data_style(self, bytes):
        style = self.get_style()
        return style & data_bit_mask and not style & comment_bit_mask
    
    @classmethod
    def get_miniassembler(cls, cpu):
        if not cpu in cls.cached_miniassemblers:
            asm = miniasm.MiniAssembler(cpu, allow_undocumented=cls.allow_undocumented)
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
    allow_undocumented = True


class Flagged6502Disassembler(Undocumented6502Disassembler):
    name = "6502 (highlighted undocumented opcodes)"
    
    def get_flag(self, flag):
        return flag & disasm.und


class Basic65C02Disassembler(BaseDisassembler):
    name = "65c02"
    cpu = "65c02"


class Basic65816Disassembler(BaseDisassembler):
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
