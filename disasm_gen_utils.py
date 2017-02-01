import logging
log = logging.getLogger(__name__)

# flags
pcr = 1
und = 2
z80bit = 4
lbl = 8 # subroutine/jump target; candidate for a label
r = 64
w = 128

def convert_fmt(fmt):
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

    if "'" in fmt:
        fmt = fmt.replace("'", "\\'")
    return fmt, argorder

byte_loc = 5
label_loc = 17
op_loc = 23

class PrintBase(object):
    def __init__(self, lines, indent, leadin, leadin_offset):
        self.lines = lines
        self.indent = indent
        self.leadin = leadin
        self.leadin_offset = leadin_offset
        self.first = True

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
        self.fmt, self.argorder = convert_fmt(fmt)
        if self.mode in parser.rw_modes:
            if self.mnemonic in parser.r_mnemonics:
                self.flag |= r
            if self.mnemonic in parser.w_mnemonics:
                self.flag |= w
        if not parser.mnemonic_lower:
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


class PrintNumpy(PrintBase):
    preamble = """
def put_bytes(str, loc, dest):
    for a in str:
        dest[loc] = ord(a)
        loc += 1

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


class PrintC(PrintNumpy):
    preamble = """#include <stdio.h>

int parse_instruction_c(unsigned char *wrap, unsigned int pc, unsigned char *src, unsigned int last_pc, unsigned short *labels) {
    int count, rel, dist;
    short addr;
    unsigned char opcode, leadin, op1, op2, op3;
    unsigned int num_printed = 0;

    opcode = *src++;
    sprintf(wrap, "%04x " , pc);
    wrap += 5;
"""

    def out(self, s):
        if not s.endswith(":") and not s.endswith("{") and not s.endswith("}"):
            s += ";"
        self.lines.append(self.indent + s)

    def z80_4byte_intro(self, opcode):
        self.out("case 0x%x:" % (opcode))
        self.out("    op1 = *src++")
        self.out("    op2 = *src++")
        self.out("    count = 4")
        self.out("    if (pc + count > last_pc) return 0")
        self.out("    if (op1 > 127) dist = op1 - 256; else dist = op1")
        self.out("    rel = (pc + 2 + dist) & 0xffff")
        self.out("    switch(op2) {")

    def z80_4byte(self, z80_2nd_byte, opcode):
        self.out("case 0x%x:" % (opcode))
        bstr, bvars = "%02x %02x %%02x %02x" % (self.leadin, z80_2nd_byte, opcode), ["op1"]
        bvars.append("rel")
        outstr = "\"%s       %s %s\", %s" % (bstr, self.mnemonic, self.fmt, ", ".join(bvars))
        self.out("    num_printed = sprintf(wrap, %s)" % (outstr))
        self.out("    break")
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
        self.out("    count = %d" % self.length)
        if self.length > 1:
            self.out("    if (pc + count > last_pc) return 0")

    def opcode1(self, opcode):
        bstr, bvars = self.bytes1(opcode)
        if bvars:
            bvars.extend(self.argorder) # should be null operation; 1 byte length opcodes shouldn't have any arguments
            outstr = "\"%s       %s %s\", %s" % (bstr, self.mnemonic, self.fmt, bvars)
        else:
            outstr = "\"%s       %s %s\"" % (bstr, self.mnemonic, self.fmt)
        self.out("    num_printed = sprintf(wrap, %s)" % outstr)

    def opcode2(self, opcode):
        self.op1()
        bstr, bvars = self.bytes2(opcode)
        if self.fmt:
            if self.flag & pcr:
                self.out("    if (op1 > 127) dist = op1 - 256; else dist = op1")
                self.out("    rel = (pc + 2 + dist) & 0xffff")
                self.out("    labels[rel] = 1")
        if bvars:
            bvars.extend(self.argorder)
            outstr = "\"%s       %s %s\", %s" % (bstr, self.mnemonic, self.fmt, ", ".join(bvars))
        else:
            outstr = "\"%s       %s %s\"" % (bstr, self.mnemonic, self.fmt)
        self.out("    num_printed = sprintf(wrap, %s)" % outstr)

    def opcode3(self, opcode):
        self.op1()
        self.op2()
        bstr, bvars = self.bytes3(opcode)
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
        if bvars:
            bvars.extend(self.argorder)
            outstr = "\"%s       %s %s\", %s" % (bstr, self.mnemonic, self.fmt, ", ".join(bvars))
        else:
            outstr = "\"%s       %s %s\"" % (bstr, self.mnemonic, self.fmt)
        self.out("    num_printed = sprintf(wrap, %s)" % outstr)

    def opcode4(self, opcode):
        self.op1()
        self.op2()
        self.op3()
        bstr, bvars = self.bytes4(opcode)
        if bvars:
            bvars.extend(self.argorder)
            outstr = "\"%s       %s %s\", %s" % (bstr, self.mnemonic, self.fmt, ", ".join(bvars))
        else:
            outstr = "\"%s       %s %s\"" % (bstr, self.mnemonic, self.fmt)
        self.out("    num_printed = sprintf(wrap, %s)" % outstr)

    def unknown_opcode(self):
        self.out("default:")
        if self.leadin_offset == 0:
            self.out("    count = 1")
            bstr = "%02x __ __ __"
            bvars = ["opcode", "opcode"]
            mnemonic = ".byte"
            fmt = "%02x"
            outstr = "\"%s       %s %s\", %s" % (bstr, mnemonic, fmt, ", ".join(bvars))
        elif self.leadin_offset == 1:
            self.out("    count = 2")
            bstr = "%02x %02x __ __"
            bvars = ["leadin", "opcode", "leadin", "opcode"]
            mnemonic = ".byte"
            fmt = "%02x, %02x"
            outstr = "\"%s       %s %s\", %s" % (bstr, mnemonic, fmt, ", ".join(bvars))

        self.out("    num_printed = sprintf(wrap, %s)" % outstr)
        self.out("    break")

    def start_multibyte_leadin(self, leadin):
        self.out("case 0x%x:" % (leadin))
        self.out("    leadin = opcode")
        self.out("    opcode = *src++")
        log.debug("starting multibyte with leadin %x" % leadin)

    def end_subroutine(self):
        self.out("}")
        if self.leadin_offset == 0:
            # Get rid of trailing zero that is always appended by sprintf
            # http://stackoverflow.com/questions/357068
            self.out("if (num_printed > 0) wrap[num_printed]=' '")
            self.out("return count")
            self.lines.append("}") # no indent for closing brace
        else:
            self.out("break")

class RawC(PrintC):
    max_mnemonic_length = 5
    max_operand_length = 32 - 4 - 4 - 1 - 1 - max_mnemonic_length

    preamble = """#include <stdio.h>
#include <string.h>

/* 32 byte structure */
typedef struct {
    int pc;
    int dest_pc; /* address pointed to by this opcode; -1 if not applicable */
    unsigned char count;
    unsigned char flag;
    char mnemonic[%d]; /* max length of opcode string is currently 5 */
    char operand[%d];
} asm_entry;

int parse_instruction_c(asm_entry *wrap, unsigned int pc, unsigned char *src, unsigned int last_pc, unsigned short *labels) {
    int count, dist;
    unsigned int rel;
    unsigned short addr;
    unsigned char opcode, leadin, op1, op2, op3;
    unsigned int num_printed = 0;

    opcode = *src++;
    wrap->pc = pc;
""" % (max_mnemonic_length, max_operand_length)

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
        self.fmt = ["rel"]
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
            self.out("    if (pc + wrap->count > last_pc) return 0")

    def opcode1(self, opcode):
        padding = " "*(self.max_mnemonic_length - len(self.mnemonic))
        self.out("    strncpy(wrap->mnemonic, \"%s\", %d)" % (self.mnemonic + padding, self.max_mnemonic_length))
        if self.argorder:
            outstr = "\"%s\", %s" % (self.fmt, ", ".join(self.argorder))
            self.out("    num_printed = sprintf(wrap->operand, %s)" % outstr)
        else:
            outstr = self.fmt
            if outstr:
                self.out("    strncpy(wrap->operand, \"%s\", %d)" % (outstr, len(outstr)))

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
            self.fmt = "%02x"
            self.argorder = ["op1"]
        elif self.leadin_offset == 1:
            self.out("    wrap->count = 2")
            self.mnemonic = ".byte"
            self.fmt = "%02x, %02x"
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
            self.out("memset(wrap->operand + num_printed, ' ', %d - num_printed)" % self.max_operand_length)
            self.out("return wrap->count")
            self.lines.append("}") # no indent for closing brace
        else:
            self.out("break")
