from udis import disasm, miniasm

from atrcopy import match_bit_mask, comment_bit_mask, data_bit_mask, selected_bit_mask, user_bit_mask


class BaseDisassembler(disasm.Disassembler):
    name = "generic disassembler"
    cpu = "undefined"
    allow_undocumented = False
    read_instructions = set()
    write_instructions = set()
    rw_modes = set()
    
    cached_miniassemblers = {}
    
    def __init__(self, asm_syntax, memory_map=None, hex_lower=True, mnemonic_lower=False):
        disasm.Disassembler.__init__(self, self.cpu, asm_syntax, memory_map, self.allow_undocumented, hex_lower, mnemonic_lower, self.read_instructions, self.write_instructions, self.rw_modes)
    
    def get_style(self):
        if self.pc >= self.origin + self.length:
            return 0, 0
        try:
            style = self.source.style[self.pc + self.pc_offset]
            if style & user_bit_mask:
                user_type = self.source.get_user_data(self.pc + self.pc_offset, 1)
            else:
                user_type = 0
            return style, user_type
        except AttributeError:
            # If there is no style parameter, assume it's all code!
            return 0, 0
    
    def is_data(self):
        return self.get_style()[0] & data_bit_mask
    
    def get_data_comment(self, style_tuple, bytes):
        style, user_type = style_tuple
        if (style & user_bit_mask) == 1:
            user_parser, user_disasm = user_disassemblers[user_type]
            return "; " + user_disasm(bytes, self.hex_lower)
        return disasm.Disassembler.get_data_comment(self, style, bytes)
    
    def is_same_data_style(self, style_tuple, first_style_tuple, bytes):
        style, user_type = style_tuple
        first_style, first_user_type = first_style_tuple
        if (style & first_style & user_bit_mask) == 1:
            if user_type == first_user_type:
                # display list! check to see if the byte is still part of the same
                # line in the display list disassembly
                user_parser, user_disasm = user_disassemblers[user_type]
                dl = user_parser(list(bytes))
                return len(dl) == 1
            return False
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


# Display list processing based on code from the atari800 project, monitor.c

def parse_antic_dl(bytes):
    groups = []
    last = []
    try:
        while len(bytes) > 0:
            byte = bytes.pop(0)
            if (byte & 0x0f == 1) or (byte & 0xf0 == 0x40):
                if last:
                    groups.append(last)
                    last = []
                # handle JVB, JMP, LMS
                last.append(byte)
                lo = bytes.pop(0)
                last.append(lo)
                hi = bytes.pop(0)
                last.append(hi)
                groups.append(last)
                last = []
            else:
                if last:
                    if last[-1] == byte:
                        last.append(byte)
                    else:
                        groups.append(last)
                        last = [byte]
                else:
                    last = [byte]
    except IndexError:
        pass
    if last:
        groups.append(last)
    return groups

def get_antic_dl(group, hex_lower=True):
    """Get the text version of the display list entry.
    
    If multiple entries are present in the group, they are assumed to be
    identical to the first entry -- i.e. they have been processed by a call to
    parse_antic_dl above.
    """
    if hex_lower:
        op_fmt = "%s %02x%02x"
    else:
        op_fmt = "%s %02X%02X"
    commands = []
    byte = group[0]
    count = len(group)
    if byte & 0xf == 1:
        if byte & 0x80:
            commands.append("DLI")
        if byte & 0x40:
            op = "JVB"
        elif byte & 0xf0 > 0:
            op = "<invalid %02x>" % byte
        else:
            op = "JMP"
        if count < 3:
            commands.append("%s <bad addr>" % op)
        else:
            commands.append(op_fmt % (op, group[2], group[1]))
    else:
        if byte & 0xf == 0:
            if byte & 0x80:
                commands.append("DLI")
            commands.append("%d BLANK" % (((byte >> 4) & 0x07) + 1))
        else:
            if byte & 0x80:
                commands.append("DLI")
            if byte & 0x40:
                if count < 3:
                    commands.append("LMS <bad addr>")
                else:
                    commands.append(op_fmt % ("LMS", group[2], group[1]))
                count = 1
            if byte & 0x20:
                commands.append("VSCROL")
            if byte & 0x10:
                commands.append("HSCROL")
            commands.append("MODE %X" % (byte & 0x0f))
        if count > 1:
            commands[0:0] = ["%dx" % count]
    return " ".join(commands)

