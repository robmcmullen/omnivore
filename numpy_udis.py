import numpy as np

class StorageWrapper(object):
    def __init__(self, storage):
        # string array
        self.storage = storage
        self.row = 0
        self.num_rows = storage.shape[0]
        self.strsize = storage.itemsize

        # strings are immutable, so get a view of bytes that we can change
        self.data = storage.view(dtype=np.uint8).reshape((self.num_rows, self.strsize))
        self.clear()

    def clear(self):
        self.data[:,:] = ord(" ")
        self.row = 0

    def __getitem__(self, index):
        return self.data[self.row, index]
    
    def __setitem__(self, index, value):
        self.data[self.row, index] = value

    def next(self):
        self.row += 1
        if self.row == self.num_rows:
            return False
        return True




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

    storage = np.empty((1000,), dtype="|S48")
    storage_wrapper = StorageWrapper(storage)
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
        last = pc + size
        i = 0
        while pc < last:
            while pc < last:
                count = parse_mod.parse_instruction_numpy(storage_wrapper, pc, binary[i:i+4], last)
                if count > 0:
                    pc += count
                    i += count
                    if not storage_wrapper.next():
                        break
                else:
                    break

            for r in range(storage_wrapper.row):
                line = storage[r]
                if line.strip():
                    print line

            storage_wrapper.clear()

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
