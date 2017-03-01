import logging
log = logging.getLogger(__name__)

# flags
pcr = 1
und = 2
z80bit = 4
lbl = 8 # subroutine/jump target; candidate for a label
comment = 16 # instruction should be displayed as a comment, not an assembler command for
r = 64
w = 128

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

    def __init__(self, lines, indent, leadin, leadin_offset):
        self.lines = lines
        self.indent = indent
        self.leadin = leadin
        self.leadin_offset = leadin_offset
        self.first = True

    def set_case(self, mnemonic_lower, hex_lower):
        pass

    def bytes1(self, opcode):
        if self.leadin_offset == 0:
            return "%02x __ __ __" % opcode, []
        else:
            return "%02x %02x __ __" % (self.leadin, opcode), []

    def bytes2(self, opcode):
        if self.leadin_offset == 0:
            return "%02x %%02x __ __" % (opcode), ["op1"]
        else:
            return "%02x %02x %%02x __" % (self.leadin, opcode), ["op1"]

    def bytes3(self, opcode):
        if self.leadin_offset == 0:
            return "%02x %%02x %%02x __" % (opcode), ["op1", "op2"]
        else:
            return "%02x %02x %%02x %%02x" % (self.leadin, opcode), ["op1", "op2"]

    def bytes4(self, opcode):
        return "%02x %%02x %%02x %%02x" % (opcode), ["op1", "op2", "op3"]

    def set_current(self, optable, parser):
        try:
            self.length, self.mnemonic, self.mode, self.flag = optable
        except ValueError:
            self.length, self.mnemonic, self.mode = optable
            self.flag = 0
        fmt = parser.address_modes[self.mode]
        self.fmt, self.argorder = convert_fmt(fmt, parser.mnemonic_lower, parser.hex_lower, self.escape_strings)
        if self.mode in parser.rw_modes:
            if self.mnemonic in parser.r_mnemonics:
                self.flag |= r
            if self.mnemonic in parser.w_mnemonics:
                self.flag |= w
        if parser.mnemonic_lower:
            self.mnemonic = self.mnemonic.lower()
        else:
            self.mnemonic = self.mnemonic.upper()
        self.fmt_op = parser.fmt_op
        self.data_op = parser.data_op

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


