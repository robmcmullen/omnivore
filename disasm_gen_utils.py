# flags
pcr = 1
und = 2
z80bit = 4
lbl = 8 # subroutine/jump target; candidate for a label
r = 64
w = 128

def convert_fmt(fmt):
    if "{0:02x}" in fmt and "{1:02x}" in fmt:
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
        self.out_if(opcode)
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
        self.first = False


class PrintNumpy(PrintBase):
    def __init__(self, lines, indent, leadin, leadin_offset):
        self.lines = lines
        self.indent = indent
        self.leadin = leadin
        self.leadin_offset = leadin_offset
        self.first = True

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

    def op1(self):
        self.out("    op1 = src[%d]" % (1 + self.leadin_offset))

    def op2(self):
        self.out("    op2 = src[%d]" % (2 + self.leadin_offset))

    def op3(self):
        self.out("    op3 = src[%d]" % (3 + self.leadin_offset))

    def out_if(self, opcode):
        self.out("%s opcode == 0x%x:" % (self.iftext, opcode))

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
                self.out("    rel = (pc + 2 + signed) & 0xffff  # limit to 64k address space")
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
        outstr = "'%s       %s %s' %% (%s)" % (bstr, self.mnemonic, self.fmt, ", ".join(bvars))
        self.out("    put_bytes(%s, %d, wrap)" % (outstr, byte_loc))

    def unknown_opcode(self):
        self.out("else:")
        self.out("    count = 1")
        bstr = "%02x __ __ __"
        bvars = ["opcode", "opcode"]
        mnemonic = ".byte"
        fmt = "%02x"
        outstr = "'%s       %s %s' %% (%s)" % (bstr, self.mnemonic, self.fmt, ", ".join(bvars))
        self.out("    put_bytes(%s, %d, wrap)" % (outstr, byte_loc))

    def start_multibyte_leadin(self, leadin):
        self.out("elif opcode == 0x%x:" % (leadin))
        self.out("    leadin = opcode")
        self.out("    opcode = src[1]")
        print("starting multibyte with leadin %x" % leadin)

    def end_subroutine(self):
        self.out("return count")