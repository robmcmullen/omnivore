import numpy as np

import udis_fast

from udis_fast.flags import *


if __name__ == "__main__":
    import sys
    import argparse
    import importlib
    
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--cpu", help="Specify CPU type (defaults to 6502)", default="6502")
    parser.add_argument("-u", "--undocumented", help="Allow undocumented opcodes", action="store_true")
    parser.add_argument("-x", "--hex", help="Disassemble a string version of hex digits")
    parser.add_argument("-f", "--fast", action="store_true", help="Use C code for disassembly generation", default=True)
    parser.add_argument("--slow", action="store_false", dest="fast", help="Use C code for disassembly generation", default=True)
    parser.add_argument("-s", "--show", action="store_true", help="Show disassembly", default=False)
    parser.add_argument("-p", "--pc", action="store", help="set PC at start", default="0")
    parser.add_argument("-e", "--entry-points", nargs='+', help="PC of entry points")
    parser.add_argument("filenames", metavar="filenames", nargs='*',
                   help="Binary files(s) to disassemble")
    args = parser.parse_args()

    disasm = udis_fast.DisassemblerWrapper(args.cpu, fast=args.fast)

    def process(binary, show=False):
        if args.fast:
            process_fast(binary, show)
            return
        pc = 0;
        size = len(binary)
        last = pc + size
        i = 0
        incomplete = False
        count = 0
        while pc < last or incomplete:
            disasm.clear()
            next_pc, i = disasm.next_chunk(binary, pc, last, i)
            if next_pc == pc:
                incomplete = True
                break
            pc = next_pc

            count += disasm.rows
            if show:
                if args.fast:
                    for r in range(disasm.rows):
                        data = disasm.storage_wrapper.view(r)
                        line = "%04x %s %s" % (data['pc'], data['mnemonic'], data['operand'])
                        if data['dest_pc'] > 0:
                            line += " -> %04x" % data['dest_pc']
                        print line
                else:
                    for r in range(disasm.rows):
                        line = disasm.storage[r]
                        if line.strip():
                            print line

        if show:
            addr = 0
            for w in disasm.labels:
                if w > 0:
                    print "label: %04x" % addr
                addr += 1

        print "total instructions: %d" % count

    def process_fast(binary, show=False):
        pc = int(args.pc, 16)
        size = len(binary)
        last = pc + size
        i = 0
        info = disasm.get_all(binary, pc, i)
        if show:
            row = 0
            while (row < info.num_instructions):
                data = info[row]
                line = "%04x %s" % (data.pc, data.instruction)
                if data.dest_pc > 0:
                    line += " -> %04x %x" % (data.dest_pc, data.flag)
                    if data.flag & flag_branch:
                        line += " (branch)"
                    if data.flag & flag_jump:
                        line += " (jump)"
                if data.flag & flag_return:
                    line += " (return)"
                print line
                row += 1

        np.set_printoptions(formatter={'int':hex})
        print "total instructions: %d, bytes: %d" % (info.num_instructions, size)
        print repr(info.index_to_row[0:1000])
        print repr(info.labels[pc:pc + size])
        print np.where(info.labels > 0)

        for i, entry in enumerate(info):
            pass
        print "getitem test (looping count): %d" % i

        # add a label to an opcode if there exists a label that points to a
        # byte in the middle of that instruction, i.e. after that opcode but
        # before the next opcode.
        i = size
        while i > 0:
            i -= 1
            has_label = info.labels[pc + i]
            if has_label:
                print "Found label %04x, info.index_to_row[%d]=%d" % (pc + i, i, info.index_to_row[i])
                while info.index_to_row[i - 1] == info.index_to_row[i]:
                    i -= 1
                if info.labels[pc + i] == 0:
                    print "  added label at %04x" % (pc + i)
                info.labels[pc + i] = 1
        print np.where(info.labels > 0)

        start_points = [pc]
        if args.entry_points:
            for spc in args.entry_points:
                start_points.append(int(spc, 16))
        disasm.trace_disassembly(start_points)

    if args.hex:
        try:
            binary = args.hex.decode("hex")
        except TypeError:
            print("Invalid hex digits!")
            sys.exit()
        binary = np.fromstring(binary, dtype=np.uint8)
        process(binary, args.show)
    else:
        for filename in args.filenames:
            with open(filename, 'rb') as fh:
                binary = fh.read()
            binary = np.fromstring(binary, dtype=np.uint8)
            process(binary, args.show)