class PrintNumpy(PrintBase):
    preamble_header = """
def put_bytes(str, loc, dest):
    for a in str:
        dest[loc] = ord(a)
        loc += 1
"""

    preamble = """
def parse_instruction_numpy(wrap, pc, src, last_pc):
    opcode = src[0]
    put_bytes('%04x' % pc, 0, wrap)
"""

    def out(self, text):
        self.lines.append(self.indent + text)

    @property
    def iftext(self):
        if self.first:
            return "if"
        return "elif"

    def z80_4byte_intro(self, opcode):
        self.out("%s opcode == 0x%x:" % (self.iftext, opcode))
        self.out("    op1 = src[2]")
        self.out("    op2 = src[3]")
        self.out("    count = 4")
        self.out("    if pc + count > last_pc: return 0")
        self.out("    dist = op1 - 256 if op1 > 127 else op1")
        self.out("    rel = (pc + 2 + dist) & 0xffff  # limit to 64k address space")

    def z80_4byte(self, z80_2nd_byte, opcode):
        self.out("%s op2 == 0x%x:" % (self.iftext, opcode))
        bstr, bvars = "%02x %02x %%02x %02x" % (self.leadin, z80_2nd_byte, opcode), ["op1"]
        bvars.append("rel")
        outstr = "'%s       %s %s' %% (%s)" % (bstr, self.mnemonic, self.fmt, ", ".join(bvars))
        self.out("    put_bytes(%s, %d, wrap)" % (outstr, byte_loc))
        self.first = False

    def z80_4byte_outro(self):
        pass

    def op1(self):
        self.out("    op1 = src[%d]" % (1 + self.leadin_offset))

    def op2(self):
        self.out("    op2 = src[%d]" % (2 + self.leadin_offset))

    def op3(self):
        self.out("    op3 = src[%d]" % (3 + self.leadin_offset))

    def start_if_clause(self, opcode):
        self.out("%s opcode == 0x%x:" % (self.iftext, opcode))

    def end_if_clause(self):
        pass

    def check_pc(self):
        self.out("    count = %d" % self.length)
        if self.length > 1:
            self.out("    if pc + count > last_pc: return 0")

    def opcode1(self, opcode):
        bstr, bvars = self.bytes1(opcode)
        if bvars:
            bvars.extend(self.argorder) # should be null operation; 1 byte length opcodes shouldn't have any arguments
            outstr = "'%s       %s %s' %% %s" % (bstr, self.mnemonic, self.fmt, bvars)
        else:
            outstr = "'%s       %s %s'" % (bstr, self.mnemonic, self.fmt)
        self.out("    put_bytes(%s, %d, wrap)" % (outstr, byte_loc))

    def opcode2(self, opcode):
        self.op1()
        bstr, bvars = self.bytes2(opcode)
        if self.fmt:
            if self.flag & pcr:
                self.out("    dist = op1 - 256 if op1 > 127 else op1")
                self.out("    rel = (pc + 2 + dist) & 0xffff  # limit to 64k address space")
                self.out("    wrap.labels[rel] = 1")
        if bvars:
            bvars.extend(self.argorder)
            outstr = "'%s       %s %s' %% (%s)" % (bstr, self.mnemonic, self.fmt, ", ".join(bvars))
        else:
            outstr = "'%s       %s %s'" % (bstr, self.mnemonic, self.fmt)
        self.out("    put_bytes(%s, %d, wrap)" % (outstr, byte_loc))

    def opcode3(self, opcode):
        self.op1()
        self.op2()
        bstr, bvars = self.bytes3(opcode)
        if self.fmt:
            if self.flag & pcr:
                self.out("    addr = op1 + 256 * op2")
                self.out("    if addr > 32768: addr -= 0x10000")
                # limit relative address to 64k address space
                self.out("    rel = (pc + 2 + addr) & 0xffff")
                self.out("    wrap.labels[rel] = 1")
            elif self.flag & lbl:
                self.out("    addr = op1 + 256 * op2")
                self.out("    wrap.labels[addr] = 1")
        if bvars:
            bvars.extend(self.argorder)
            outstr = "'%s       %s %s' %% (%s)" % (bstr, self.mnemonic, self.fmt, ", ".join(bvars))
        else:
            outstr = "'%s       %s %s'" % (bstr, self.mnemonic, self.fmt)
        self.out("    put_bytes(%s, %d, wrap)" % (outstr, byte_loc))

    def opcode4(self, opcode):
        self.op1()
        self.op2()
        self.op3()
        bstr, bvars = self.bytes4(opcode)
        if bvars:
            bvars.extend(self.argorder)
            outstr = "'%s       %s %s' %% (%s)" % (bstr, self.mnemonic, self.fmt, ", ".join(bvars))
        else:
            outstr = "'%s       %s %s' %% (%s)" % (bstr, self.mnemonic, self.fmt, ", ".join(bvars))
        self.out("    put_bytes(%s, %d, wrap)" % (outstr, byte_loc))

    def unknown_opcode(self):
        self.out("else:")
        self.out("    count = 1")
        bstr = "%02x __ __ __"
        bvars = ["opcode", "opcode"]
        mnemonic = ".byte"
        fmt = "%02x"
        outstr = "'%s       %s %s' %% (%s)" % (bstr, mnemonic, fmt, ", ".join(bvars))
        self.out("    put_bytes(%s, %d, wrap)" % (outstr, byte_loc))

    def start_multibyte_leadin(self, leadin):
        self.out("elif opcode == 0x%x:" % (leadin))
        self.out("    leadin = opcode")
        self.out("    opcode = src[1]")
        log.debug("starting multibyte with leadin %x" % leadin)

    def end_subroutine(self):
        self.out("return count")


