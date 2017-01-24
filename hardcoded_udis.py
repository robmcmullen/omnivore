import numpy as np

def parse_instruction_sample(pc, src):
    opcode = src[0]
    print "%04x" % pc,
    if opcode == 00:
        count = 1
        print "%02x __ __ __" % opcode,
        print "L0000",
        print "BRK"
    elif opcode == 01:
        count = 2
        op1 = src[1]
        print "%02x %02x __ __" % (opcode, op1),
        print "L0000",
        print "ORA ($%02x,x)" % op1
    elif opcode == 0x10:
        count = 2
        op1 = src[1]
        signed = op1 - 256 if op1 > 127 else operand1
        rel = (pc + 2 + signed) & 0xffff  # limit to 64k address space
        print "%02x %02x __ __" % (opcode, op1),
        print "L0000",
        print "BPL $%04x" % rel
    elif opcode == 0x20:
        count = 3
        op1 = src[1]
        op2 = src[2]
        print "%02x %02x %02x __" % (opcode, op1, op2),
        print "L0000",
        print "JSR $%02x%02x" % (op2, op1)
    elif opcode == 0x29:
        count = 8
        op1 = src[1]
        op2 = src[7]
        print "%02x %02x %02x __" % (opcode, op1, op2),
        print "L0000",
        print "JSR $%02x%02x" % (op2, op1)
    else:
        count = 1
        print "%02x __ __ __" % opcode,
        print "L0000",
        print ".byte %02x" % opcode
    return count

if __name__ == "__main__":
    import sys
    import argparse
    import importlib
    
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--cpu", help="Specify CPU type (defaults to 6502)", default="6502")
    parser.add_argument("-u", "--undocumented", help="Allow undocumented opcodes", action="store_true")
    parser.add_argument("-x", "--hex", help="Disassemble a string version of hex digits")
    parser.add_argument("filenames", metavar="filenames", nargs='*',
                   help="Binary files(s) to disassemble")
    args = parser.parse_args()

    mod_name = "hardcoded_parse_%s" % args.cpu
    try:
        parse_mod = importlib.import_module(mod_name)
    except ImportError:
        from disasm_gen_py import gen_cpu
        gen_cpu(args.cpu)
        parse_mod = importlib.import_module(mod_name)

    def process(binary):
        pc = 0;
        size = len(binary)
        i = 0
        while i < size:
            count = parse_mod.parse_instruction(pc, binary[i:i+4], pc+size)
            pc += count
            i += count

    if args.hex:
        try:
            binary = args.hex.decode("hex")
        except TypeError:
            print("Invalid hex digits!")
            sys.exit()
        binary = np.fromstring(binary, dtype=np.uint8)
        process(binary)
    else:
        for filename in args.filenames:
            with open(filename, 'rb') as fh:
                binary = fh.read()
            binary = np.fromstring(binary, dtype=np.uint8)
            process(binary)
