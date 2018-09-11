import logging
log = logging.getLogger(__name__)

# mnemonic flags
from omni8bit.udis_fast.flags import *

# output flags
c_define_flags = ""
# for flag_name, flag_val in list(locals().items()):
#     if flag_name.startswith("flag_"):
#         c_define_flags += "#define %s %s\n" % (flag_name.upper(), flag_val)


def convert_fmt(fmt, mnemonic_lower = True, hex_lower=True, escape_strings=True):
    fmt = fmt.lower()
    if "{0:02x}" in fmt and "{1:02x}" and "{2:02x}" in fmt:
        # determine order of args by which comes first in the format string
        indexes = [
            (fmt.index("{0:02x}"), "op1"),
            (fmt.index("{1:02x}"), "op2"),
            (fmt.index("{2:02x}"), "op3"),
            ]
        indexes.sort()
        argorder = [i[1] for i in indexes]
        fmt = fmt.replace("{0:02x}", "%02x").replace("{1:02x}", "%02x").replace("{2:02x}", "%02x")
    elif "{0:02x}" in fmt and "{1:02x}" in fmt:
        # determine order of args by which comes first in the format string
        i0 = fmt.index("{0:02x}")
        i1 = fmt.index("{1:02x}")
        if i0 < i1:
            argorder = ["op1", "op2"]
        else:
            argorder = ["op2", "op1"]
        fmt = fmt.replace("{0:02x}", "%02x").replace("{1:02x}", "%02x")
    elif "{0:02x}" in fmt:
        fmt = fmt.replace("{0:02x}", "%02x")
        argorder = ["op1"]
    elif "{0:04x}" in fmt:
        fmt = fmt.replace("{0:04x}", "%04x")
        argorder = ["rel"]
    else:
        argorder = []

    if escape_strings and "'" in fmt:
        fmt = fmt.replace("'", "\\'")
    if mnemonic_lower:
        if not hex_lower:
            fmt = fmt.replace("%02x", "%02X").replace("%04x", "%04X")
    else:
        fmt = fmt.upper()
        if hex_lower:
            fmt = fmt.replace("%02X", "%02x").replace("%04X", "%04x")
    return fmt, argorder

byte_loc = 5
label_loc = 17
op_loc = 23

class PrintBase(object):
    escape_strings = True

    def __init__(self, generator, lines, indent="    ", leadin=0, leadin_offset=0):
        self.lines = lines
        self.indent = indent
        self.leadin = leadin
        self.leadin_offset = leadin_offset
        self.first = True
        self.generator = generator

    def set_case(self, mnemonic_lower, hex_lower):
        pass

    def set_current(self, optable):
        self.length, self.mnemonic, self.mode, self.flag = optable
        # only low 8 bits of flags is saved in output, so convert any that are
        # needed
        if self.flag & comment:
            self.flag |= flag_data_bytes
        gen = self.generator
        fmt = gen.address_modes[self.mode]
        self.fmt, self.argorder = convert_fmt(fmt, gen.mnemonic_lower, gen.hex_lower, self.escape_strings)
        if self.mode in gen.rw_modes:
            if self.mnemonic in gen.r_mnemonics:
                self.flag |= r
            if self.mnemonic in gen.w_mnemonics:
                self.flag |= w
        if gen.mnemonic_lower:
            self.mnemonic = self.mnemonic.lower()
        else:
            self.mnemonic = self.mnemonic.upper()

    @property
    def undocumented(self):
        return self.flag & und

    def process(self, opcode):
        self.start_if_clause(opcode)
        if self.length - self.leadin_offset == 1:
            self.check_pc()
            self.opcode1(opcode)
        elif self.length - self.leadin_offset == 2:
            self.check_pc()
            self.opcode2(opcode)
        elif self.length - self.leadin_offset == 3:
            self.check_pc()
            self.opcode3(opcode)
        elif self.length == 4:
            self.check_pc()
            self.opcode4(opcode)
        self.end_if_clause()
        self.first = False


c_preamble_header = """#include <stdio.h>
#include <string.h>

%s

#include "libudis.h"
""" % c_define_flags