c_preamble_header = """#include <stdio.h>
#include <string.h>

/* 12 byte structure */
typedef struct {
    unsigned short pc;
    unsigned short dest_pc; /* address pointed to by this opcode; if applicable */
    unsigned char count;
    unsigned char flag;
    unsigned char strlen;
    unsigned char reserved;
    int strpos; /* position of start of text in instruction array */
} asm_entry;
"""


class RawC(PrintNumpy):
    preamble_header = c_preamble_header

    preamble = """
int %s(asm_entry *wrap, unsigned char *src, unsigned int pc, unsigned int last_pc, unsigned short *labels, char *instructions, int strpos) {
    int dist;
    unsigned int rel;
    unsigned short addr;
    unsigned char opcode, leadin, op1, op2, op3;
    unsigned int num_printed = 0;

    opcode = *src++;
    wrap->pc = (unsigned short)pc;
    wrap->strpos = strpos;
"""

    def out(self, s):
        if not s.endswith(":") and not s.endswith("{") and not s.endswith("}"):
            s += ";"
        self.lines.append(self.indent + s)

    def z80_4byte_intro(self, opcode):
        self.out("case 0x%x:" % (opcode))
        self.out("    op1 = *src++")
        self.out("    op2 = *src++")
        self.out("    wrap->count = 4")
        self.out("    if (pc + wrap->count > last_pc) return 0")
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

    def op2(self):
        self.out("    op2 = *src++")

    def op3(self):
        self.out("    op3 = *src++")

    def start_if_clause(self, opcode):
        if self.first:
            self.out("switch(opcode) {")
            self.first = False
        self.out("case 0x%x:" % (opcode))

    def end_if_clause(self):
        self.out("    break")

    def check_pc(self):
        self.out("    wrap->count = %d" % self.length)
        if self.length > 1:
            self.out("    if (pc + wrap->count > last_pc) goto truncated")

    comment_argorder = ["opcode", "op1", "op2", "op3"]

    def get_comment(self, count, argorder):
        newargs = []
        prefix = ""
        if self.flag & comment:
            prefix = "%s " % self.data_op
            for i in range(4):
                if count > i:
                    prefix += "%s" % self.fmt_op
                    if count > i + 1:
                        prefix += ", "
                    else:
                        prefix += "  "
                    newargs.append(self.comment_argorder[i])
                else:
                    prefix += "     "
            prefix += "; "
            argorder[0:0] = newargs
        return prefix

    def opcode_line_out(self, outstr, argorder):
        if argorder:
            outstr += ", %s" % (", ".join(argorder))
        self.out("    num_printed = sprintf(instructions, %s)" % outstr)

    def opcode1(self, opcode):
        prefix = self.get_comment(self.length, self.argorder)
        outstr = "\"%s%s %s\"" % (prefix, self.mnemonic, self.fmt)
        self.opcode_line_out(outstr, self.argorder)

    def opcode2(self, opcode):
        self.op1()
        if self.fmt:
            if self.flag & pcr:
                self.out("    if (op1 > 127) dist = op1 - 256; else dist = op1")
                self.out("    rel = (pc + 2 + dist) & 0xffff")
                self.out("    labels[rel] = 1")
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
            elif self.flag & lbl:
                self.out("    addr = op1 + 256 * op2")
                self.out("    labels[addr] = 1")
        self.opcode1(opcode)

    def opcode4(self, opcode):
        self.op1()
        self.op2()
        self.op3()
        self.opcode1(opcode)

    def unknown_opcode(self):
        self.out("default:")
        if self.leadin_offset == 0:
            self.out("    wrap->count = 1")
            self.mnemonic = ".byte"
            self.fmt = "$%02x"
            self.argorder = ["opcode"]
        elif self.leadin_offset == 1:
            self.out("    wrap->count = 2")
            self.mnemonic = ".byte"
            self.fmt = "$%02x, $%02x"
            self.argorder = ["leadin", "opcode"]
        self.opcode1(0)
        self.out("    break")

    def start_multibyte_leadin(self, leadin):
        self.out("case 0x%x:" % (leadin))
        self.out("    leadin = opcode")
        self.out("    opcode = *src++")
        log.debug("starting multibyte with leadin %x" % leadin)

    def end_subroutine(self):
        self.out("}")
        if self.leadin_offset == 0:
            self.out("wrap->flag = 0")
            self.out("wrap->strlen = num_printed")
            self.out("return wrap->count")
            self.lines.append("truncated:")
            self.out("wrap->count = 1")
            self.mnemonic = ".byte"
            self.fmt = "$%02x"
            self.argorder = ["opcode"]
            self.opcode1(0)
            self.out("wrap->strlen = num_printed")
            self.out("return wrap->count")
            self.lines.append("}") # no indent for closing brace
        else:
            self.out("break")