jumpman_commands = {
    0xfc: (2, "type $ADDR"),
    0xfd: (3, "draw x=%s y=%s len=%s"),
    0xfe: (2, "spacing dx=%s dy=%s"),
    0xff: (0, "end"),
}

def parse_jumpman_level(bytes):
    groups = []
    count = 0
    data = []
    while len(bytes) > 0:
        byte = bytes.pop(0)
        if count == 0:
            if byte in jumpman_commands:
                count = jumpman_commands[byte][0]
                data = [byte]
            else:
                groups.append([byte])
                data = []
        else:
            data.append(byte)
            count -= 1

        if count == 0:
            groups.append(data)
            data = []
    if data:
        groups.append(data)
    return groups

def get_jumpman_level(group, hex_lower=True):
    """Get the text version of the display list entry.
    
    If multiple entries are present in the group, they are assumed to be
    identical to the first entry -- i.e. they have been processed by a call to
    parse_antic_dl above.
    """
    if hex_lower:
        op_fmt = "%02x"
        addr_fmt = "%04x"
    else:
        op_fmt = "%02X"
        addr_fmt = "%04X"
    commands = []
    byte = group[0]
    if byte in jumpman_commands:
        count, text = jumpman_commands[byte]
        if "ADDR" in text:
            if len(group[1:]) == 2:
                addr = addr_fmt % (group[1] + 256 * group[2])
            else:
                addr = "<bad addr>"
            text = text.replace("ADDR", addr)
        else:
            values = [op_fmt % g for g in group[1:]]
            if len(values) < count:
                values.extend(["<missing>" for i in range(count - len(values))])
            text = text % tuple(values)
    else:
        text = "<invalid command %s>" % (op_fmt % byte)
    return text

def parse_jumpman_harvest(bytes):
    groups = []
    count = 7
    data = []
    while len(bytes) > 0:
        byte = bytes.pop(0)
        if count == 7 and byte == 0xff:
            data = [byte]
            break
        data.append(byte)
        count -= 1

        if count == 0:
            groups.append(data)
            data = []
            count = 7
    if data:
        groups.append(data)
    return groups

def get_jumpman_harvest(group, hex_lower=True):
    """Get the text version of the display list entry.
    
    If multiple entries are present in the group, they are assumed to be
    identical to the first entry -- i.e. they have been processed by a call to
    parse_antic_dl above.
    """
    if hex_lower:
        op_fmt = "%02x"
        addr_fmt = "%04x"
    else:
        op_fmt = "%02X"
        addr_fmt = "%04X"
    commands = []
    byte = group[0]
    if byte == 0xff:
        text = "end"
    else:
        text = "enc=%s x=%s y=%s take=$%s paint=$%s"
        values = ["<missing>" for i in range(5)]
        if len(group) >= 1:
            values[0] = op_fmt % group[0]
        if len(group) >= 2:
            values[1] = op_fmt % group[1]
        if len(group) >= 3:
            values[2] = op_fmt % group[2]
        if len(group) >= 5:
            values[3] = addr_fmt % (group[3] + 256 * group[4])
        if len(group) >= 7:
            values[4] = addr_fmt % (group[5] + 256 * group[6])
        text = text % tuple(values)
    return text

ANTIC_DISASM = 0
JUMPMAN_LEVEL = 1
JUMPMAN_HARVEST = 2
user_disassemblers = {
    ANTIC_DISASM: (parse_antic_dl, get_antic_dl),
    JUMPMAN_LEVEL: (parse_jumpman_level, get_jumpman_level),
    JUMPMAN_HARVEST: (parse_jumpman_harvest, get_jumpman_harvest),
}