class RawC(PrintBase):
    preamble_header = c_preamble_header

    preamble = """
int %s(history_entry_t *entry, char *txt) {
    int dist;
    unsigned int rel;
    unsigned short addr;
    unsigned char opcode, leadin, op1, op2, op3;
    unsigned int num_printed = 0;

    opcode = entry->instruction[0];
"""

    def out(self, s):
        if not s.endswith(":") and not s.endswith("{") and not s.endswith("}"):
            s += ";"
        self.lines.append(self.indent + s)

    def z80_4byte_intro(self, opcode):
        self.out("case 0x%x:" % (opcode))
        self.out("    op1 = entry->instruction[1]")
        self.out("    op2 = entry->instruction[2]")
        self.out("    rel = entry->target_addr")
        self.out("    switch(op2) {")

    def z80_4byte(self, z80_2nd_byte, opcode):
        self.out("case 0x%x:" % (opcode))
        self.argorder = ["rel"]
        self.opcode1(opcode)
        self.first = False

    def z80_4byte_outro(self):
        pass

    def op1(self):
        self.out("    op1 = entry->instruction[1]")

    def op2(self):
        self.out("    op2 = entry->instruction[2]")

    def op3(self):
        self.out("    op3 = entry->instruction[3]")

    def start_if_clause(self, opcode):
        # if self.first:
        #     self.out("switch(opcode) {")
        #     self.first = False
        self.out("case 0x%x: /* %s %s */" % (opcode, self.mnemonic, self.fmt))

    def end_if_clause(self):
        self.out("    break")

    def check_pc(self):
        pass

    comment_argorder = ["opcode", "op1", "op2", "op3"]

    def get_comment(self, count, argorder):
        newargs = []
        prefix = ""
        if self.flag & comment:
            for i in range(4):
                if count > i:
                    prefix += self.generator.data_op
                    newargs.append(self.comment_argorder[i])
            prefix += "; "
            argorder[0:0] = newargs
        return prefix

    def opcode_line_out(self, outstr, argorder):
        if argorder:
            outstr += ", %s" % (", ".join(argorder))
        self.out("    num_printed = sprintf(txt, %s)" % outstr)

    def wrap_quotes(self, outstr):
        return "\"%s\"" % outstr

    def opcode1(self, opcode):
        prefix = self.get_comment(self.length, self.argorder)
        outstr = "%s%s %s" % (prefix, self.mnemonic, self.fmt)
        outstr = self.wrap_quotes(outstr.lstrip())
        self.opcode_line_out(outstr.rstrip(), self.argorder)

    def opcode2(self, opcode):
        self.op1()
        if self.fmt:
            if self.flag & pcr:
                self.out("    if (op1 > 127) dist = op1 - 256; else dist = op1")
                self.out("    rel = (pc + 2 + dist) & 0xffff")
        self.opcode1(opcode)

    def opcode3(self, opcode):
        self.op1()
        self.op2()
        if self.fmt:
            if self.flag & pcr:
                self.out("    addr = op1 + 256 * op2")
                self.out("    if (addr > 32768) addr -= 0x10000")
                # limit relative address to 64k address space
                self.out("    rel = (pc + 2 + addr) & 0xffff")
        self.opcode1(opcode)

    def opcode4(self, opcode):
        self.op1()
        self.op2()
        self.op3()
        self.opcode1(opcode)

    def unknown_opcode(self):
        self.out("default:")
        if self.leadin_offset == 0:
            self.mnemonic = ""
            self.fmt = self.generator.data_op
            self.argorder = ["opcode"]
        elif self.leadin_offset == 1:
            self.mnemonic = ""
            self.fmt = self.generator.data_op * 2
            self.argorder = ["leadin", "opcode"]
        self.opcode1(0)
        self.out("    break")

    def start_multibyte_leadin(self, leadin):
        self.out("case 0x%x:" % (leadin))
        self.out("    leadin = opcode")
        self.out("    opcode = entry->instruction[1]")
        log.debug("starting multibyte with leadin %x" % leadin)

    def start_subroutine(self):
        self.out("switch(opcode) {")

    def end_subroutine(self):
        self.out("}")
        if self.leadin_offset == 0:
            self.out("return num_printed")
            self.lines.append("}") # no indent for closing brace
        else:
            self.out("break")


