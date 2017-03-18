import numpy as np
from profilehooks import profile

from udis import miniasm, cputables
import udis.udis_fast as udis_fast

from atrcopy import match_bit_mask, comment_bit_mask, selected_bit_mask, user_bit_mask, data_style

from memory_map import EmptyMemoryMap


def fast_get_entire_style_ranges(segment, split_comments=[data_style], **kwargs):
    style_copy = segment.get_comment_locations(**kwargs)
    print "FAST_GET_ENTIRE", style_copy
    last = -1
    for i in range(len(style_copy)):
        s = style_copy[i]
        if s & comment_bit_mask:
            if last == s:
                print "%04x" % i,
            else:
                print
                print "comment type: %02x" % s,
                last = s
    print
    num_bytes = len(style_copy)
    if num_bytes < 1:
        return []
    elif num_bytes == 1:
        return [(0,1)]
    first_index = 0
    first_style = style_copy[0]
    base_style = style_copy[0] & user_bit_mask
    ranges = []
    for i in range(1, num_bytes):
        s = style_copy[i]
        s2 = s & user_bit_mask
        print "%04x" % i, s, s2,
        if s & comment_bit_mask:
            if s2 == base_style and s2 not in split_comments:
                print "same w/skippable comment"
                continue
        elif s2 == base_style: # or s == first_style:
            print "same"
            continue
        ranges.append(((first_index, i), base_style))
        print "last\nbreak here -> %x:%x = %s" % ((ranges[-1][0][0], ranges[-1][0][1], ranges[-1][1]))
        first_index = i
        first_style = s
        base_style = s2
    ranges.append(((first_index, i+1), base_style))
    return ranges, style_copy




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
        'data byte prefix': '$',
        'data byte separator': ', ',
        'name': "MAC/65",
        }
    
    cached_miniassemblers = {}
    
    def __init__(self, asm_syntax=None, memory_map=None, hex_lower=True, mnemonic_lower=False, byte_mnemonic=".byte"):
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

    def add_chunk_processor(self, disassembler_name, style):
        self.fast.add_chunk_processor(disassembler_name, style)

    def print_r(self, r):
        print ", ".join("((%04x, %04x), %02x)" % (i[0][0], i[0][1], i[1]) for i in r)
        print

    @profile
    def disassemble_segment(self, segment):
        self.segment = segment
        self.start_addr = segment.start_addr
        self.end_addr = self.start_addr + len(segment)
        pc = self.start_addr
        rf, stylef = fast_get_entire_style_ranges(segment, user=user_bit_mask, split_comments=[data_style])
        print "FAST:", self.print_r(rf)
        r, style = segment.get_entire_style_ranges(user=user_bit_mask, split_comments=[data_style])
        print "SLOW:", self.print_r(r)
        print "FAST:", self.print_r(rf)
        assert np.all(style == stylef)
        assert id(style) != id(stylef)
        #assert rf == r
        self.info = self.fast.get_all(segment.rawdata.unindexed_view, pc, 0, rf)
        return self.info

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
            c = self.segment.get_comment(index + i)
            if c:
                comments.append(c)
        if comments:
            return " ".join(comments)
        return ""

    def get_prior_valid_opcode_start(self, target_pc):
        index = target_pc - self.start_addr
        row = self.info.index_to_row[index]
        while index > 0:
            row_above = self.info.index_to_row[index - 1]
            if row_above < row:
                break
            index -= 1
        return index + self.start_addr

    def get_operand_label(self, operand):
        """Find the label that the operand points to.
        """
        dollar = operand.find("$")
        if dollar >=0 and "#" not in operand:
            text_hex = operand[dollar+1:dollar+1+4]
            if len(text_hex) > 2 and text_hex[2] in "0123456789abcdefABCDEF":
                size = 4
            else:
                size = 2
            target_pc = int(text_hex[0:size], 16)

            # check for memory map label first, then branch label
            label = self.memory_map.get_name(target_pc)
            if not label and target_pc >= self.start_addr and target_pc <= self.end_addr:
                #print operand, dollar, text_hex, target_pc, operand_labels_start_pc, operand_labels_end_pc
                good_opcode_target_pc = self.get_prior_valid_opcode_start(target_pc)
                diff = target_pc - good_opcode_target_pc
                if diff > 0:
                    # if no existing label at the target, reference it using
                    # offset in bytes from the nearest previous label
                    label = "L%04X+%d" % (good_opcode_target_pc, diff)
                else:
                    label = "L%04X" % (target_pc)
            if label:
                operand = operand[0:dollar] + label + operand[dollar+1+size:]
            return operand, target_pc, label
        return operand, -1, ""

    def get_addr_dest(self, row):
        operand = self.info[row].instruction
        _, target_pc, _ = self.get_operand_label(operand)
        return target_pc

    def get_label_instruction(self, pc, line=None):
        if line is None:
            index = pc - self.start_addr
            row = self.info.index_to_row(index)
            line = self.info[row]
        if self.info.labels[pc]:
            label = "L" + (self.fmt_hex4 % pc)
        else:
            label = extra_labels.get(pc, "     ")
        if ";" in line.instruction:
            operand, _ = line.instruction.split(";", 1)
        else:
            operand = line.instruction.rstrip()
        if count > 1 and not line.flag & udis_fast.flag_data_bytes:
            if operand_labels_start_pc < 0:
                operand_labels_start_pc = self.start_addr
            if operand_labels_end_pc < 0:
                operand_labels_end_pc = self.end_addr
            operand, target_pc, label = self.get_operand_label(operand, operand_labels_start_pc, operand_labels_end_pc, offset_operand_labels)
        return label, operand

    def format_row_label(self, line):
        return self.fmt_hex4 % line.pc

    def format_data_list_bytes(self, index, num):
        return " ".join(self.fmt_hex2 % self.segment[index + i] for i in range(num))

    def format_data_directive_bytes(self, digits):
        """ Split string of hex digits into format used by chosen assembler

        """
        count = len(digits) / 2
        fmt = self.fmt_hex_digit_separator.join(self.fmt_hex_digits for i in range(count))
        return self.fmt_hex_directive + " " + fmt % tuple(digits[0:count*2])

    def format_label(self, line):
        pc = line.pc
        if self.info.labels[pc]:
            text = "L" + (self.fmt_hex4 % pc)
        else:
            text = self.memory_map.get_name(pc)
            if not text:
                text = "     "
        return text

    def get_operand_from_instruction(self, text):
        if ";" in text:
            operand, _ = text.split(";", 1)
        else:
            operand = text.rstrip()
        return operand

    def format_operand(self, line, operand):
        if line.flag & udis_fast.flag_data_bytes:
            operand = self.format_data_directive_bytes(operand)
        elif line.num_bytes > 1:
            operand, target_pc, label = self.get_operand_label(operand)
        return operand

    def format_instruction(self, index, line):
        label = self.format_label(line)
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
        if ";" in c:
            _, c = c.split(";", 1)
            comments.append(c)
        for i in range(line.num_bytes):
            c = self.segment.get_comment(index + i)
            if c:
                comments.append(c)
        if comments:
            return " ".join(comments)
        return ""

    def iter_row_text(self, start=0, end=-1, max_bytes_per_line=8):
        """iterates over the rows representing the disassembly
        
        Return information designed to be used by program list formatters.
        """
        if end < 0:
            end = len(self.info.index_to_row) - 1

        start_row = self.info.index_to_row[start]
        end_row = self.info.index_to_row[end - 1] # end is python style range, want actual last byte

        for row in range(start_row, end_row + 1):
            line = self.info[row]
            index = line.pc - self.start_addr
            label = self.format_label(line)
            comment = self.format_comment(index, line)
            operand = self.get_operand_from_instruction(line.instruction)
            if line.flag & udis_fast.flag_data_bytes and line.num_bytes > max_bytes_per_line:
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
        org = self.format_row_label(line)
        lines.append("        %s $%s" % (self.asm_origin, org))
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
        pc = self.segment.start_addr
        for line, hex_bytes, code, comment, num_bytes in self.iter_row_text():
            if comment:
                code = "%-30s; %s" % (code, comment)
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
            pc += num_bytes
        return lines


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
