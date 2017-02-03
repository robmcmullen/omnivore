import importlib
import functools

import numpy as np

# mimicking the 32 byte C structure:
# 
# typedef struct {
#     int pc;
#     int dest_pc; /* address pointed to by this opcode; -1 if not applicable */
#     unsigned char count;
#     unsigned char flag;
#     char mnemonic[5]; /* max length of opcode string is currently 5 */
#     char operand[17];
# } asm_entry;

rawdtype = [('pc', '<i4'), ('dest_pc', '<i4'), ('count', 'u1'), ('flag', 'u1'), ('mnemonic', 'S5'), ('operand', 'S17')]

class StorageWrapper(object):
    def __init__(self, lines=1000, strsize=48):
        # string array
        self.storage = np.empty((lines,), dtype="|S%d" % strsize)
        self.row = 0
        self.num_rows = self.storage.shape[0]
        self.strsize = self.storage.itemsize
        self.labels = np.zeros([4*256*256], dtype=np.uint16)
        self.index = np.zeros([16*256*256], dtype=np.uint32)

        # strings are immutable, so get a view of bytes that we can change
        self.data = self.storage.view(dtype=np.uint8).reshape((self.num_rows, self.strsize))
        self.clear()

    def clear(self):
        self.data[:,:] = ord(" ")
        self.labels[:] = 0
        self.index[:] = 0
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

    def view(self, row):
        return self.storage.view(dtype=rawdtype)[row]

    def copy_resize(self, num_bytes):
        count = self.row
        c = np.empty([count], dtype=rawdtype)
        c1 = c.view(dtype=np.uint8).reshape([count, self.strsize])
        c1[:] = self.data[:count]
        l = np.empty([count], dtype=self.labels.dtype)
        l[:] = self.labels[:count]
        i = np.empty([num_bytes], dtype=self.index.dtype)
        i[:] = self.index[:num_bytes]
        return c, l, i

class DisassemblyInfo(object):
    def __init__(self, wrapper, first_pc, num_bytes):
        self.first_pc = first_pc
        self.num_bytes = num_bytes
        self.instructions, self.labels, self.index = wrapper.storage_wrapper.copy_resize(num_bytes)
        self.num_instructions = len(self.instructions)

    def print_instructions(self, start, count):
        for i in range(start, start+count):
            data = self.instructions[i]
            line = "%d %s %s" % (data['pc'], data['mnemonic'], data['operand'])
            print line

def get_disassembled_chunk(parse_mod, storage_wrapper, binary, pc, last, index_of_pc):
    while pc < last:
        count = parse_mod.parse_instruction_numpy(storage_wrapper, pc, binary[index_of_pc:index_of_pc+4], last)
        if count > 0:
            pc += count
            index_of_pc += count
            if not storage_wrapper.next():
                break
        else:
            break
    return pc, index_of_pc


class DisassemblerWrapper(object):
    def __init__(self, cpu, lines=65536, fast=True, mnemonic_lower=False, hex_lower=True):
        self.disasm, strsize = self.get_disassembler(cpu, fast)
        self.storage_wrapper = StorageWrapper(lines, strsize)
        self.mnemonic_lower = mnemonic_lower
        self.hex_lower = hex_lower

    def get_disassembler(self, cpu, fast=True):
        try:
            if not fast:
                raise RuntimeError
            mod_name = "udis_fast.disasm_speedups_%s" % cpu
            parse_mod = importlib.import_module(mod_name)
            self.chunk_processor = parse_mod.get_disassembled_chunk_fast
            strsize = 32
        except RuntimeError:
            mod_name = "udis_fast.hardcoded_parse_%s" % cpu
            parse_mod = importlib.import_module(mod_name)
            self.chunk_processor = functools.partial(get_disassembled_chunk, parse_mod)
            strsize = 48
        return parse_mod, strsize

    @property
    def rows(self):
        return self.storage_wrapper.row

    @property
    def labels(self):
        return self.storage_wrapper.labels

    @property
    def storage(self):
        return self.storage_wrapper.storage
    
    
    def clear(self):
        self.storage_wrapper.clear()

    def next_chunk(self, binary, pc, last, i):
        return self.chunk_processor(self.storage_wrapper, binary, pc, last, i, self.mnemonic_lower , self.hex_lower)

    def get_all(self, binary, pc, i):
        self.clear()
        num_bytes = pc - i + len(binary)
        self.chunk_processor(self.storage_wrapper, binary, pc, pc + len(binary), i, self.mnemonic_lower , self.hex_lower)
        info = DisassemblyInfo(self, pc, num_bytes)
        return info