class UnrolledC(RawC):
    escape_strings = False

    preamble_header = c_preamble_header

   

    preamble = """
int %s(history_entry_t *entry, char *txt, char *hexdigits, int lc) {
    int dist;
    unsigned char opcode, leadin, op1, op2, op3;
    char *first_txt, *h;
    unsigned int rel;

    first_txt = txt;
    opcode = entry->instruction[0];
"""

    def wrap_quotes(self, outstr):
        # doesn't need quotes
        return outstr

    def opcode2(self, opcode):
        op1_needed = True
        if self.fmt:
            if self.flag & pcr:
                self.out("    rel = entry->target_addr")
                op1_needed = False
        if op1_needed:
            self.op1()
        self.opcode1(opcode)

    def opcode3(self, opcode):
        op1_and_2_needed = True
        if self.fmt:
            if self.flag & pcr:
                self.out("    rel = entry->target_addr")
                op1_and_2_needed = False
        if op1_and_2_needed:
            self.op1()
            self.op2()
        self.opcode1(opcode)

    def opcode_line_out(self, outstr, argorder=[], force_case=False):
        log.debug("opcode_line_out: %s %s" % (outstr, argorder))

        def flush_mixed(diffs):
            if force_case:
                for c in diffs:
                    self.out("        *txt++ = '%s'" % c)
            else:
                # self.out("    if (lc) {")
                # for c in diffs:
                #     self.out("        *txt++ = '%s'" % c.lower())
                # self.out("    }")
                # self.out("    else {")
                # for c in diffs:
                #     self.out("        *txt++ = '%s'" % c.upper())
                # self.out("    }")
                line = "if (lc) "
                ops = ["*txt++ = '%s'" % c.lower() for c in diffs]
                line += ",".join(ops)
                # for c in diffs:
                #     self.out("        *txt++ = '%s'" % c.lower())
                self.out("    %s" % line)
                line = "else "
                ops = ["*txt++ = '%s'" % c.upper() for c in diffs]
                line += ",".join(ops)
                # for c in diffs:
                #     self.out("        *txt++ = '%s'" % c.lower())
                self.out("    %s" % line)
            return []

        def flush_text(text):
            same = []
            diffs = []
            for l, u in zip(text.lower(), text.upper()):
                if l == u:
                    #print "l==u: -->%s<-- -->%s<--: diffs=%s" % (l, u, diffs)
                    if len(diffs) > 0:
                        diffs = flush_mixed(diffs)
                    if u == "'" or u == "\\":
                        same.append("\\%s" %  u)
                    else:
                        same.append(u)
                else:
                    if len(same) > 0:
                        self.out("    " + ",".join(["*txt++ = '%s'" % s for s in same]))
                        same = []
                    diffs.append(u)
                    #print "l!=u: -->%s<-- -->%s<--: diffs=%s" % (l, u, diffs)
            if len(same) > 0:
                self.out("    " + ",".join(["*txt++ = '%s'" % s for s in same]))
            if len(diffs) > 0:
                flush_mixed(diffs)
            return ""

        def flush_nibble(operand):
            self.out("    h = &hexdigits[(%s & 0xff)*2] + 1" % operand)
            self.out("    *txt++ = *h++")

        def flush_hex(operand):
            self.out("    h = &hexdigits[(%s & 0xff)*2]" % operand)
            self.out("    *txt++ = *h++")
            self.out("    *txt++ = *h++")

        def flush_hex16(operand):
            flush_hex("(%s>>8)" % operand)
            flush_hex("%s" % operand)
            # self.out("    h = &hexdigits[((%s>>8)&0xff)*2]" % operand)
            # self.out("    *txt++ = *h++")
            # self.out("    *txt++ = *h++")
            # self.out("    h = &hexdigits[(%s&0xff)*2]" % operand)
            # self.out("    *txt++ = *h++")
            # self.out("    *txt++ = *h++")

        def flush_dec(operand):
            self.out("    txt += sprintf(txt, \"%%d\", %s)" % operand)

        def flush_raw(operand):
            self.out("    *txt++ = %s" % operand)

        i = 0
        text = ""
        fmt = ""
        while i < len(outstr):
            tail = outstr[i:].lower()
            if tail.startswith("#$%02x%02x"):
                text = text + "#$"
                text = flush_text(text)
                flush_hex(argorder.pop(0))
                flush_hex(argorder.pop(0))
                i += 10
            elif tail.startswith("#$%02x"):
                text = text + "#$"
                text = flush_text(text)
                flush_hex(argorder.pop(0))
                i += 6
            elif tail.startswith("$%02x%02x"):
                text = text + "$"
                text = flush_text(text)
                flush_hex(argorder.pop(0))
                flush_hex(argorder.pop(0))
                i += 9
            elif tail.startswith("$%02x"):
                text = text + "$"
                text = flush_text(text)
                flush_hex(argorder.pop(0))
                i += 5
            elif tail.startswith("$%04x"):
                text = text + "$"
                text = flush_text(text)
                flush_hex16(argorder.pop(0))
                i += 5
            elif tail.startswith("%02x"):
                text = flush_text(text)
                flush_hex(argorder.pop(0))
                i += 4
            elif tail.startswith("%1x"):
                text = flush_text(text)
                flush_nibble(argorder.pop(0))
                i += 3
            elif tail.startswith("%d"):
                text = flush_text(text)
                flush_dec(argorder.pop(0))
                i += 2
            elif tail.startswith("\\"):
                text = flush_text(text)
                i += 1
                flush_raw(ord(outstr[i]))
                i += 1
            elif tail.startswith("$%"):
                raise RuntimeError("Unsupported operand format: %s" % tail)
            else:
                text += outstr[i]
                i += 1
        flush_text(text)

    def end_subroutine(self):
        self.out("}")
        if self.leadin_offset == 0:
            self.out("return (int)(txt - first_txt)")
            self.lines.append("}") # no indent for closing brace
        else:
            self.out("break")