class UnrolledC(RawC):
    escape_strings = False

    preamble_header = c_preamble_header

   

    preamble = """
int %s(asm_entry *wrap, unsigned char *src, unsigned int pc, unsigned int last_pc, unsigned short *labels, char *instructions, int strpos, int mnemonic_lower, char *hexdigits) {
    int dist;
    unsigned int rel;
    unsigned short addr;
    unsigned char opcode, leadin, op1, op2, op3;
    char *first_instruction_ptr, *h;

    first_instruction_ptr = instructions;
    opcode = *src++;
    wrap->pc = (unsigned short)pc;
    wrap->strpos = strpos;
"""

    def opcode1(self, opcode):
        prefix = self.get_comment(self.length, self.argorder)
        outstr = "%s%s %s" % (prefix, self.mnemonic, self.fmt)
        self.opcode_line_out(outstr.rstrip(), self.argorder)

    def opcode_line_out(self, outstr, argorder):
        print outstr, argorder

        def flush_mixed(diffs):
            self.out("    if (mnemonic_lower) {")
            for c in diffs:
                self.out("        *instructions++ = '%s'" % c.lower())
            self.out("    }")
            self.out("    else {")
            for c in diffs:
                self.out("        *instructions++ = '%s'" % c.upper())
            self.out("    }")
            return []

        def flush_text(text):
            diffs = []
            for l, u in zip(text.lower(), text.upper()):
                if l == u:
                    #print "l==u: -->%s<-- -->%s<--: diffs=%s" % (l, u, diffs)
                    if len(diffs) > 0:
                        diffs = flush_mixed(diffs)
                    if u == "'" or u == "\\":
                        self.out("    *instructions++ = '\\%s'" %  u)
                    else:
                        self.out("    *instructions++ = '%s'" %  u)
                else:
                    diffs.append(u)
                    #print "l!=u: -->%s<-- -->%s<--: diffs=%s" % (l, u, diffs)
            if len(diffs) > 0:
                flush_mixed(diffs)
            return ""

        def flush_hex(operand):
            self.out("    h = &hexdigits[%s*2]" % operand)
            self.out("    *instructions++ = *h++")
            self.out("    *instructions++ = *h++")

        def flush_hex16(operand):
            self.out("    h = &hexdigits[((%s>>8)&0xff)*2]" % operand)
            self.out("    *instructions++ = *h++")
            self.out("    *instructions++ = *h++")
            self.out("    h = &hexdigits[(%s&0xff)*2]" % operand)
            self.out("    *instructions++ = *h++")
            self.out("    *instructions++ = *h++")

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
            elif tail.startswith("$%"):
                raise RuntimeError("Unsupported operand format: %s" % tail)
            else:
                text += outstr[i]
                i += 1
        flush_text(text)

    def end_subroutine(self):
        self.out("}")
        if self.leadin_offset == 0:
            self.out("wrap->flag = 0")
            self.out("wrap->strlen = (int)(instructions - first_instruction_ptr)")
            self.out("return wrap->count")
            self.lines.append("truncated:")
            self.out("wrap->count = 1")
            self.mnemonic = ".byte"
            self.fmt = "$%02x"
            self.argorder = ["opcode"]
            self.opcode1(0)
            self.out("wrap->strlen = (int)(instructions - first_instruction_ptr)")
            self.out("return wrap->count")
            self.lines.append("}") # no indent for closing brace
        else:
            self.out("break")


