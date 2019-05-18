import numpy as np

from .. import disassembler as udis_fast

from atrip import style_bits

from .memory_map import EmptyMemoryMap

import logging
log = logging.getLogger(__name__)


# Style numbers for other disassemblers
ANTIC_DISASM = 2
JUMPMAN_LEVEL = 3
JUMPMAN_HARVEST = 4
UNINITIALIZED_DATA = 5

style_names = {
    0: "code",
    1: "data",
    ANTIC_DISASM: "antic_dl",
    JUMPMAN_LEVEL: "jumpman_level",
    JUMPMAN_HARVEST: "jumpman_harvest",
    UNINITIALIZED_DATA: "uninitialized data",
}

def get_style_name(segment, index):
    if segment.is_valid_index(index):
        s = segment.style[index] & style_bits.user_bit_mask
        msg = style_names.get(s, "")
    else:
        msg = ""
    return msg

def iter_disasm_styles():
    for i, name in style_names.items():
        if i == 0:
            continue
        yield i, name


class BaseDisassembler(object):
    name = "generic disassembler"
    cpu = "undefined"
    read_instructions = set()
    write_instructions = set()
    rw_modes = set()
    highlight_flags = 0
    default_assembler = {
        'comment char': ';',
        'origin': '*=',
        'data byte': '.byte',
        'data byte prefix': '$',
        'data byte separator': ', ',
        'name': "MAC/65",
        }

    cached_miniassemblers = {}
    label_format = "L%04X"  # Labels always upper case to match udis

    def __init__(self, asm_syntax=None, memory_map=None, hex_lower=True, mnemonic_lower=False):
        if asm_syntax is None:
            asm_syntax = self.default_assembler
        self.hex_lower = hex_lower
        self.mnemonic_lower = mnemonic_lower
        if self.hex_lower:
            self.fmt_hex2 = "%02x"
            self.fmt_hex4 = "%04x"
        else:
            self.fmt_hex2 = "%02X"
            self.fmt_hex4 = "%04X"
        if mnemonic_lower:
            case_func = lambda a:a.lower()
        else:
            case_func = lambda a:a.upper()
        self.fmt_hex_directive = asm_syntax['data byte']
        self.fmt_hex_digits = asm_syntax['data byte prefix'] + "%c%c"
        self.fmt_hex_digit_separator = asm_syntax['data byte separator']
        self.asm_origin = case_func(asm_syntax['origin'])
        self.comment_char = case_func(asm_syntax['comment char'])
        self.fast = udis_fast.DisassemblerWrapper(self.cpu, fast=True, mnemonic_lower=mnemonic_lower, hex_lower=hex_lower)
        self.memory_map = memory_map if memory_map is not None else EmptyMemoryMap()
        self.segment = None
        self.info = None
        self._pc_label_cache = None
        self._dest_pc_label_cache = None
        self._computed_directive_cache = None

    @classmethod
    def get_nop(cls):
        cpu = cputables.processors[cls.cpu]
        return cpu['nop']

    @classmethod
    def get_miniassembler(cls, cpu):
        if not cpu in cls.cached_miniassemblers:
            asm = udis_fast.MiniAssembler(cpu)
            cls.cached_miniassemblers[cpu] = asm

        return cls.cached_miniassemblers[cpu]

    @property
    def label_dict(self):
        d = {}
        if self.info:
            all_pcs = np.where(self.info.labels > 0)[0]
            inside = np.where((self.origin <= all_pcs) & (all_pcs < self.end_addr))[0]
            pcs = all_pcs[inside]
            fmt = self.label_format
            d = {pc:fmt % pc for pc in pcs}
        return d

    def assemble_text(self, pc, cmd):
        miniasm = self.get_miniassembler(self.cpu)
        byte_values = miniasm.asm(pc, cmd)
        if not byte_values:
            raise RuntimeError("Unknown addressing mode")
        return byte_values

    def add_chunk_processor(self, disassembler_name, style):
        self.fast.add_chunk_processor(disassembler_name, style)

    def disassemble_segment(self, segment):
        self.invalidate_caches()
        self.segment = segment
        self.origin = segment.origin
        self.end_addr = self.origin + len(segment)
        self.info = udis_fast.fast_disassemble_segment(self.fast, segment)
        self.use_labels = self.origin > 0
        return self.info

    def is_current(self, segment):
        return self.segment == segment and self.origin == segment.origin

    @property
    def pc_label_cache(self):
        if self._pc_label_cache is None:
            self.create_label_caches()
        return self._pc_label_cache

    @property
    def dest_pc_label_cache(self):
        if self._dest_pc_label_cache is None:
            self.create_label_caches()
        return self._dest_pc_label_cache

    @property
    def computed_directive_cache(self):
        if self._computed_directive_cache is None:
            self.create_computed_directive_cache()
        return self._computed_directive_cache

    def invalidate_caches(self):
        log.debug("Invalidating label caches")
        self._pc_label_cache = None
        self._dest_pc_label_cache = None
        self._computed_directive_cache = None

    def create_label_caches(self):
        pc_labels = {}
        dest_pc_labels = {}
        for line in self.info:
            text = self.get_pc_label(line.pc)
            if text:
                pc_labels[line.pc] = text
            if line.flag & udis_fast.flags.flag_label:
                text = self.get_dest_pc_label(line.dest_pc)
                if text:
                    dest_pc_labels[line.pc] = text
        self._pc_label_cache = pc_labels
        self._dest_pc_label_cache = dest_pc_labels
        log.debug("Created label caches: %d in pc, %d in dest_pc" % (len(pc_labels), len(dest_pc_labels)))

    def create_computed_directive_cache(self):
        pc_to_directive = {}
        for line in self.info:
            if line.flag & udis_fast.flags.flag_data_bytes:
                operand = self.get_operand_from_instruction(line.instruction)
                text = self.format_data_directive_bytes(operand)
                pc_to_directive[line.pc] = text
        self._computed_directive_cache = pc_to_directive
        log.debug("Created directive cache, %d lines" % (len(pc_to_directive)))

    def get_origin(self, pc):
        return "%s $%s" % (self.asm_origin, self.fmt_hex4 % pc)

    def get_next_instruction_pc(self, pc):
        info = self.info
        index = pc - self.origin
        row = info.index_to_row[index]
        line = info[row + 1]  # next line!
        return line.pc

    def get_comments(self, index, line=None):
        info = self.info
        if line is None:
            row = info.index_to_row[index]
            line = info[row]
        comments = []
        c = line.instruction
        if ";" in c:
            _, c = c.split(";", 1)
            comments.append(c)
        for i in range(line.num_bytes):
            c = self.segment.get_comment_at(index + i)
            if c:
                comments.append(c)
        if comments:
            return " ".join(comments)
        return ""

    def get_pc_label(self, pc):
        """Get the label for a program counter address

        """
        text = self.memory_map.get_name(pc)
        if not text and self.info.labels[pc]:
            text = self.label_format % pc
        return text

    def get_dest_pc_label(self, target_pc):
        """Get the label for a target address

        This differs from get_pc_label in that if a label doesn't exist at the
        target_pc but there is one at some small offset before, use that label
        plus the offset difference.
        """
        label = self.memory_map.get_name(target_pc)
        if not label and target_pc >= self.origin and target_pc < self.end_addr:
            #print operand, dollar, text_hex, target_pc, operand_labels_start_pc, operand_labels_end_pc
            good_opcode_target_pc = self.info.get_instruction_start_pc(target_pc)
            diff = target_pc - good_opcode_target_pc
            if diff > 0:
                # if no existing label at the target, reference it using
                # offset in bytes from the nearest previous label
                nearest_label = self.memory_map.get_name(good_opcode_target_pc)
                if not nearest_label:
                    nearest_label = self.label_format % good_opcode_target_pc
                label = "%s+%d" % (nearest_label, diff)
            else:
                label = self.label_format % target_pc
        return label

    def get_operand_label(self, line, operand):
        """Find the label that the operand points to.
        """
        target_pc = line.dest_pc

        label = self.get_dest_pc_label(target_pc)
        if label:
            # find the place to replace hex digits with the text label
            dollar = operand.find("$")
            if dollar >=0 and "#" not in operand:
                text_hex = operand[dollar+1:dollar+1+4]
                if len(text_hex) > 2 and text_hex[2] in "0123456789abcdefABCDEF":
                    size = 4
                else:
                    size = 2
                operand = operand[0:dollar] + label + operand[dollar+1+size:]
        return operand

    def get_addr_dest(self, row):
        line = self.info[row]
        return line.dest_pc if line.flag & udis_fast.flags.flag_label else -1

    def format_row_label(self, line):
        return self.fmt_hex4 % line.pc

    def format_data_list_bytes(self, index, num):
        return " ".join(self.fmt_hex2 % self.segment[index + i] for i in range(num))

    def format_data_directive_bytes(self, digits):
        """ Split string of hex digits into format used by chosen assembler

        """
        count = len(digits) // 2
        fmt = self.fmt_hex_digit_separator.join(self.fmt_hex_digits for i in range(count))
        return self.fmt_hex_directive + " " + fmt % tuple(digits[0:count*2])

    def format_label(self, line):
        if not self.use_labels:
            return "     "
        text = self.get_pc_label(line.pc)
        return "     " if not text else text

    def get_operand_from_instruction(self, text):
        if b";" in text:
            operand, _ = text.split(b";", 1)
        else:
            operand = text.rstrip()
        return operand.decode("latin-1")

    def format_operand(self, line, operand):
        if line.flag == udis_fast.flags.flag_origin:
            operand = self.get_origin(line.dest_pc)
        elif line.flag & udis_fast.flags.flag_data_bytes:
            operand = self.format_data_directive_bytes(operand)
        elif self.use_labels and line.flag & udis_fast.flags.flag_label:
            operand = self.get_operand_label(line, operand)
        return operand

    def format_instruction(self, index, line):
        label = self.format_label(line)

        # py3 notes: line.instruction is ascii byte_values, but operand will be
        # unicode after this.
        operand = self.get_operand_from_instruction(line.instruction)

        operand = self.format_operand(line, operand)
        return label + " " + operand

    def format_comment(self, index, line=None):
        info = self.info
        if line is None:
            row = info.index_to_row[index]
            line = info[row]
        comments = []
        c = line.instruction
        if b";" in c:
            _, c = c.split(b";", 1)
            comments.append(c.decode('utf-8'))
        for i in range(line.num_bytes):
            c = self.segment.get_comment_at(index + i)
            if c:
                comments.append(c)
        if comments:
            text = " ".join(comments)
            return text.replace("\r", "").replace("\n", "")
        return ""

    def iter_row_text(self, start=0, end=-1, max_bytes_per_line=8):
        """iterates over the rows representing the disassembly

        Return information designed to be used by program list formatters.
        """
        if end < 0:
            end = len(self.info.index_to_row)

        start_row = self.info.index_to_row[start]
        end_row = self.info.index_to_row[end - 1] # end is python style range, want actual last byte

        for row in range(start_row, end_row + 1):
            line = self.info[row]
            index = line.pc - self.origin
            label = self.format_label(line)
            comment = self.format_comment(index, line)
            operand = self.get_operand_from_instruction(line.instruction)
            if line.flag & udis_fast.flags.flag_data_bytes and line.num_bytes > max_bytes_per_line:
                first = True
                for i in range(0, line.num_bytes, max_bytes_per_line):
                    count = min(line.num_bytes, i + max_bytes_per_line) - i
                    hex_bytes = self.format_data_list_bytes(index + i, count)
                    subset = operand[i*2:(i+count)*2]
                    code = self.format_data_directive_bytes(subset)
                    yield line, hex_bytes, label + "   " + code, comment, count
                    if first:
                        label = "     "
                        comment = ""
                        first = False
            else:
                if line.flag == udis_fast.flags.flag_origin:
                    hex_bytes = ""
                else:
                    hex_bytes = self.format_data_list_bytes(index, line.num_bytes)
                code = self.format_operand(line, operand)
                # expand to 8 spaces
                code = label + "   " + code
                yield line, hex_bytes, code, comment, line.num_bytes

    def get_disassembled_text(self, start=0, end=-1):
        """Returns list of lines representing the disassembly

        Raises IndexError if the disassembly hasn't reached the index yet
        """
        lines = []
        start_row = self.info.index_to_row[start]
        line = self.info[start_row]
        lines.append("        " + self.get_origin(line.pc))
        for line, hex_bytes, code, comment, num_bytes in self.iter_row_text(start, end):
            if comment:
                text = "%-30s; %s" % (code, comment)
            else:
                text = code
            lines.append(text)
        return lines

    def get_atasm_lst_text(self):
        """Returns list of lines representing the disassembly

        Raises IndexError if the disassembly hasn't reached the index yet
        """
        lines = [""]
        lines.append("Source: %s.s" % (self.segment.name))
        line_num = 2
        pc = self.segment.origin
        for line, hex_bytes, code, comment, num_bytes in self.iter_row_text():
            if line.flag == udis_fast.flags.flag_origin:
                line_num += 1
                continue
            pc = line.pc
            if comment:
                code = "%-30s; %s" % (code, comment.rstrip())
            if ".byte" in code:
                count = 0
                hex_bytes = hex_bytes.upper()
                text = ""
                while count < num_bytes:
                    sub_bytes = hex_bytes[count * 3:count * 3 + 6].rstrip()
                    if count == 0:
                        text = "%05d %04X  %-17s %s" % (line_num, pc, sub_bytes, code)
                    else:
                        text += "\n%05d %04X  %s " % (line_num, pc + count, sub_bytes)
                    count += 2
            else:
                text = "%05d %04X  %-17s %s" % (line_num, line.pc, hex_bytes.upper(), code)
            lines.append(text)
            line_num += 1
        return lines

    def search_labels(self, labels, search_text, match_case=False):
        s = self.origin
        matches = []
        if not match_case:
            for pc, label in labels.items():
                if search_text in label.lower():
                    matches.append((pc - s, pc - s + 1))
        else:
            for pc, label in labels.items():
                if search_text in label:
                    matches.append((pc - s, pc - s + 1))
        return matches

    def search(self, search_text, match_case=False):
        s = self.origin
        if not match_case:
            search_text = search_text.lower()
            matches = [(t.pc - s, t.pc - s + t.num_bytes) for t in self.info if search_text in t.instruction.lower()]
        else:
            matches = [(t.pc - s, t.pc - s + t.num_bytes) for t in self.info if search_text in t.instruction]
        log.debug("instruction matches: %s" % str(matches))

        label_matches = self.search_labels(self.pc_label_cache, search_text, match_case)
        matches.extend(label_matches)
        log.debug("pc label matches: %s" % str(label_matches))

        label_matches = self.search_labels(self.dest_pc_label_cache, search_text, match_case)
        matches.extend(label_matches)
        log.debug("dest pc label matches: %s" % str(label_matches))

        label_matches = self.search_labels(self.computed_directive_cache, search_text, match_case)
        matches.extend(label_matches)
        log.debug("computed directives match: %s" % str(label_matches))

        return matches


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
    # highlight_flags = udis_fast.flags.FLAG_UNDOC


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