class DataC(UnrolledC):
    preamble_header = c_preamble_header

    preamble = """
int %s(history_entry_t *entry, char *txt, char *hexdigits, int lc) {
    char *first_txt, *h;
    unsigned char *data;

    first_txt = txt;
    data = entry->instruction;
    switch(entry->num_bytes) {
"""
    def print_bytes(self, count, data_op):
        outstr = data_op * count
        argorder = ["src[%d]" % i for i in range(count)]
        self.opcode_line_out(outstr, argorder)

    def process(self, count):
        if count > 1:
            self.out("case %d:" % count)
        else:
            self.out("default:")
        # self.print_bytes(count, self.generator.data_op)
        self.opcode_line_out(self.generator.data_op, ["*data++"])

    def gen_cases(self):
        for count in range(self.generator.bytes_per_line, 0, -1): # down to 1
            self.process(count)
        self.out("    break")

    def end_subroutine(self):
        self.out("}")
        self.out("return (int)(txt - first_txt)")
        self.lines.append("}") # no indent for closing brace

class AnticC(DataC):
    preamble = """
int %s(history_entry_t *entry, char *txt, char *hexdigits, int lc) {
    unsigned char opcode;
    int i;
    char *first_txt, *h;

    first_txt = txt;
    opcode = entry->instruction[0];

    for (i=0; i<entry->num_bytes; i++) {
        h = &hexdigits[(entry->instruction[i] & 0xff)*2];
        *txt++ = *h++;
        *txt++ = *h++;
    }
"""
    def process(self, count):
        self.opcode_line_out("; ");
        self.out("    if ((opcode & 0xf) == 1) {")
        self.out("        if (opcode & 0x80) {")
        self.opcode_line_out("DLI ", force_case=True);
        self.out("        }")
        self.out("        if (opcode & 0x40) {")
        self.opcode_line_out("JVB ", force_case=True)
        self.out("        }")
        self.out("        else if ((opcode & 0xf0) > 0) {")
        self.opcode_line_out("<invalid>", force_case=True)
        self.out("        }")
        self.out("        else {")
        self.opcode_line_out("JMP ", force_case=True)
        self.out("        }")
        self.out("        if (entry->num_bytes < 3) {")
        self.opcode_line_out("<bad addr>", force_case=True)
        self.out("        }")
        self.out("        else {")
        self.opcode_line_out("$%02x%02x", ["entry->instruction[2]", "entry->instruction[1]"])
        self.out("        }")

        self.out("    }")
        self.out("    else {")
        self.out("        if ((opcode & 0xf) == 0) {")
        self.out("            if (entry->num_bytes > 1) {")
        self.opcode_line_out("%d\\x", ["entry->num_bytes"])
        self.out("            }")
        self.out("            if (opcode & 0x80) {")
        self.opcode_line_out("DLI ", force_case=True)
        self.out("            }")
        self.opcode_line_out("%d BLANK", ["(((opcode >> 4) & 0x07) + 1)"], force_case=True)
        self.out("        }")
        self.out("        else {")
        self.out("            if ((opcode & 0xf0) == 0x40) {")
        self.out("                if (entry->num_bytes < 3) {")
        self.opcode_line_out("LMS <bad addr> ", force_case=True)
        self.out("                }")
        self.out("                else {")
        self.opcode_line_out("LMS $%02x%02x ", ["entry->instruction[2]", "entry->instruction[1]"], force_case=True)
        self.out("                }")
        self.out("            }")
        self.out("            else if (entry->num_bytes > 1) {")
        self.opcode_line_out("%d\\x", ["entry->num_bytes"])
        self.out("            }")
        self.out("            if (opcode & 0x80) {")
        self.opcode_line_out("DLI ", force_case=True)
        self.out("            }")
        self.out("            if (opcode & 0x20) {")
        self.opcode_line_out("VSCROLL ", force_case=True)
        self.out("            }")
        self.out("            if (opcode & 0x10) {")
        self.opcode_line_out("HSCROLL ", force_case=True)
        self.out("            }")
        self.opcode_line_out("MODE %1x", ["(opcode & 0x0f)"], force_case=True)
        self.out("        }")
        self.out("    }")

        self.out("    return (int)(txt - first_txt)")
        self.out("}")

    def gen_cases(self):
        self.process(0)

    def end_subroutine(self):
        pass