class DataC(RawC):
    preamble_header = c_preamble_header

    preamble = """
int %s(asm_entry *wrap, unsigned char *src, unsigned int pc, unsigned int last_pc, unsigned short *labels, char *instructions, int strpos) {
    unsigned int num_printed = 0;

    wrap->pc = (unsigned short)pc;
    wrap->strpos = strpos;
    wrap->count = 4;
    wrap->flag = 0;
    if (pc + wrap->count > last_pc) {
        wrap->count = pc + wrap->count - last_pc;
        if (wrap->count == 0) {
            wrap->strlen = 0;
            return 0;
        }
    }
    switch(wrap->count) {
"""
    def __init__(self, lines):
        self.lines = lines
        self.first = True
        self.indent = "    "

    def print_bytes(self, count, data_op, fmt_op):
        fmt = ", ".join([fmt_op] * count)
        args = ", ".join(["src[%d]" % i for i in range(count)])
        self.out("    num_printed = sprintf(instructions, \"%s %s\", %s)" % (data_op, fmt, args))

    def process(self, count, data_op, fmt_op):
        if count > 1:
            self.out("case %d:" % count)
        else:
            self.out("default:")
        self.print_bytes(count, data_op, fmt_op)
        self.out("    break")

    def gen_cases(self, parser):
        for count in range(parser.bytes_per_line, 0, -1): # down to 1
            self.process(count, parser.data_op, parser.fmt_op)

    def end_subroutine(self):
        self.out("}")
        self.out("wrap->strlen = num_printed")
        self.out("return wrap->count")
        self.lines.append("}") # no indent for closing brace