class JumpmanHarvestC(UnrolledC):
    preamble = """
int %s(history_entry_t *entry, char *txt, char *hexdigits, int lc) {
    unsigned char opcode;
    char *first_txt, *h;

    first_txt = txt;
    opcode = entry->instruction[0];
"""

    footer = """
    }
    return (int)(txt - first_txt);
}
"""

    def process(self, count):
        sections = [("""
    if (opcode == 0xff) {
        """, "%02x ; end", ["opcode"]),
    ("""
    }
    else if (entry->num_bytes == 7) {
        """, "%02x"*7 + " ; enc=$%02x x=$%02x y=$%02x take=$%02x%02x paint=$%02x%02x", ["opcode", "entry->instruction[1]", "entry->instruction[2]", "entry->instruction[3]", "entry->instruction[4]", "entry->instruction[5]", "entry->instruction[6]", "opcode", "entry->instruction[1]", "entry->instruction[2]", "entry->instruction[4]", "entry->instruction[3]", "entry->instruction[6]", "entry->instruction[5]"]),
    ("""
    }
    else {
        """, "%02x ; [incomplete]", ["opcode"]),
    ]
        for code, outstr, argorder in sections:
            self.lines.extend(code.splitlines())
            self.opcode_line_out(outstr, argorder)
        self.lines.extend(self.footer.splitlines())

    def gen_cases(self):
        self.process(0)

    def end_subroutine(self):
        pass


class HistoryEntryC(RawC):
    preamble_header = c_preamble_header

    preamble = """
int %s(history_entry_t *entry, unsigned char *src, unsigned int pc, unsigned int last_pc, unsigned short *labels) {
    int dist;
    unsigned int rel;
    unsigned short addr;
    unsigned char opcode, leadin, op1, op2, op3;

    opcode = *src++;
    entry->instruction[0] = opcode;
    entry->pc = (unsigned short)pc;
    entry->target_addr = 0;
"""

    def out(self, s):
        if not s.endswith(":") and not s.endswith("{") and not s.endswith("}") and not s.endswith("*/"):
            s += ";"
        self.lines.append(self.indent + s)

    def z80_4byte_intro(self, opcode):
        self.out("case 0x%x:" % (opcode))
        self.out("    op1 = *src++")
        self.out("    op2 = *src++")
        self.out("    entry->num_bytes = 4")
        self.out("    if (pc + entry->num_bytes > last_pc) return 0")
        self.out("    if (op1 > 127) dist = op1 - 256; else dist = op1")
        self.out("    rel = (pc + 2 + dist) & 0xffff")
        self.out("    switch(op2) {")

    def z80_4byte(self, z80_2nd_byte, opcode):
        self.out("case 0x%x:" % (opcode))
        self.argorder = ["rel"]
        self.opcode1(opcode)
        self.first = False

    def z80_4byte_outro(self):
        pass

    def op1(self):
        self.out("    op1 = *src++")
        self.out("    entry->instruction[1] = op1")

    def op2(self):
        self.out("    op2 = *src++")
        self.out("    entry->instruction[2] = op2")

    def op3(self):
        self.out("    op3 = *src++")
        self.out("    entry->instruction[3] = op3")

    def start_if_clause(self, opcode):
        # if self.first:
        #     self.out("switch(opcode) {")
        #     self.first = False
        self.out("case 0x%x: /* %s %s */" % (opcode, self.mnemonic, self.fmt))

    def end_if_clause(self):
        self.out("    break")

    def check_pc(self):
        self.out("    entry->num_bytes = %d" % self.length)
        if self.length > 1:
            self.out("    if (pc + %d > last_pc) goto truncated" % self.length)

    comment_argorder = ["opcode", "op1", "op2", "op3"]

    def get_comment(self, count, argorder):
        newargs = []
        prefix = ""
        if self.flag & comment:
            for i in range(4):
                if count > i:
                    prefix += self.generator.data_op
                    newargs.append(self.comment_argorder[i])
            prefix += "; "
            argorder[0:0] = newargs
        return prefix

    def wrap_quotes(self, outstr):
        return "\"%s\"" % outstr

    def opcode1(self, opcode):
        try:
            f = udis_opcode_flag_map[self.flag & 0xff]
        except KeyError:
            f = None
        if self.flag & und:
            if f:
                f += " | FLAG_UNDOC"
            else:
                f = "FLAG_UNDOC"
        if f:
            self.out(f"    entry->flag = {f}")
        self.out(f"    entry->disassembler_type = %d" % self.generator.disassembler_type)

    def opcode2(self, opcode):
        self.op1()
        if self.fmt:
            if self.flag & pcr:
                self.out("    if (op1 > 127) dist = op1 - 256; else dist = op1")
                self.out("    rel = (pc + 2 + dist) & 0xffff")
                self.out("    labels[rel] = 1")
                self.out("    entry->target_addr = rel")
            elif self.flag & lbl:
                self.out("    labels[op1] = 1")
                self.out("    entry->target_addr = op1")
        self.opcode1(opcode)

    def opcode3(self, opcode):
        self.op1()
        self.op2()
        if self.fmt:
            if self.flag & pcr:
                self.out("    addr = op1 + 256 * op2")
                self.out("    if (addr > 32768) addr -= 0x10000")
                # limit relative address to 64k address space
                self.out("    rel = (pc + 2 + addr) & 0xffff")
                self.out("    labels[rel] = 1")
                self.out("    entry->target_addr = rel")
            elif self.flag & lbl:
                self.out("    addr = op1 + 256 * op2")
                self.out("    labels[addr] = 1")
                self.out("    entry->target_addr = addr")
        self.opcode1(opcode)

    def opcode4(self, opcode):
        self.op1()
        self.op2()
        self.op3()
        self.opcode1(opcode)

    def unknown_opcode(self):
        self.out("default:")
        self.out("    entry->flag = 0")
        self.out("    entry->disassembler_type = %d" % self.generator.disassembler_type)
        if self.leadin_offset == 0:
            self.out("    entry->num_bytes = 1")
            self.mnemonic = ""
            self.fmt = self.generator.data_op
            self.argorder = ["opcode"]
        elif self.leadin_offset == 1:
            self.out("    entry->num_bytes = 2")
            self.mnemonic = ""
            self.fmt = self.generator.data_op * 2
            self.argorder = ["leadin", "opcode"]
        self.out("    break")

    def start_multibyte_leadin(self, leadin):
        self.out("case 0x%x:" % (leadin))
        self.out("    leadin = opcode")
        self.out("    opcode = *src++")
        log.debug("starting multibyte with leadin %x" % leadin)

    def end_subroutine(self):
        self.out("}")
        if self.leadin_offset == 0:
            self.out("return entry->num_bytes")
            self.lines.append("truncated:")
            self.out("entry->flag = FLAG_DATA_BYTES")
            self.out("entry->num_bytes = 1")
            self.out("return entry->num_bytes")
            self.lines.append("}") # no indent for closing brace
        else:
            self.out("break")