class AnticC(RawC):
    preamble = """
int %s(asm_entry *wrap, unsigned char *src, unsigned int pc, unsigned int last_pc, unsigned short *labels, char *instructions, int strpos) {
    unsigned char opcode;
    unsigned int num_printed = 0;
    int i;
    char *mnemonic;

    wrap->pc = (unsigned short)pc;
    wrap->strpos = strpos;
    wrap->flag = 0;
    wrap->count = 1;
    opcode = src[0];

    if (((opcode & 0x0f) == 1) || ((opcode & 0xf0) == 0x40)) {
        wrap->count = 3;
        if (pc + wrap->count > last_pc) {
            wrap->count = pc + wrap->count - last_pc;
        }
    }
    else {
        while ((pc + wrap->count < last_pc) && (wrap->count < 8)) {
            if (src[wrap->count] == opcode) wrap->count += 1;
            else break;
        }
    }
"""

    main = """
    switch(wrap->count) {
    case 3:
        num_printed = sprintf(instructions, "$BYTE $HEX, $HEX, $HEX ; ", src[0], src[1], src[2]);
        break;
    case 2:
        num_printed = sprintf(instructions, "$BYTE $HEX, $HEX      ; ", src[0], src[1]);
        break;
    case 1:
        num_printed = sprintf(instructions, "$BYTE $HEX           ; ", src[0]);
        break;
    default:
        num_printed = sprintf(instructions, "$BYTE $HEX", src[0]);
        for (i=1; i<wrap->count; i++) {
            num_printed += sprintf(instructions + num_printed, ", $HEX", src[i]);
        }
        num_printed += sprintf(instructions + num_printed, "; ");
        break;
    }
 

    if ((opcode & 0xf) == 1) {
        if (opcode & 0x80) num_printed += sprintf(instructions + num_printed, "DLI ");
        if (opcode & 0x40) mnemonic = "JVB";
        else if ((opcode & 0xf0) > 0) mnemonic = "<invalid>";
        else mnemonic = "JMP";
        if (wrap->count < 3) num_printed += sprintf(instructions + num_printed, "%s <bad addr>", mnemonic);
        else num_printed += sprintf(instructions + num_printed, "%s $HEX%02x", mnemonic, src[2], src[1]);
    }
    else {
        if ((opcode & 0xf) == 0) {
            if (wrap->count > 1) num_printed += sprintf(instructions + num_printed, "%dx", wrap->count);
            if (opcode & 0x80) num_printed += sprintf(instructions + num_printed, "DLI ");
            num_printed += sprintf(instructions + num_printed, "%d BLANK", (((opcode >> 4) & 0x07) + 1));
        }
        else {
            if ((opcode & 0xf0) == 0x40) {
                if (wrap->count < 3) num_printed += sprintf(instructions + num_printed, "LMS <bad addr> ");
                else num_printed += sprintf(instructions + num_printed, "LMS $HEX%02x ", src[2], src[1]);
            }
            else if (wrap->count > 1) num_printed += sprintf(instructions + num_printed, "%dx", wrap->count);

            if (opcode & 0x80) num_printed += sprintf(instructions + num_printed, "DLI ");
            if (opcode & 0x20) num_printed += sprintf(instructions + num_printed, "VSCROL ");
            if (opcode & 0x10) num_printed += sprintf(instructions + num_printed, "HSCROL ");

            num_printed += sprintf(instructions + num_printed, "MODE %X", (opcode & 0x0f));
        }
    }

    wrap->strlen = num_printed;
    return wrap->count;
}
"""
    def __init__(self, lines):
        self.lines = lines
        self.first = True
        self.indent = "    "

    def process(self, count, data_op, fmt_op):
        text = self.main.replace("$BYTE", data_op).replace("$HEX", fmt_op)
        self.lines.extend(text.splitlines())

    def gen_cases(self, parser):
        self.process(0, parser.data_op, parser.fmt_op)

    def end_subroutine(self):
        pass

class JumpmanHarvestC(RawC):
    preamble = """
int %s(asm_entry *wrap, unsigned char *src, unsigned int pc, unsigned int last_pc, unsigned short *labels, char *instructions, int strpos) {
    unsigned char opcode;
    unsigned int num_printed = 0;

    wrap->pc = (unsigned short)pc;
    wrap->strpos = strpos;
    wrap->flag = 0;
    opcode = src[0];
"""

    main = """
    if (opcode == 0xff) {
        wrap->count = 1;
        if (pc + wrap->count > last_pc) {
            wrap->count = pc + wrap->count - last_pc;
        }
        num_printed = sprintf(instructions, "$BYTE $HEX                               ; end", src[0]);
    }
    else if (pc + 7 <= last_pc) {
        wrap->count = 7;
        num_printed = sprintf(instructions, "$BYTE $HEX, $HEX, $HEX, $HEX, $HEX, $HEX, $HEX ; enc=$HEX x=$HEX y=$HEX take=$2HEX paint=$2HEX", src[0], src[1], src[2], src[3], src[4], src[5], src[6], src[0], src[1], src[2], src[4], src[3], src[6], src[5]);
    }
    else {
        wrap->count = 1;
        num_printed = sprintf(instructions, "$BYTE $HEX                               ; [incomplete]", src[0]);
    }

    wrap->strlen = num_printed;
    return wrap->count;
}
"""
    def __init__(self, lines):
        self.lines = lines
        self.first = True
        self.indent = "    "

    def process(self, count, data_op, fmt_op, fmt_2op):
        text = self.main.replace("$BYTE", data_op).replace("$HEX", fmt_op).replace("$2HEX", fmt_2op)
        self.lines.extend(text.splitlines())

    def gen_cases(self, parser):
        self.process(0, parser.data_op, parser.fmt_op, parser.fmt_2op)

    def end_subroutine(self):
        pass