class HistoryEntryDataC(RawC):
    preamble_header = c_preamble_header

    preamble = """
int %s(history_entry_t *entry, unsigned char *src, unsigned int pc, unsigned int last_pc, unsigned short *labels) {
    unsigned char *first_instruction_ptr;

    first_instruction_ptr = entry->instruction;
    entry->pc = (unsigned short)pc;
    entry->target_addr = 0;
    entry->flag = FLAG_DATA_BYTES;"""

    entry_size = """
    entry->num_bytes = %d;
    if (pc + entry->num_bytes > last_pc) {
        entry->num_bytes = last_pc - pc;
        if (entry->num_bytes == 0) {
            return 0;
        }
    }"""

    def gen_entry_size(self):
        self.out(self.entry_size % self.generator.bytes_per_line)

    def process(self, count):
        if count > 1:
            self.out("case %d:" % count)
        else:
            self.out("default:")
        self.out("    *first_instruction_ptr++ = *src++")

    @property
    def num_cases(self):
        return self.generator.bytes_per_line

    def gen_cases(self):
        self.out("entry->disassembler_type = %s" % self.generator.disassembler_type)
        self.gen_entry_size()
        self.out("switch(entry->num_bytes) {")
        for count in range(self.num_cases, 0, -1): # down to 1
            self.process(count)
        self.out("    break")

    def end_subroutine(self):
        self.out("}")
        self.out("return entry->num_bytes")
        self.lines.append("}") # no indent for closing brace

class HistoryEntryAnticC(HistoryEntryDataC):
    entry_size = """
    entry->num_bytes = 1;
    unsigned char opcode = src[0];

    if (((opcode & 0x0f) == 1) || ((opcode & 0xf0) == 0x40)) {
        entry->num_bytes = 3;
        if (pc + entry->num_bytes > last_pc) {
            entry->num_bytes = last_pc - pc;
        }
    }
    else {
        while ((pc + entry->num_bytes < last_pc) && (entry->num_bytes < %d)) {
            if (src[entry->num_bytes] == opcode) entry->num_bytes += 1;
            else break;
        }
    }"""


class HistoryEntryJumpmanHarvestC(HistoryEntryDataC):
    entry_size = """
    unsigned char opcode = src[0];

    if (opcode == 0xff) {
        entry->num_bytes = 1;
    }
    else if (pc + 7 <= last_pc) {
        entry->num_bytes = 7;
    }
    else {
        entry->num_bytes = 1;
    }"""

    @property
    def num_cases(self):
        return 7

    def gen_entry_size(self):
        self.out(self.entry_size)
